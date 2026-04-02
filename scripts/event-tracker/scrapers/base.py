"""
scrapers/base.py — Base scraper with retry, timeout, and HTML fallback.

Resilience strategy:
  - tenacity: exponential backoff on network failures (2s → 30s cap, 3 attempts)
  - timeout:  hard 30s limit per request (prevents infinite hang)
  - polite delay: 0.5–1.5s random jitter between requests (avoids rate limiting)
  - user-agent: mimics Chrome browser to avoid bot detection
  - lxml → html.parser fallback: tolerates malformed HTML from some IDX pages
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_log,
    after_log,
)

from config import config

logger = logging.getLogger(__name__)

# Realistic Chrome UA to avoid IDX/KSEI bot blocking
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

BASE_HEADERS = {
    "Accept": "application/json, text/html, */*;q=0.9",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}


class ScraperError(Exception):
    """Raised when a scraper fails after all retries."""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for all IDX ecosystem scrapers.

    Subclasses implement fetch() which must return a list of raw
    event dicts conforming to the pre-normalization schema.
    """

    def __init__(
        self,
        timeout: int = config.SCRAPER_TIMEOUT,
        max_retries: int = config.SCRAPER_MAX_RETRIES,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.__class__.__name__)

        self.session = requests.Session()
        self.session.headers.update(BASE_HEADERS)
        self.session.headers["User-Agent"] = random.choice(_USER_AGENTS)

    # ── HTTP helpers ──────────────────────────────────────────

    def _get(self, url: str, **kwargs) -> requests.Response:
        """GET with retry, timeout, and polite delay."""
        return self._request_with_retry("GET", url, **kwargs)

    def _post(self, url: str, **kwargs) -> requests.Response:
        """POST with retry and timeout."""
        return self._request_with_retry("POST", url, **kwargs)

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Retry wrapper using tenacity.
        Exponential backoff: 2s, 4s, 8s (cap 30s).
        Retries on network errors and HTTP 5xx.
        """
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type(
                (requests.ConnectionError, requests.Timeout, requests.HTTPError)
            ),
            before=before_log(self.logger, logging.DEBUG),
            after=after_log(self.logger, logging.WARNING),
            reraise=True,
        )
        def _do_request():
            # Polite delay between requests
            time.sleep(random.uniform(0.5, 1.5))
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
            # Retry on 5xx, raise immediately on 4xx
            if resp.status_code >= 500:
                resp.raise_for_status()
            return resp

        try:
            return _do_request()
        except Exception as e:
            raise ScraperError(f"[{self.__class__.__name__}] Failed to {method} {url}: {e}") from e

    # ── HTML parsing ──────────────────────────────────────────

    def _parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML with lxml (fast), fallback to html.parser (lenient).
        IDX pages sometimes serve malformed HTML that lxml rejects.
        """
        try:
            return BeautifulSoup(html, "lxml")
        except Exception:
            self.logger.debug("lxml parsing failed, falling back to html.parser")
            return BeautifulSoup(html, "html.parser")

    def _safe_text(self, element: Optional[Any]) -> str:
        """Safely extract and strip text from a BeautifulSoup element."""
        if element is None:
            return ""
        return element.get_text(separator=" ", strip=True)

    def _safe_attr(self, element: Optional[Any], attr: str) -> str:
        """Safely extract an attribute from a BeautifulSoup element."""
        if element is None:
            return ""
        return element.get(attr, "") or ""

    # ── Abstract interface ────────────────────────────────────

    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch and return a list of raw event records.
        Each record is a dict with at minimum:
          { ticker, company, title, event_date, source, url }
        """
        raise NotImplementedError
