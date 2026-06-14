"""CleanupParquetUseCase — xoá các Parquet partition cũ hơn ngưỡng giữ lại.

Entry point: ``make cleanup`` hoặc chạy trực tiếp:
    uv run python -m src.application.use_cases.cleanup_parquet
"""

from __future__ import annotations

import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

_DEFAULT_RETENTION_DAYS = 90


class CleanupParquetUseCase:
    """Xoá Parquet partitions cũ hơn ``retention_days`` ngày.

    Args:
        parquet_base_path: Đường dẫn tới thư mục chứa các partition event_date=YYYY-MM-DD.
        retention_days:    Số ngày giữ lại dữ liệu (mặc định 90 ngày).
        dry_run:           Nếu True, chỉ log mà không xoá.
    """

    def __init__(
        self,
        parquet_base_path: str,
        retention_days: int = _DEFAULT_RETENTION_DAYS,
        *,
        dry_run: bool = False,
    ) -> None:
        self._base_path = Path(parquet_base_path)
        self._retention_days = retention_days
        self._dry_run = dry_run

    def execute(self) -> dict[str, object]:
        """Quét và xoá các partition hết hạn.

        Returns:
            Dict chứa thống kê: deleted_partitions, deleted_bytes, skipped_partitions, errors.
        """
        cutoff = date.today() - timedelta(days=self._retention_days)
        deleted_partitions: list[str] = []
        skipped_partitions: list[str] = []
        deleted_bytes = 0
        errors: list[str] = []

        if not self._base_path.exists():
            logger.warning("cleanup_parquet.base_path_missing", path=str(self._base_path))
            return {"deleted_partitions": [], "deleted_bytes": 0, "skipped_partitions": [], "errors": []}

        for partition_dir in sorted(self._base_path.iterdir()):
            if not partition_dir.is_dir():
                continue
            if not partition_dir.name.startswith("event_date="):
                continue

            raw_date = partition_dir.name.removeprefix("event_date=")
            try:
                partition_date = date.fromisoformat(raw_date)
            except ValueError:
                skipped_partitions.append(partition_dir.name)
                continue

            if partition_date >= cutoff:
                skipped_partitions.append(partition_dir.name)
                continue

            # Tính dung lượng trước khi xoá
            partition_bytes = sum(f.stat().st_size for f in partition_dir.rglob("*") if f.is_file())

            if self._dry_run:
                logger.info(
                    "cleanup_parquet.would_delete",
                    partition=partition_dir.name,
                    size_mb=round(partition_bytes / 1024 / 1024, 1),
                )
                deleted_partitions.append(partition_dir.name)
                deleted_bytes += partition_bytes
                continue

            try:
                shutil.rmtree(partition_dir)
                deleted_partitions.append(partition_dir.name)
                deleted_bytes += partition_bytes
                logger.info(
                    "cleanup_parquet.deleted",
                    partition=partition_dir.name,
                    size_mb=round(partition_bytes / 1024 / 1024, 1),
                )
            except OSError as exc:
                errors.append(f"{partition_dir.name}: {exc}")
                logger.error(
                    "cleanup_parquet.delete_failed",
                    partition=partition_dir.name,
                    error=str(exc),
                )

        logger.info(
            "cleanup_parquet.completed",
            deleted_count=len(deleted_partitions),
            deleted_mb=round(deleted_bytes / 1024 / 1024, 1),
            skipped_count=len(skipped_partitions),
            error_count=len(errors),
            dry_run=self._dry_run,
            cutoff=str(cutoff),
        )

        return {
            "deleted_partitions": deleted_partitions,
            "deleted_bytes": deleted_bytes,
            "skipped_partitions": skipped_partitions,
            "errors": errors,
        }


def _main() -> None:
    import argparse

    from src.infrastructure.config import get_settings
    from src.infrastructure.logging_config import configure_logging

    parser = argparse.ArgumentParser(description="Xoá Parquet partitions cũ")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=_DEFAULT_RETENTION_DAYS,
        help=f"Số ngày giữ lại (mặc định {_DEFAULT_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ hiển thị sẽ xoá gì, không thực sự xoá",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)

    use_case = CleanupParquetUseCase(
        parquet_base_path=settings.parquet_base_path,
        retention_days=args.retention_days,
        dry_run=args.dry_run,
    )
    result = use_case.execute()

    deleted = len(result["deleted_partitions"])  # type: ignore[arg-type]
    freed_mb = round(result["deleted_bytes"] / 1024 / 1024, 1)  # type: ignore[operator]
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Đã xoá {deleted} partition, giải phóng {freed_mb} MB")


if __name__ == "__main__":
    _main()
