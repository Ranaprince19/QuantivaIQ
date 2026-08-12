import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import logging

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database Configuration
DB_DRIVER = os.getenv("DB_DRIVER", "sqlite").lower()

SQLITE_DB_FULL_PATH = BASE_DIR / "quantivaiq.db"

if DB_DRIVER == "sqlite":

    if os.getenv("VERCEL"):
        # Vercel requires SQLite in read-only URI mode
        db_path = SQLITE_DB_FULL_PATH.as_posix()

        if not db_path.startswith("/"):
            db_path = "/" + db_path

        DATABASE_URL = (
            f"sqlite:///file://{db_path}?mode=ro&uri=true"
        )

    else:
        DATABASE_URL = f"sqlite:///{SQLITE_DB_FULL_PATH}"

else:
    DATABASE_URL = os.getenv("DATABASE_URL")


# Logging Configuration
def setup_logging(name="QuantivaIQ"):

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


# SQLAlchemy Engine
def get_engine():
    if is_sqlite():
        # SQLite locks the whole file on writes by default, so concurrent
        # processes (ETL + live simulator + dashboard) can hit
        # "database is locked" errors. WAL mode + a busy timeout lets
        # readers and writers coexist instead of failing immediately.
        engine = create_engine(DATABASE_URL, connect_args={"timeout": 30})
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.execute(text("PRAGMA busy_timeout=30000;"))
        return engine
    return create_engine(DATABASE_URL)


# Database Connection Test
def test_db_connection():

    try:
        engine = get_engine()

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return True, ""

    except OperationalError as exc:

        logger = setup_logging("DBConnectionCheck")

        logger.error(
            f"Unable to connect to the configured database. Error: {exc}"
        )

        return False, str(exc)


# App Settings
NUM_ORDERS = int(os.getenv("NUM_ORDERS", 50000))
NUM_CUSTOMERS = int(os.getenv("NUM_CUSTOMERS", 5000))
NUM_PRODUCTS = int(os.getenv("NUM_PRODUCTS", 500))
SIMULATION_INTERVAL = int(os.getenv("SIMULATION_INTERVAL_SECONDS", 10))

FRAUD_RATE = float(
    os.getenv("FRAUD_CONTAMINATION_RATE", 0.02)
)
def is_sqlite():
    return DB_DRIVER == "sqlite"