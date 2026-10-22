"""Resolve Wizz Air's versioned public API from its official website."""

from __future__ import annotations

import re
from threading import Lock
from typing import Optional
from urllib.parse import urljoin

from curl_cffi import requests


WIZZ_HOMEPAGE_URL = "https://www.wizzair.com/en-gb"
_API_PATTERN = re.compile(r"https://be\.wizzair\.com/(\d+\.\d+\.\d+)/Api")
_SCRIPT_PATTERN = re.compile(r'''src=["']([^"']+\.js(?:\?[^"']*)?)["']''')
_cached_api_base: Optional[str] = None
_cache_lock = Lock()


def extract_wizz_api_base(text: str) -> Optional[str]:
    """Return the first versioned Wizz API base embedded in page source."""
    match = _API_PATTERN.search(text)
    if not match:
        return None
    return f"https://be.wizzair.com/{match.group(1)}/Api"


def wizz_api_base() -> str:
    """Read and cache the current public API base from official Wizz assets."""
    global _cached_api_base
    if _cached_api_base is not None:
        return _cached_api_base

    with _cache_lock:
        if _cached_api_base is not None:
            return _cached_api_base

        session = requests.Session(impersonate="chrome")
        response = session.get(WIZZ_HOMEPAGE_URL, timeout=45)
        response.raise_for_status()
        resolved = extract_wizz_api_base(response.text)

        if resolved is None:
            for script_path in _SCRIPT_PATTERN.findall(response.text):
                if "/dist/" not in script_path:
                    continue
                script = session.get(urljoin(WIZZ_HOMEPAGE_URL, script_path), timeout=45)
                if script.status_code >= 400:
                    continue
                resolved = extract_wizz_api_base(script.text)
                if resolved is not None:
                    break

        if resolved is None:
            raise RuntimeError(
                "Wizz Air: nie udało się ustalić aktualnej wersji publicznego API "
                "z oficjalnej strony"
            )

        _cached_api_base = resolved
        return resolved
