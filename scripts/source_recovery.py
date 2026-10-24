"""Bounded, deferred source retries inside one immutable full-batch run.

The normal adapter retry budget is unchanged. Only failed jobs are replayed,
after the rest of their queue, without releasing the provider's HTTP limits.
Standalone collectors retain their existing fail-closed behaviour.
"""
from collections import deque
from concurrent.futures import CancelledError, FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import date, datetime, timezone
import threading
from time import monotonic

RECOVERY_DELAYS = (60, 120)
MAX_FAILED_JOBS_PER_ROUND = 20
_controller = None
_local = threading.local()


class PermanentSourceError(RuntimeError):
    """Local integrity/configuration/safety failure, not a request to replay."""


class RecoveryExhausted(RuntimeError):
    def __init__(self, group, missing):
        super().__init__(f"Source recovery exhausted: {group}; {missing} unfinished jobs; publication blocked")


def retryable(error):
    chain, seen = [], set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        chain.append(error)
        error = error.__cause__ or error.__context__
    if any(isinstance(e, (PermanentSourceError, CancelledError, KeyboardInterrupt,
                          SystemExit, PermissionError, FileNotFoundError)) for e in chain):
        return False
    return bool(chain) and isinstance(chain[0], (RuntimeError, ValueError, TimeoutError, ConnectionError))


def can_defer(error):
    return _controller is not None and getattr(_local, "recovering", False) and retryable(error)


def _job_id(job):
    if isinstance(job, (tuple, list)):
        return [_job_id(value) for value in job]
    if isinstance(job, date):
        return job.isoformat()
    if isinstance(job, str):
        return job
    raise PermanentSourceError("Recovery jobs require route/date identifiers, never session data")


class RecoveryRun:
    def __init__(self, path, identity, delays):
        self.path, self.delays = path, tuple(delays)
        self.lock = threading.RLock()
        self.report = {"status": "running", "run_id": identity["run_id"],
                       "identity": identity, "delays_seconds": list(delays),
                       "failure_cutoff_per_round": MAX_FAILED_JOBS_PER_ROUND, "groups": {}}

    def update(self, group=None, **fields):
        from scripts.collection_coverage import atomic_json
        with self.lock:
            row = self.report if group is None else self.report["groups"].setdefault(group, {})
            row.update(fields, updated_at=datetime.now(timezone.utc).isoformat())
            atomic_json(self.path, self.report)

    def wait(self, seconds):
        from scripts.source_scheduler import _stopped, raise_if_stopped
        # No HTTP slot is held. Stop/interrupt remains responsive during cooldown.
        while seconds > 0:
            raise_if_stopped()
            chunk = min(seconds, 10)
            _stopped.wait(chunk)
            seconds -= chunk
        raise_if_stopped()


@contextmanager
def deferred_collection(path, identity, delays=RECOVERY_DELAYS):
    global _controller
    if _controller is not None:
        raise PermanentSourceError("Another deferred collection is active")
    controller = RecoveryRun(path, identity, delays)
    _controller = controller
    try:
        controller.update()
        yield controller
    except BaseException as error:
        controller.update(status="failed", error_type=type(error).__name__)
        raise
    else:
        controller.update(status="complete")
    finally:
        _controller = None


def map_jobs(group, function, jobs, workers):
    """Yield successful jobs once; retry only failures in two deferred rounds."""
    jobs = list(jobs)
    controller = _controller
    if controller is None:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            yield from pool.map(function, jobs)
        return
    pending, completed = list(range(len(jobs))), 0
    errors, failed_at = {}, {}

    def fetch(index):
        from scripts.source_scheduler import raise_if_stopped
        previous = getattr(_local, "recovering", False)
        _local.recovering = True
        try:
            raise_if_stopped()
            return function(jobs[index])
        finally:
            _local.recovering = previous

    for round_number in range(len(controller.delays) + 1):
        if round_number:
            from scripts.source_scheduler import retry_delay
            # Time spent finishing healthy jobs already counts as cooldown.
            now = monotonic()
            delay = max([0] + [
                max(controller.delays[round_number - 1], retry_delay(0, error))
                - (now - failed_at[index]) for index, error in errors.items()])
            controller.update(group, status="cooldown", round=round_number,
                              pending=[_job_id(jobs[i]) for i in pending], wait_seconds=delay)
            print(f"Source {group}: {len(pending)} deferred jobs; recovery {round_number} in {delay:g}s", flush=True)
            if delay > 0:
                controller.wait(delay)
        controller.update(group, status="running", round=round_number,
                          total=len(jobs), completed=completed,
                          pending=[_job_id(jobs[i]) for i in pending] if round_number else [],
                          circuit_open=False)
        failed, errors, failed_at, circuit_open = [], {}, {}, False
        with ThreadPoolExecutor(max_workers=workers) as pool:
            queued, futures = deque(pending), {}
            try:
                while queued or futures:
                    # Only the active workers have futures. A broad outage can
                    # pause the queue before thousands of new attempts start.
                    while queued and len(futures) < workers:
                        index = queued.popleft()
                        futures[pool.submit(fetch, index)] = index
                    done, _ = wait(futures, return_when=FIRST_COMPLETED)
                    for future in done:
                        index = futures.pop(future)
                        try:
                            result = future.result()
                        except Exception as error:
                            if not retryable(error):
                                raise
                            failed.append(index)
                            errors[index] = error
                            failed_at[index] = monotonic()
                            controller.update(group, last_error_type=type(error).__name__,
                                              last_failed_job=_job_id(jobs[index]))
                            if len(errors) >= MAX_FAILED_JOBS_PER_ROUND and not circuit_open:
                                circuit_open = True
                                # Not attempted is missing, not empty/successful.
                                failed.extend(queued)
                                queued.clear()
                                controller.update(group, circuit_open=True)
                        else:
                            completed += 1
                            yield result
            except BaseException:
                from scripts.source_scheduler import stop_requests
                stop_requests()
                for future in futures:
                    future.cancel()
                controller.update(group, status="failed", completed=completed)
                raise
        pending = sorted(failed)
        controller.update(group, status="deferred" if pending else "complete",
                          completed=completed, pending=[_job_id(jobs[i]) for i in pending])
        if not pending:
            return
    controller.update(group, status="exhausted")
    raise RecoveryExhausted(group, len(pending))
