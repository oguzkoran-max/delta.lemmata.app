from __future__ import annotations

import os
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from delta_lemmata import web_runtime as runtime_module
from delta_lemmata.analysis_orchestrator import AnalysisOrchestrator
from delta_lemmata.corpus_materialization import CorpusMaterializationService
from delta_lemmata.job_janitor import JobJanitor
from delta_lemmata.prepared_corpus_service import PreparedCorpusService
from delta_lemmata.web_runtime import (
    WebRuntime,
    WebRuntimeError,
    WebRuntimeErrorCode,
    build_web_runtime,
)

STORE_SECRET = "11" * 32
AUTHORITY_SECRET = "22" * 32
RECOVERY_SECRET = "33" * 32


def _private(path: Path) -> Path:
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    return path.resolve(strict=True)


def _production(root: Path) -> dict[str, str]:
    return {
        "DELTA_ENV": "production",
        "DELTA_RUNTIME_ROOT": str(root),
        "DELTA_JOB_OWNER_SECRET_HEX": STORE_SECRET,
        "DELTA_PREPARATION_AUTHORITY_SECRET_HEX": AUTHORITY_SECRET,
        "DELTA_RECOVERY_RECEIPT_SECRET_HEX": RECOVERY_SECRET,
    }


def _expect(environment: dict[str, str], code: WebRuntimeErrorCode) -> None:
    with pytest.raises(WebRuntimeError) as captured:
        build_web_runtime(environment)
    assert captured.value.code is code
    assert str(captured.value) == code.value
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_development_runtime_uses_a_private_temporary_root_and_closes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "DELTA_RUNTIME_ROOT",
        "DELTA_JOB_OWNER_SECRET_HEX",
        "DELTA_PREPARATION_AUTHORITY_SECRET_HEX",
        "DELTA_RECOVERY_RECEIPT_SECRET_HEX",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DELTA_ENV", "test")

    runtime = build_web_runtime()
    temporary = runtime._temporary_directory
    assert temporary is not None
    root = Path(temporary.name).resolve(strict=True)
    assert isinstance(runtime.materializations, CorpusMaterializationService)
    assert isinstance(runtime.prepared_corpora, PreparedCorpusService)
    assert isinstance(runtime.analyses, AnalysisOrchestrator)
    assert isinstance(runtime.janitor, JobJanitor)
    runtime.maintain()
    assert stat_mode(root) == 0o700
    runtime.close()
    assert not root.exists()
    runtime.close()


def stat_mode(path: Path) -> int:
    return os.stat(path, follow_symlinks=False).st_mode & 0o777


def test_explicit_development_and_production_roots_build_without_being_owned_by_runtime(
    tmp_path: Path,
) -> None:
    development_root = _private(tmp_path / "development")
    development = build_web_runtime(
        {
            "DELTA_ENV": " Development ",
            "DELTA_RUNTIME_ROOT": str(development_root),
        }
    )
    assert development._temporary_directory is None
    development.close()
    assert development_root.is_dir()

    production_root = _private(tmp_path / "production")
    production = build_web_runtime(_production(production_root))
    assert production._temporary_directory is None
    thread = production._maintenance_thread
    assert thread is not None
    assert thread.name == "delta-job-maintenance"
    assert thread.daemon is True
    assert thread.is_alive()
    production.close()
    assert production._maintenance_stop is None
    assert production._maintenance_thread is None
    assert not thread.is_alive()
    assert production_root.is_dir()


@pytest.mark.parametrize(
    ("environment", "code"),
    [
        ({"DELTA_ENV": "unknown"}, WebRuntimeErrorCode.INVALID_PROFILE),
        ({"DELTA_ENV": "production"}, WebRuntimeErrorCode.INVALID_ROOT),
    ],
)
def test_profile_and_required_production_root_fail_closed(
    environment: dict[str, str],
    code: WebRuntimeErrorCode,
) -> None:
    _expect(environment, code)


