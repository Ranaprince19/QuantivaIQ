from config import setup_logging, test_db_connection, is_sqlite
from utils import refresh_materialized_views

logger = setup_logging("PowerBIRefresh")


def main():
    if not test_db_connection():
        logger.error("Unable to connect to the configured database. Confirm your .env values are correct.")
        return

    if is_sqlite():
        logger.info("SQLite mode detected; materialized views are not supported.")
        return

    refresh_materialized_views()
    logger.info("All Power BI materialized views refreshed successfully.")


if __name__ == '__main__':
    main()
