"""CLI entry point for bootstrapping ClickHouse from the Parquet archive."""

from __future__ import annotations

import argparse
from datetime import date

import structlog

from src.domain.exceptions import ClickHouseBackfillError
from src.infrastructure.config import get_settings
from src.infrastructure.logging_config import configure_logging
from src.infrastructure.storage.clickhouse_backfill_service import ClickHouseBackfillService

logger = structlog.get_logger(__name__)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from exc


def main() -> int:
    """Run the one-shot Parquet-to-ClickHouse bootstrap."""
    parser = argparse.ArgumentParser(
        description="Bootstrap ClickHouse github_data from data/raw parquet partitions."
    )
    parser.add_argument("--start-date", type=_parse_date, default=None)
    parser.add_argument("--end-date", type=_parse_date, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Truncate github_data before inserting when the table is not empty.",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)

    service = ClickHouseBackfillService(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
        parquet_base_path=settings.parquet_base_path,
    )

    try:
        result = service.backfill(
            start_date=args.start_date,
            end_date=args.end_date,
            force=args.force,
        )
    except ClickHouseBackfillError as exc:
        logger.error("clickhouse_backfill.failed", error=str(exc))
        return 1

    logger.info(
        "clickhouse_backfill.succeeded",
        inserted_rows=result.inserted_rows,
        batch_count=result.batch_count,
        start_date=result.start_date.isoformat() if result.start_date else None,
        end_date=result.end_date.isoformat() if result.end_date else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