def test_production_requires_three_distinct_valid_secrets(tmp_path: Path) -> None:
    root = _private(tmp_path / "runtime")
    base = _production(root)

    missing = dict(base)
    missing.pop("DELTA_JOB_OWNER_SECRET_HEX")
    _expect(missing, WebRuntimeErrorCode.MISSING_SECRET)

    blank = dict(base)
    blank["DELTA_JOB_OWNER_SECRET_HEX"] = "  "
    _expect(blank, WebRuntimeErrorCode.MISSING_SECRET)

    for value in ("a", "zz", "aa"):
        invalid = dict(base)
        invalid["DELTA_JOB_OWNER_SECRET_HEX"] = value
        _expect(invalid, WebRuntimeErrorCode.INVALID_SECRET)

    reused = dict(base)
    reused["DELTA_PREPARATION_AUTHORITY_SECRET_HEX"] = STORE_SECRET.upper()
    _expect(reused, WebRuntimeErrorCode.SECRET_REUSE)

    reused_recovery = dict(base)
    reused_recovery["DELTA_RECOVERY_RECEIPT_SECRET_HEX"] = AUTHORITY_SECRET
    _expect(reused_recovery, WebRuntimeErrorCode.SECRET_REUSE)

    _expect(
        {"DELTA_ENV": "test", "DELTA_JOB_OWNER_SECRET_HEX": "a"},
        WebRuntimeErrorCode.INVALID_SECRET,
    )


def test_runtime_root_rejects_relative_missing_symlink_file_and_permissive_paths(
    tmp_path: Path,
) -> None:
    _expect(
        {"DELTA_ENV": "development", "DELTA_RUNTIME_ROOT": "relative"},
        WebRuntimeErrorCode.INVALID_ROOT,
    )
    _expect(
        {
            "DELTA_ENV": "development",
            "DELTA_RUNTIME_ROOT": str(tmp_path / "missing-parent" / "runtime"),
        },
        WebRuntimeErrorCode.INVALID_ROOT,
    )
    _expect(
        _production(tmp_path / "absent-production"),
        WebRuntimeErrorCode.INVALID_ROOT,
    )

    target = _private(tmp_path / "target")
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    _expect(_production(link), WebRuntimeErrorCode.INVALID_ROOT)

    file_root = tmp_path / "file"
    file_root.write_text("not a directory", encoding="utf-8")
    _expect(_production(file_root), WebRuntimeErrorCode.INVALID_ROOT)

    permissive = _private(tmp_path / "permissive")
    permissive.chmod(0o755)
    _expect(_production(permissive), WebRuntimeErrorCode.INVALID_ROOT)


def test_runtime_maps_unexpected_initialization_failures_and_cleans_temporary_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    created: list[Path] = []
    original = runtime_module.TemporaryDirectory
    original_store = runtime_module.SQLiteJobStore

    def observed_temporary_directory(*args: object, **kwargs: object):
        directory = original(*args, **kwargs)
        created.append(Path(directory.name).resolve(strict=True))
        return directory

    monkeypatch.setattr(runtime_module, "TemporaryDirectory", observed_temporary_directory)
    monkeypatch.setattr(
        runtime_module,
        "SQLiteJobStore",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("private path")),
    )
    _expect({"DELTA_ENV": "test"}, WebRuntimeErrorCode.INITIALIZATION_FAILED)
    assert created and not created[0].exists()

    explicit_root = _private(tmp_path / "explicit")
    _expect(
        {"DELTA_ENV": "development", "DELTA_RUNTIME_ROOT": str(explicit_root)},
        WebRuntimeErrorCode.INITIALIZATION_FAILED,
    )
    assert explicit_root.exists()
    monkeypatch.setattr(runtime_module, "SQLiteJobStore", original_store)

    class BrokenThread:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError("private thread failure")

        def join(self, *, timeout: float) -> None:
            assert timeout == runtime_module._MAINTENANCE_JOIN_TIMEOUT_SECONDS

    production_root = _private(tmp_path / "broken-thread")
    monkeypatch.setattr(runtime_module, "Thread", BrokenThread)
    _expect(_production(production_root), WebRuntimeErrorCode.INITIALIZATION_FAILED)


