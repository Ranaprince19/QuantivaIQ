import os
import time
import requests
from typing import Optional

POWERBI_TENANT = os.getenv("POWERBI_TENANT_ID")
POWERBI_CLIENT_ID = os.getenv("POWERBI_CLIENT_ID")
POWERBI_CLIENT_SECRET = os.getenv("POWERBI_CLIENT_SECRET")
POWERBI_WORKSPACE_ID = os.getenv("POWERBI_WORKSPACE_ID")
POWERBI_REPORT_ID = os.getenv("POWERBI_REPORT_ID")


def _get_aad_token() -> Optional[str]:
    """Obtain an AAD token for Power BI using client credentials."""
    if not (POWERBI_TENANT and POWERBI_CLIENT_ID and POWERBI_CLIENT_SECRET):
        return None

    token_url = f"https://login.microsoftonline.com/{POWERBI_TENANT}/oauth2/v2.0/token"
    data = {
        "client_id": POWERBI_CLIENT_ID,
        "client_secret": POWERBI_CLIENT_SECRET,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
        "grant_type": "client_credentials",
    }

    resp = requests.post(token_url, data=data, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    return token


def get_report_embed_info():
    """Return embed information for a Power BI report (embedUrl and a generated embed token).

    Requires these environment variables to be set:
      - POWERBI_TENANT_ID
      - POWERBI_CLIENT_ID
      - POWERBI_CLIENT_SECRET
      - POWERBI_WORKSPACE_ID
      - POWERBI_REPORT_ID

    The service principal must have permission to the target workspace/report.
    """
    access_token = _get_aad_token()
    if not access_token:
        return None

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    # Get report metadata (embedUrl)
    if not (POWERBI_WORKSPACE_ID and POWERBI_REPORT_ID):
        return None

    report_url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{POWERBI_WORKSPACE_ID}/reports/{POWERBI_REPORT_ID}"
    )
    resp = requests.get(report_url, headers=headers, timeout=10)
    resp.raise_for_status()
    report = resp.json()
    embed_url = report.get("embedUrl")

    # Generate embed token for the report
    gen_token_url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{POWERBI_WORKSPACE_ID}/reports/{POWERBI_REPORT_ID}/GenerateToken"
    )
    body = {"accessLevel": "View"}
    token_resp = requests.post(gen_token_url, headers=headers, json=body, timeout=10)
    token_resp.raise_for_status()
    embed_token = token_resp.json().get("token")
    expire_seconds = token_resp.json().get("expiration", None)

    return {
        "embedUrl": embed_url,
        "embedToken": embed_token,
        "reportId": POWERBI_REPORT_ID,
        "workspaceId": POWERBI_WORKSPACE_ID,
        "expiration": expire_seconds,
        "fetched_at": int(time.time()),
    }


def create_push_dataset(dataset_name: str, tables: dict):
    """Create a streaming/push dataset in Power BI. `tables` is a dict of tableName -> columns spec.

    Example `tables`:
      {"transactions": [{"name": "transaction_id", "dataType": "string"}, ...]}
    """
    access_token = _get_aad_token()
    if not access_token:
        return None

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    url = "https://api.powerbi.com/v1.0/myorg/datasets?defaultRetentionPolicy=None"
    dataset = {"name": dataset_name, "tables": []}
    for tbl_name, cols in tables.items():
        dataset["tables"].append({"name": tbl_name, "columns": cols})

    resp = requests.post(url, headers=headers, json=dataset, timeout=10)
    resp.raise_for_status()
    return resp.json()


def push_rows_to_dataset(dataset_id: str, table_name: str, rows: list):
    access_token = _get_aad_token()
    if not access_token:
        return None
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    url = f"https://api.powerbi.com/v1.0/myorg/datasets/{dataset_id}/tables/{table_name}/rows"
    resp = requests.post(url, headers=headers, json={"rows": rows}, timeout=10)
    resp.raise_for_status()
    return resp.json()
