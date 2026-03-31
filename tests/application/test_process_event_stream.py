from __future__ import annotations

import signal
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.application.use_cases.process_event_stream import (
    ProcessEventStreamUseCase,
    SparkJobError,
    _main,
)


class StubStreamingJob:
    def __init__(self) -> None:
        self.start_calls = 0
        self.await_calls = 0
        self.stop_calls = 0

    def start(self) -> None:
        self.start_calls += 1

    def await_termination(self) -> None:
        self.await_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


class FailingStartJob(StubStreamingJob):
    def start(self) -> None:
        self.start_calls += 1
        raise RuntimeError("spark boom")


class StubLoop:
    def __init__(self) -> None:
        self.handlers: dict[signal.Signals, object] = {}
        self.executor_calls: list[str] = []

    def add_signal_handler(self, sig: signal.Signals, handler: object) -> None:
        self.handlers[sig] = handler

    async def run_in_executor(self, executor: object, func: object) -> object:
        del executor
        self.executor_calls.append(getattr(func, "__name__", repr(func)))
        return func()


@pytest.mark.asyncio
async def test_execute_happy_path_starts_waits_and_stops_job() -> None:
    job = StubStreamingJob()
    use_case = ProcessEventStreamUseCase(streaming_job=job)
    loop = StubLoop()

    with patch(
        "src.application.use_cases.process_event_stream.asyncio.get_running_loop",
        return_value=loop,
    ):
        await use_case.execute()

    assert job.start_calls == 1
    assert job.await_calls == 1
    assert job.stop_calls == 1
    assert signal.SIGINT in loop.handlers
    assert signal.SIGTERM in loop.handlers


@pytest.mark.asyncio
async def test_execute_job_failure_raises_spark_job_error_and_stops() -> None:
    job = FailingStartJob()
    use_case = ProcessEventStreamUseCase(streaming_job=job)
    loop = StubLoop()

    with (
        patch(
            "src.application.use_cases.process_event_stream.asyncio.get_running_loop",
            return_value=loop,
        ),
        pytest.raises(SparkJobError, match="spark boom"),
    ):
        await use_case.execute()

    assert job.start_calls == 1
    assert job.await_calls == 0
    assert job.stop_calls == 1


def test_on_shutdown_sets_event_and_stops_job() -> None:
    job = StubStreamingJob()
    use_case = ProcessEventStreamUseCase(streaming_job=job)

    use_case._on_shutdown()

    assert use_case._shutdown_event.is_set() is True
    assert job.stop_calls == 1


@pytest.mark.asyncio
async def test_main_wires_dependencies_and_executes_use_case() -> None:
    settings = SimpleNamespace(log_level="INFO", metrics_port=9091)
    spark = object()
    execute_mock = AsyncMock()
    streaming_job_instances: list[object] = []

    config_module = ModuleType("src.infrastructure.config")
    config_module.get_settings = lambda: settings  # type: ignore[attr-defined]

    logging_module = ModuleType("src.infrastructure.observability.logging_config")
    logging_module.configure_logging = lambda level: None  # type: ignore[attr-defined]

    metrics_module = ModuleType("src.infrastructure.observability.metrics")
    metrics_module.start_metrics_server = lambda port: None  # type: ignore[attr-defined]

    session_factory_module = ModuleType("src.infrastructure.spark.session_factory")
    session_factory_module.create_spark_session = lambda cfg: spark  # type: ignore[attr-defined]

    streaming_module = ModuleType("src.infrastructure.spark.streaming_job")

    class FakeGithubStreamingJob:
        def __init__(self, *, spark: object, settings: object) -> None:
            self.spark = spark
            self.settings = settings
            streaming_job_instances.append(self)

        def start(self) -> None:
            return None

        def await_termination(self) -> None:
            return None

        def stop(self) -> None:
            return None

    streaming_module.GithubStreamingJob = FakeGithubStreamingJob  # type: ignore[attr-defined]

    with (
        patch.dict(
            sys.modules,
            {
                "src.infrastructure.config": config_module,
                "src.infrastructure.observability.logging_config": logging_module,
                "src.infrastructure.observability.metrics": metrics_module,
                "src.infrastructure.spark.session_factory": session_factory_module,
                "src.infrastructure.spark.streaming_job": streaming_module,
            },
        ),
        patch.object(ProcessEventStreamUseCase, "execute", execute_mock),
    ):
        await _main()

    execute_mock.assert_awaited_once()
    assert len(streaming_job_instances) == 1
    assert streaming_job_instances[0].spark is spark
    assert streaming_job_instances[0].settings is settings
