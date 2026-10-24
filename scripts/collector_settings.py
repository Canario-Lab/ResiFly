"""Shared reliability settings for recurring flight collection."""

from __future__ import annotations


# Google Flights starts returning intermittent errors when a shared runner
# sends too many route/day requests at once.  Keep this independent from the
# general airline collector concurrency requested with --workers.
GOOGLE_FLIGHTS_MAX_WORKERS = 3


def google_flights_worker_count(requested_workers: int) -> int:
    """Clamp to the user-selected ceiling; not a guaranteed Google service limit."""
    return min(max(int(requested_workers), 1), GOOGLE_FLIGHTS_MAX_WORKERS)