def test_runtime_maintenance_is_content_free_and_startup_recovery_is_mandatory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = build_web_runtime({"DELTA_ENV": "test"})
    monkeypatch.setattr(
        runtime.materializations,
        "reap_expired",
        lambda: (_ for _ in ()).throw(RuntimeError("private corpus")),
    )
    with pytest.raises(WebRuntimeError) as captured:
        runtime.maintain()
    assert captured.value.code is WebRuntimeErrorCode.MAINTENANCE_FAILED
    assert str(captured.value) == WebRuntimeErrorCode.MAINTENANCE_FAILED.value
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None
    runtime.close()

    class BrokenJanitor:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def recover_startup(self) -> None:
            raise RuntimeError("private durable state")

    monkeypatch.setattr(runtime_module, "JobJanitor", BrokenJanitor)
    _expect({"DELTA_ENV": "test"}, WebRuntimeErrorCode.INITIALIZATION_FAILED)


def test_analysis_run_finalizes_result_before_terminal_maintenance() -> None:
    events: list[str] = []

    class Materializations:
        @staticmethod
        def reap_expired() -> None:
            events.append("materializations")

    class Analyses:
        @staticmethod
        def run_until(*, expected_job_id: str) -> SimpleNamespace:
            events.append(f"analysis:{expected_job_id}")
            return SimpleNamespace(job_id=expected_job_id)

    class Janitor:
        @staticmethod
        def run_once() -> None:
            events.append("janitor")

    runtime = WebRuntime(
        materializations=Materializations(),  # type: ignore[arg-type]
        prepared_corpora=object(),  # type: ignore[arg-type]
        analyses=Analyses(),  # type: ignore[arg-type]
        janitor=Janitor(),  # type: ignore[arg-type]
    )

    def finalize_result() -> None:
        events.append("finalize")

    def present_result() -> str:
        events.append("present")
        return "published"

    def admit_analysis() -> None:
        events.append("admit")

    def resume_result() -> bool:
        events.append("resume")
        return False

    assert (
        runtime.run_analysis_once(
            expected_job_id="job-a",
            admit_analysis=admit_analysis,
            resume_result=resume_result,
            finalize_result=finalize_result,
            present_result=present_result,
        )
        == "published"
    )
    assert events == [
        "resume",
        "admit",
        "analysis:job-a",
        "finalize",
        "materializations",
        "janitor",
        "present",
    ]

    class FailedAnalyses:
        @staticmethod
        def run_until(*, expected_job_id: str) -> None:
            assert expected_job_id == "job-a"
            events.append("failed-analysis")
            raise RuntimeError("primary failure")

    class FailedMaintenance:
        @staticmethod
        def reap_expired() -> None:
            events.append("failed-maintenance")
            raise RuntimeError("private cleanup failure")

    runtime.analyses = FailedAnalyses()  # type: ignore[assignment]
    runtime.materializations = FailedMaintenance()  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="primary failure"):
        runtime.run_analysis_once(
            expected_job_id="job-a",
            admit_analysis=admit_analysis,
            resume_result=lambda: False,
            finalize_result=finalize_result,
            present_result=present_result,
        )
    assert events[-3:] == ["failed-analysis", "failed-maintenance", "janitor"]

    runtime.analyses = Analyses()  # type: ignore[assignment]
    with pytest.raises(WebRuntimeError) as captured:
        runtime.run_analysis_once(
            expected_job_id="job-a",
            admit_analysis=admit_analysis,
            resume_result=lambda: False,
            finalize_result=finalize_result,
            present_result=present_result,
        )
    assert captured.value.code is WebRuntimeErrorCode.MAINTENANCE_FAILED

    runtime.materializations = Materializations()  # type: ignore[assignment]

    def failed_finalization() -> None:
        events.append("failed-finalization")
        raise RuntimeError("publication failure")

    with pytest.raises(RuntimeError, match="publication failure"):
        runtime.run_analysis_once(
            expected_job_id="job-a",
            admit_analysis=admit_analysis,
            resume_result=lambda: False,
            finalize_result=failed_finalization,
            present_result=present_result,
        )
    assert events[-4:] == [
        "analysis:job-a",
        "failed-finalization",
        "materializations",
        "janitor",
    ]


