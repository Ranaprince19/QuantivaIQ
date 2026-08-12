# Power BI CSV Export

This folder contains generated CSV exports for Power BI Desktop.

## Regenerate the dataset

Run the export helper from the repository root:

```powershell
python python/export_powerbi_csv.py
```

## Import into Power BI Desktop

1. Open Power BI Desktop.
2. Select **Get Data → Folder**.
3. Point to the `dashboards/powerbi_data/` folder.
4. Confirm the file list and load the datasets.

## Notes

- The CSV files can be used when direct PostgreSQL access is unavailable.
- For a live dashboard, use PostgreSQL DirectQuery instead.
