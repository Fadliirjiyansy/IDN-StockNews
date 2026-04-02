"""
scrapers/idx_suspensions.py — Trading Suspension Scraper

Source: IDX Disclosure (Keterbukaan Informasi) announcements
  https://www.idx.co.id/primary/ListedCompany/GetCompanyAnnouncements?keyword=suspensi

IDX may also publish suspensions as:
  - "Penghentian Sementara Perdagangan Efek"
  - "Unusual Market Activity (UMA)"
  - "Trading Halt"
"""

import logging
from typing import Any, Dict, List, Optional

from config import config
from scrapers.base import BaseScraper, ScraperError

logger = logging.getLogger(__name__)

SUSPENSION_KEYWORDS = [
    "suspensi",
    "suspend",
    "penghentian sementara",
    "penghentian perdagangan",
    "uma",
    "unusual market activity",
    "trading halt",
    "halt perdagangan",
]


class IDXSuspensionsScraper(BaseScraper):
    """
    Queries IDX announcements for suspension-related keywords.
    Each keyword is queried separately; results are merged and de-duplicated
    in-memory by announcement URL (before hash-based DB deduplication).
    """

    IDX_ANNOUNCE_URL = f"{config.IDX_API_BASE}/ListedCompany/GetCompanyAnnouncements"

    def fetch(self) -> List[Dict[str, Any]]:
        events = []
        seen_urls: set = set()

        for keyword in SUSPENSION_KEYWORDS:
            batch = self._query_suspensions(keyword)
            for event in batch:
                # In-memory dedup by URL before passing to pipeline
                url = event.get("url", "")
                title = event.get("title", "")
                key = url or title
                if key and key not in seen_urls:
                    seen_urls.add(key)
                    events.append(event)

        logger.info(f"[IDXSuspensionsScraper] Total raw suspension events: {len(events)}")
        return events

    def _query_suspensions(self, keyword: str) -> List[Dict[str, Any]]:
        """Query IDX announcement API for one keyword."""
        events = []
        params = {
            "start":   0,
            "length":  20,
            "keyword": keyword,
        }
        try:
            resp = self._get(self.IDX_ANNOUNCE_URL, params=params)

            # Gracefully handle non-JSON responses (HTML error pages, etc.)
            if "application/json" not in resp.headers.get("Content-Type", ""):
                self.logger.debug(f"Non-JSON response for keyword='{keyword}', skipping")
                return []

            data = resp.json()
            records = data.get("data", data.get("Data", []))

            for rec in records:
                event = self._parse_suspension(rec)
                if event:
                    events.append(event)

        except ScraperError as e:
            self.logger.warning(f"Suspension query failed keyword='{keyword}': {e}")
        except Exception as e:
            self.logger.debug(f"Suspension parse error keyword='{keyword}': {e}")

        return events

    def _parse_suspension(self, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single IDX announcement record into a raw event dict."""
        ticker   = rec.get("KodeEmiten") or rec.get("StockCode")
        company  = rec.get("NamaEmiten") or rec.get("CompanyName")
        title    = rec.get("Judul") or rec.get("Title") or rec.get("title")
        date_str = rec.get("Tanggal") or rec.get("Date") or rec.get("date")
        url      = rec.get("Attachment") or rec.get("Url") or rec.get("url")

        if not title:
            return None

        # Filter: only keep records that actually contain suspension keywords
        title_lower = str(title).lower()
        if not any(kw in title_lower for kw in SUSPENSION_KEYWORDS):
            return None

        if url and not str(url).startswith("http"):
            url = config.IDX_BASE_URL + url

        return {
            "source":             "IDX",
            "event_type":         "SUSPENSION",
            "ticker":             ticker,
            "company":            company,
            "title":              str(title).strip(),
            "description":        self._extract_reason(str(title)),
            "announcement_date":  date_str,
            "event_date":         date_str,
            "url":                url,
        }

    def _extract_reason(self, title: str) -> str:
        """
        Attempt to extract suspension reason from the title string.
        Examples:
          "Suspensi Saham ABCD - Unusual Market Activity" → "Unusual Market Activity"
          "Penghentian Sementara Perdagangan GOTO"        → "N/A"
        """
        if "-" in title:
            parts = title.split("-", 1)
            reason = parts[-1].strip()
            if reason:
                return reason
        if "uma" in title.lower() or "unusual" in title.lower():
            return "Unusual Market Activity (UMA)"
        if "suspensi" in title.lower() or "suspend" in title.lower():
            return "Trading Suspension"
        return "N/A"