def test_analysis_run_resumes_published_context_and_rejects_job_mismatch() -> None:
    events: list[str] = []

    class Materializations:
        @staticmethod
        def reap_expired() -> None:
            events.append("materializations")

    class Analyses:
        @staticmethod
        def run_until(*, expected_job_id: str) -> None:
            events.append(f"analysis:{expected_job_id}")
            return None

    class Janitor:
        @staticmethod
        def run_once() -> None:
            events.append("janitor")

    runtime = WebRuntime(
        materializations=Materializations(),  # type: ignore[arg-type]
        prepared_corpora=object(),  # type: ignore[arg-type]
        analyses=Analyses(),  # type: ignore[arg-type]
        janitor=Janitor(),  # type: ignore[arg-type]
    )

    assert (
        runtime.run_analysis_once(
            expected_job_id="job-a",
            admit_analysis=lambda: events.append("unexpected-admit"),
            resume_result=lambda: True,
            finalize_result=lambda: events.append("unexpected-finalize"),
            present_result=lambda: "recovered",
        )
        == "recovered"
    )
    assert events == ["materializations", "janitor"]

    events.clear()
    with pytest.raises(WebRuntimeError) as captured:
        runtime.run_analysis_once(
            expected_job_id="job-a",
            admit_analysis=lambda: events.append("admit"),
            resume_result=lambda: False,
            finalize_result=lambda: events.append("unexpected-finalize"),
            present_result=lambda: events.append("unexpected-present"),
        )
    assert captured.value.code is WebRuntimeErrorCode.ANALYSIS_NOT_READY
    assert events == ["admit", "analysis:job-a", "materializations", "janitor"]


def test_analysis_run_drains_a_stale_fifo_predecessor_without_cross_presentation() -> None:
    events: list[str] = []

    class Materializations:
        @staticmethod
        def reap_expired() -> None:
            events.append("materializations")

    class Analyses:
        @staticmethod
        def run_until(*, expected_job_id: str) -> SimpleNamespace:
            events.extend(("run:stale-job", f"run:{expected_job_id}"))
            return SimpleNamespace(job_id=expected_job_id)

    class Janitor:
        @staticmethod
        def run_once() -> None:
            events.append("janitor")

    runtime = WebRuntime(
        materializations=Materializations(),  # type: ignore[arg-type]
        prepared_corpora=object(),  # type: ignore[arg-type]
        analyses=Analyses(),  # type: ignore[arg-type]
        janitor=Janitor(),  # type: ignore[arg-type]
    )

    assert (
        runtime.run_analysis_once(
            expected_job_id="expected-job",
            admit_analysis=lambda: events.append("admit:expected-job"),
            resume_result=lambda: False,
            finalize_result=lambda: events.append("finalize:expected-job"),
            present_result=lambda: "present:expected-job",
        )
        == "present:expected-job"
    )
    assert events == [
        "admit:expected-job",
        "run:stale-job",
        "run:expected-job",
        "finalize:expected-job",
        "materializations",
        "janitor",
    ]


def test_concurrent_sessions_keep_admission_execution_and_finalization_bound() -> None:
    events: list[str] = []
    release = Event()
    results: dict[str, str] = {}

    class Materializations:
        @staticmethod
        def reap_expired() -> None:
            events.append("materializations")

    class Analyses:
        @staticmethod
        def run_until(*, expected_job_id: str) -> SimpleNamespace:
            events.append(f"analysis:{expected_job_id}")
            return SimpleNamespace(job_id=expected_job_id)

    class Janitor:
        @staticmethod
        def run_once() -> None:
            events.append("janitor")

    runtime = WebRuntime(
        materializations=Materializations(),  # type: ignore[arg-type]
        prepared_corpora=object(),  # type: ignore[arg-type]
        analyses=Analyses(),  # type: ignore[arg-type]
        janitor=Janitor(),  # type: ignore[arg-type]
    )

    def run(job_id: str) -> None:
        assert release.wait(timeout=5)
        results[job_id] = runtime.run_analysis_once(
            expected_job_id=job_id,
            admit_analysis=lambda: events.append(f"admit:{job_id}"),
            resume_result=lambda: False,
            finalize_result=lambda: events.append(f"finalize:{job_id}"),
            present_result=lambda: f"published:{job_id}",
        )

    threads = [Thread(target=run, args=(job_id,)) for job_id in ("job-a", "job-b")]
    for thread in threads:
        thread.start()
    release.set()
    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert results == {
        "job-a": "published:job-a",
        "job-b": "published:job-b",
    }
    first_job = events[0].split(":", maxsplit=1)[1]
    second_job = "job-b" if first_job == "job-a" else "job-a"
    assert events == [
        f"admit:{first_job}",
        f"analysis:{first_job}",
        f"finalize:{first_job}",
        "materializations",
        "janitor",
        f"admit:{second_job}",
        f"analysis:{second_job}",
        f"finalize:{second_job}",
        "materializations",
        "janitor",
    ]


