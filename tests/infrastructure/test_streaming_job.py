from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.infrastructure.spark.streaming_job import GithubStreamingJob


class FakeBatchDataFrame:
    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path
        self.repartition_calls: list[tuple[object, ...]] = []
        self.write = _FakeWriter(self)

    def select(self, *columns: str) -> _FakeDistinctFrame:
        assert columns == ("event_date", "event_type")
        return _FakeDistinctFrame()

    def count(self) -> int:
        return 4

    def repartition(self, *args: object) -> FakeBatchDataFrame:
        self.repartition_calls.append(args)
        return self


class _FakeDistinctFrame:
    def distinct(self) -> _FakeDistinctFrame:
        return self

    def collect(self) -> list[dict[str, str]]:
        return [
            {"event_date": "2026-06-01", "event_type": "WatchEvent"},
            {"event_date": "2026-06-01", "event_type": "PushEvent"},
        ]


class _FakeWriter:
    def __init__(self, batch_df: FakeBatchDataFrame) -> None:
        self._batch_df = batch_df
        self.mode_value: str | None = None
        self.format_value: str | None = None
        self.options: dict[str, object] = {}
        self.partition_columns: tuple[str, ...] = ()

    def mode(self, value: str) -> _FakeWriter:
        self.mode_value = value
        return self

    def format(self, value: str) -> _FakeWriter:
        self.format_value = value
        return self

    def option(self, key: str, value: object) -> _FakeWriter:
        self.options[key] = value
        return self

    def partitionBy(self, *columns: str) -> _FakeWriter:  # noqa: N802
        self.partition_columns = columns
        return self

    def save(self, path: str) -> None:
        for event_type in ("WatchEvent", "PushEvent"):
            partition_dir = Path(path) / "event_date=2026-06-01" / f"event_type={event_type}"
            partition_dir.mkdir(parents=True, exist_ok=True)
            next_index = len(list(partition_dir.glob("*.parquet")))
            (partition_dir / f"part-{next_index:05d}.parquet").touch()


def test_write_parquet_batch_preserves_partition_layout_and_bounds_file_growth(
    tmp_path: Path,
) -> None:
    settings = SimpleNamespace(
        parquet_base_path=str(tmp_path / "raw"),
        checkpoint_base_path=str(tmp_path / "checkpoints"),
        spark_parquet_max_records_per_file=10,
        spark_parquet_target_partitions_per_batch=1,
    )
    job = GithubStreamingJob(spark=object(), settings=settings)
    batch_df = FakeBatchDataFrame(tmp_path)

    job._write_parquet_batch(batch_df, batch_id=1)
    job._write_parquet_batch(batch_df, batch_id=2)

    watch_dir = tmp_path / "raw" / "event_date=2026-06-01" / "event_type=WatchEvent"
    push_dir = tmp_path / "raw" / "event_date=2026-06-01" / "event_type=PushEvent"

    assert batch_df.repartition_calls == [
        (1, "event_date", "event_type"),
        (1, "event_date", "event_type"),
    ]
    assert batch_df.write.mode_value == "append"
    assert batch_df.write.format_value == "parquet"
    assert batch_df.write.options["compression"] == "snappy"
    assert batch_df.write.options["maxRecordsPerFile"] == 10
    assert batch_df.write.partition_columns == ("event_date", "event_type")
    assert len(list(watch_dir.glob("*.parquet"))) == 2
    assert len(list(push_dir.glob("*.parquet"))) == 2
