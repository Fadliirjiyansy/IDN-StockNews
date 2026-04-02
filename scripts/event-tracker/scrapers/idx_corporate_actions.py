"""
scrapers/idx_corporate_actions.py — Corporate Actions Scraper

Sources:
  1. KSEI Corporate Action schedule
     https://web.ksei.co.id/corporate_action
     → HTML table with: Emiten | Event | Ex-Date | Record Date | Payment Date

  2. IDX KI (Keterbukaan Informasi) announcements — filtered by corp action keywords
     https://www.idx.co.id/primary/ListedCompany/GetCompanyAnnouncements

Event types detected: DIVIDEND, RIGHTS_ISSUE, STOCK_SPLIT, BONUS_SHARES,
                      BUYBACK, PRIVATE_PLACEMENT.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from config import config
from scrapers.base import BaseScraper, ScraperError

logger = logging.getLogger(__name__)

# Keywords to search in IDX announcement API
CORP_ACTION_KEYWORDS = [
    "dividen", "dividend", "rights issue", "hmetd",
    "stock split", "pemecahan saham",
    "saham bonus", "bonus share",
    "buyback", "pembelian kembali",
    "private placement",
]


class IDXCorporateActionsScraper(BaseScraper):
    """
    Scrapes corporate actions from KSEI schedule and IDX announcements.
    """

    KSEI_CORP_ACTION_URL = f"{config.KSEI_BASE_URL}/corporate_action"
    IDX_ANNOUNCE_URL = f"{config.IDX_API_BASE}/ListedCompany/GetCompanyAnnouncements"

    def fetch(self) -> List[Dict[str, Any]]:
        events = []
        events.extend(self._fetch_ksei())
        events.extend(self._fetch_idx_announcements())
        logger.info(f"[CorporateActionsScraper] Total raw events: {len(events)}")
        return events

    # ── KSEI ──────────────────────────────────────────────────

    def _fetch_ksei(self) -> List[Dict[str, Any]]:
        """
        Scrape KSEI corporate action schedule table.
        Columns: No | Emiten | Kode | Jenis | Ex-Date | Record Date | Payment Date
        """
        events = []
        try:
            resp = self._get(self.KSEI_CORP_ACTION_URL)
            soup = self._parse_html(resp.text)

            tables = soup.find_all("table")
            if not tables:
                self.logger.warning("KSEI: no table found — page structure may have changed")
                return []

            # Use the largest table (most rows = data table)
            table = max(tables, key=lambda t: len(t.find_all("tr")))
            rows = table.find_all("tr")

            if len(rows) < 2:
                return []

            # Map header columns
            header_cells = rows[0].find_all(["th", "td"])
            headers = [self._safe_text(c).lower() for c in header_cells]
            col = self._map_ksei_columns(headers)

            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                try:
                    event = self._parse_ksei_row(cells, col)
                    if event:
                        events.append(event)
                except Exception as e:
                    self.logger.debug(f"Skipping KSEI row: {e}")

        except ScraperError as e:
            self.logger.error(f"KSEI scrape failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected KSEI error: {e}", exc_info=True)

        return events

    def _map_ksei_columns(self, headers: List[str]) -> Dict[str, int]:
        col = {}
        for i, h in enumerate(headers):
            if any(k in h for k in ("emiten", "company", "issuer")):
                col["company"] = i
            elif any(k in h for k in ("kode", "ticker", "code", "efek")):
                col["ticker"] = i
            elif any(k in h for k in ("jenis", "type", "event", "aksi")):
                col["event_type"] = i
            elif any(k in h for k in ("ex-date", "ex date", "ex_date", "tanggal ex")):
                col["ex_date"] = i
            elif any(k in h for k in ("record", "recording")):
                col["record_date"] = i
            elif any(k in h for k in ("payment", "pembayaran", "bayar")):
                col["payment_date"] = i

        # Positional fallbacks
        if "company" not in col:
            col["company"] = 1
        if "ticker" not in col:
            col["ticker"] = 2
        if "event_type" not in col:
            col["event_type"] = 3

        return col

    def _parse_ksei_row(
        self,
        cells: list,
        col: Dict[str, int],
    ) -> Optional[Dict[str, Any]]:
        company    = self._safe_text(cells[col.get("company", 1)]) if len(cells) > col.get("company", 1) else ""
        ticker     = self._safe_text(cells[col.get("ticker", 2)]) if len(cells) > col.get("ticker", 2) else ""
        event_str  = self._safe_text(cells[col.get("event_type", 3)]) if len(cells) > col.get("event_type", 3) else ""
        ex_date    = self._safe_text(cells[col.get("ex_date", 4)]) if len(cells) > col.get("ex_date", 4) else ""
        record_dt  = self._safe_text(cells[col.get("record_date", 5)]) if len(cells) > col.get("record_date", 5) else ""
        payment_dt = self._safe_text(cells[col.get("payment_date", 6)]) if len(cells) > col.get("payment_date", 6) else ""

        if not (company or ticker) or not event_str:
            return None

        return {
            "source":      "KSEI",
            "ticker":      ticker or None,
            "company":     company or None,
            "title":       f"{event_str} – {company or ticker}",
            "description": f"Ex-Date: {ex_date} | Record: {record_dt} | Payment: {payment_dt}",
            "ex_date":     ex_date or None,
            "record_date": record_dt or None,
            "event_date":  ex_date or record_dt or None,
            "url":         self.KSEI_CORP_ACTION_URL,
        }

    # ── IDX Announcements API ──────────────────────────────────

    def _fetch_idx_announcements(self) -> List[Dict[str, Any]]:
        """
        Query IDX announcement API for corporate action keywords.
        Paginates through results.
        """
        events = []
        for keyword in CORP_ACTION_KEYWORDS:
            try:
                page_events = self._query_idx_announcements(keyword)
                events.extend(page_events)
                self.logger.debug(
                    f"IDX announcements: keyword='{keyword}' → {len(page_events)} events"
                )
            except Exception as e:
                self.logger.warning(f"IDX announcements query failed for '{keyword}': {e}")

        return events

    def _query_idx_announcements(
        self,
        keyword: str,
        page_size: int = 30,
    ) -> List[Dict[str, Any]]:
        events = []
        params = {
            "start":  0,
            "length": page_size,
            "keyword": keyword,
            "type":   "CA",  # Corporate Actions filter (if supported)
        }
        try:
            resp = self._get(self.IDX_ANNOUNCE_URL, params=params)
            data = resp.json()
            records = data.get("data", data.get("Data", []))

            for rec in records:
                event = self._parse_idx_announcement(rec)
                if event:
                    events.append(event)

        except Exception as e:
            self.logger.debug(f"IDX announcements parse error: {e}")

        return events

    def _parse_idx_announcement(self, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ticker  = rec.get("KodeEmiten") or rec.get("StockCode")
        company = rec.get("NamaEmiten") or rec.get("CompanyName")
        title   = rec.get("Judul") or rec.get("Title") or rec.get("title")
        date_str = rec.get("Tanggal") or rec.get("Date") or rec.get("date")
        url     = rec.get("Attachment") or rec.get("Url") or rec.get("url")

        if not title:
            return None

        if url and not url.startswith("http"):
            url = config.IDX_BASE_URL + url

        return {
            "source":             "IDX",
            "ticker":             ticker,
            "company":            company,
            "title":              str(title).strip(),
            "announcement_date":  date_str,
            "event_date":         date_str,
            "url":                url,
        }
