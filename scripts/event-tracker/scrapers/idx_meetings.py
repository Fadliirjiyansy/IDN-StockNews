"""
scrapers/idx_meetings.py — AGM / EGM / RUPS Scraper

Source: IDX disclosure announcements filtered by RUPS keywords
  https://www.idx.co.id/primary/ListedCompany/GetCompanyAnnouncements?keyword=RUPS

Detects:
  - RUPST  (Rapat Umum Pemegang Saham Tahunan) → AGM
  - RUPSLB (Rapat Umum Pemegang Saham Luar Biasa) → EGM
  - AGM / EGM (English)
"""

import logging
from typing import Any, Dict, List, Optional

from config import config
from scrapers.base import BaseScraper, ScraperError

logger = logging.getLogger(__name__)

# Keyword → event_type mapping (ordered: EGM before AGM so RUPSLB wins)
MEETING_KEYWORDS: Dict[str, str] = {
    "rupslb":    "EGM",
    "rups luar biasa": "EGM",
    "extraordinary general meeting": "EGM",
    "egm":       "EGM",
    "rupst":     "AGM",
    "rups tahunan": "AGM",
    "annual general meeting": "AGM",
    "agm":       "AGM",
    "rups":      "AGM",  # generic fallback
}


class IDXMeetingsScraper(BaseScraper):
    """
    Queries IDX announcements for RUPS/AGM/EGM keywords.
    Classifies each result as either AGM or EGM.
    """

    IDX_ANNOUNCE_URL = f"{config.IDX_API_BASE}/ListedCompany/GetCompanyAnnouncements"

    def fetch(self) -> List[Dict[str, Any]]:
        events = []
        seen_keys: set = set()

        # Query using primary keywords (avoids redundant results from all synonyms)
        for keyword in ("RUPS", "RUPSLB", "AGM", "EGM"):
            batch = self._query_meetings(keyword)
            for event in batch:
                # In-memory dedup: use URL or (ticker + title) as key
                key = event.get("url") or f"{event.get('ticker')}:{event.get('title')}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    events.append(event)

        logger.info(f"[IDXMeetingsScraper] Total raw meeting events: {len(events)}")
        return events

    def _query_meetings(self, keyword: str) -> List[Dict[str, Any]]:
        """Query IDX announcement API for one meeting keyword."""
        events = []
        params = {
            "start":   0,
            "length":  30,
            "keyword": keyword,
        }
        try:
            resp = self._get(self.IDX_ANNOUNCE_URL, params=params)

            if "application/json" not in resp.headers.get("Content-Type", ""):
                return []

            data = resp.json()
            records = data.get("data", data.get("Data", []))

            for rec in records:
                event = self._parse_meeting(rec)
                if event:
                    events.append(event)

        except ScraperError as e:
            self.logger.warning(f"Meeting query failed keyword='{keyword}': {e}")
        except Exception as e:
            self.logger.debug(f"Meeting parse error: {e}")

        return events

    def _parse_meeting(self, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single announcement record into a meeting event dict."""
        ticker   = rec.get("KodeEmiten") or rec.get("StockCode")
        company  = rec.get("NamaEmiten") or rec.get("CompanyName")
        title    = rec.get("Judul") or rec.get("Title") or rec.get("title")
        date_str = rec.get("Tanggal") or rec.get("Date") or rec.get("date")
        url      = rec.get("Attachment") or rec.get("Url") or rec.get("url")

        if not title:
            return None

        # Classify as AGM or EGM
        event_type = self._classify_meeting(str(title))
        if event_type is None:
            return None  # Not a meeting announcement

        if url and not str(url).startswith("http"):
            url = config.IDX_BASE_URL + url

        return {
            "source":             "IDX",
            "event_type":         event_type,
            "ticker":             ticker,
            "company":            company,
            "title":              str(title).strip(),
            "announcement_date":  date_str,
            "event_date":         date_str,
            "url":                url,
        }

    def _classify_meeting(self, title: str) -> Optional[str]:
        """
        Determine if a title refers to an AGM or EGM.
        Returns 'AGM', 'EGM', or None if not a meeting announcement.
        """
        title_lower = title.lower()
        for keyword, event_type in MEETING_KEYWORDS.items():
            if keyword in title_lower:
                return event_type
        return None