def test_background_maintenance_waits_for_result_finalization() -> None:
    finalization_started = Event()
    release_finalization = Event()
    background_started = Event()
    background_finished = Event()
    result: list[str] = []

    class Materializations:
        @staticmethod
        def reap_expired() -> None:
            return None

    class Analyses:
        @staticmethod
        def run_until(*, expected_job_id: str) -> SimpleNamespace:
            return SimpleNamespace(job_id=expected_job_id)

    class Janitor:
        @staticmethod
        def run_once() -> None:
            return None

    runtime = WebRuntime(
        materializations=Materializations(),  # type: ignore[arg-type]
        prepared_corpora=object(),  # type: ignore[arg-type]
        analyses=Analyses(),  # type: ignore[arg-type]
        janitor=Janitor(),  # type: ignore[arg-type]
    )

    def finalize_result() -> str:
        finalization_started.set()
        assert release_finalization.wait(timeout=5)
        return "published"

    def run_analysis() -> None:
        result.append(
            runtime.run_analysis_once(
                expected_job_id="job-a",
                admit_analysis=lambda: None,
                resume_result=lambda: False,
                finalize_result=finalize_result,
                present_result=lambda: "published",
            )
        )

    def run_background_maintenance() -> None:
        background_started.set()
        runtime.maintain()
        background_finished.set()

    analysis_thread = Thread(target=run_analysis)
    maintenance_thread = Thread(target=run_background_maintenance)
    analysis_thread.start()
    assert finalization_started.wait(timeout=5)
    maintenance_thread.start()
    assert background_started.wait(timeout=5)
    assert not background_finished.wait(timeout=0.05)
    release_finalization.set()
    analysis_thread.join(timeout=5)
    maintenance_thread.join(timeout=5)

    assert not analysis_thread.is_alive()
    assert not maintenance_thread.is_alive()
    assert background_finished.is_set()
    assert result == ["published"]


def test_periodic_maintenance_is_traffic_independent_and_idempotent() -> None:
    maintenance_calls = 0
    janitor_calls = 0

    class Materializations:
        @staticmethod
        def reap_expired() -> None:
            nonlocal maintenance_calls
            maintenance_calls += 1
            if maintenance_calls == 1:
                raise RuntimeError("private first pass")

    class Janitor:
        @staticmethod
        def run_once() -> None:
            nonlocal janitor_calls
            janitor_calls += 1

    class BoundedStop:
        waits = 0

        def wait(self, interval: float) -> bool:
            assert interval == runtime_module._MAINTENANCE_INTERVAL_SECONDS
            self.waits += 1
            return self.waits == 3

    runtime = WebRuntime(
        materializations=Materializations(),  # type: ignore[arg-type]
        prepared_corpora=object(),  # type: ignore[arg-type]
        analyses=object(),  # type: ignore[arg-type]
        janitor=Janitor(),  # type: ignore[arg-type]
    )
    runtime._maintenance_loop(BoundedStop())  # type: ignore[arg-type]
    assert maintenance_calls == 2
    assert janitor_calls == 2

    runtime.start_periodic_maintenance()
    thread = runtime._maintenance_thread
    runtime.start_periodic_maintenance()
    assert runtime._maintenance_thread is thread
    runtime.close()
    assert thread is not None and not thread.is_alive()


def test_absolute_noncanonical_root_is_rejected(tmp_path: Path) -> None:
    noncanonical = tmp_path / "child" / ".." / "runtime"
    _expect(
        {"DELTA_ENV": "development", "DELTA_RUNTIME_ROOT": str(noncanonical)},
        WebRuntimeErrorCode.INVALID_ROOT,
    )
