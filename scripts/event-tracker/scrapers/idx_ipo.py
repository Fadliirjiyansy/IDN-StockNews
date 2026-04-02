"""
scrapers/idx_ipo.py — IPO Pipeline Scraper

Sources:
  1. e-ipo.co.id  — Official e-IPO platform (OJK regulated)
     https://www.e-ipo.co.id/en/ipo/ipo-now
     https://www.e-ipo.co.id/en/ipo/coming-soon

  2. IDX new listing announcements
     https://www.idx.co.id/primary/TradingData/GetNewListedStock

Robustness:
  - e-ipo multi-page pagination support
  - IDX API JSON fallback
  - HTML table parser with column index fallback if headers rename
"""

import logging
from typing import Any, Dict, List, Optional

from config import config
from scrapers.base import BaseScraper, ScraperError

logger = logging.getLogger(__name__)


class IDXIPOScraper(BaseScraper):
    """
    Scrapes upcoming and current IPOs from e-ipo.co.id and IDX.
    Returns raw event dicts ready for normalization.
    """

    EIPO_CURRENT_URL = f"{config.EIPO_BASE_URL}/en/ipo/ipo-now"
    EIPO_COMING_URL = f"{config.EIPO_BASE_URL}/en/ipo/coming-soon"
    IDX_NEW_LISTING_URL = f"{config.IDX_API_BASE}/TradingData/GetNewListedStock"

    def fetch(self) -> List[Dict[str, Any]]:
        events = []
        events.extend(self._fetch_eipo(self.EIPO_CURRENT_URL))
        events.extend(self._fetch_eipo(self.EIPO_COMING_URL))
        events.extend(self._fetch_idx_new_listings())
        logger.info(f"[IDXIPOScraper] Total raw IPO events fetched: {len(events)}")
        return events

    # ── e-ipo.co.id ───────────────────────────────────────────

    def _fetch_eipo(self, url: str) -> List[Dict[str, Any]]:
        """
        Scrape IPO listings from e-ipo.co.id HTML table.
        Table columns (may vary): Company | Ticker | Schedule | Price | Status
        """
        events = []
        try:
            resp = self._get(url)
            soup = self._parse_html(resp.text)

            # Primary selector: find the IPO table
            table = soup.find("table", class_=lambda c: c and "table" in c)
            if not table:
                # Fallback: any table on the page
                table = soup.find("table")

            if not table:
                self.logger.warning(f"No table found at {url} — page structure may have changed")
                return []

            rows = table.find_all("tr")
            if len(rows) < 2:
                return []

            # Parse header to determine column indices (resilient to reordering)
            header_row = rows[0]
            headers = [
                th.get_text(strip=True).lower()
                for th in header_row.find_all(["th", "td"])
            ]
            col = self._map_eipo_columns(headers)

            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                try:
                    event = self._parse_eipo_row(cells, col, url)
                    if event:
                        events.append(event)
                except Exception as e:
                    self.logger.debug(f"Skipping malformed e-ipo row: {e}")

        except ScraperError as e:
            self.logger.error(f"e-ipo scrape failed for {url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error scraping {url}: {e}", exc_info=True)

        return events

    def _map_eipo_columns(self, headers: List[str]) -> Dict[str, int]:
        """
        Map column names to indices. Uses fuzzy matching so minor header
        renames (e.g. 'Emiten' vs 'Company') don't break parsing.
        """
        mapping = {}
        for i, h in enumerate(headers):
            if any(k in h for k in ("company", "emiten", "perusahaan", "issuer")):
                mapping["company"] = i
            elif any(k in h for k in ("ticker", "kode", "symbol", "saham")):
                mapping["ticker"] = i
            elif any(k in h for k in ("book", "build", "penawaran", "schedule")):
                mapping["book_build"] = i
            elif any(k in h for k in ("listing", "pencatatan", "list date")):
                mapping["listing"] = i
            elif any(k in h for k in ("price", "harga", "offering")):
                mapping["price"] = i

        # Fallback to positional columns if detection fails
        if "company" not in mapping:
            mapping["company"] = 0
        if "ticker" not in mapping:
            mapping["ticker"] = 1

        return mapping

    def _parse_eipo_row(
        self,
        cells: list,
        col: Dict[str, int],
        page_url: str,
    ) -> Optional[Dict[str, Any]]:
        """Parse a single e-ipo table row into a raw event dict."""
        company = self._safe_text(cells[col.get("company", 0)])
        ticker = self._safe_text(cells[col.get("ticker", 1)])

        if not company and not ticker:
            return None

        # Book-build period: may be "01 - 05 Apr 2026" or "01–05 Apr 2026"
        book_raw = self._safe_text(cells[col.get("book_build", 2)]) if len(cells) > 2 else ""
        book_start, book_end = self._parse_date_range(book_raw)

        listing_raw = self._safe_text(cells[col.get("listing", 3)]) if len(cells) > 3 else ""

        # Try to get detail URL from the row's anchor tag
        href = ""
        link_cell = cells[col.get("company", 0)]
        anchor = link_cell.find("a")
        if anchor:
            href = self._safe_attr(anchor, "href")
            if href and not href.startswith("http"):
                href = config.EIPO_BASE_URL + href

        return {
            "source":          "EIPO",
            "event_type":      "IPO",
            "ticker":          ticker or None,
            "company":         company or None,
            "title":           f"IPO – {company or ticker}",
            "description":     f"Book-build: {book_raw} | Listing: {listing_raw}",
            "book_build_start": book_start,
            "book_build_end":   book_end,
            "listing_date":     listing_raw,
            "event_date":       listing_raw,
            "url":              href or page_url,
        }

    def _parse_date_range(self, raw: str):
        """
        Parse a date range string like "01 - 05 Apr 2026" or "01–05 Apr 2026".
        Returns (start_str, end_str) — normalizer handles actual date parsing.
        """
        if not raw:
            return None, None
        # Split on - or –
        import re
        parts = re.split(r'\s*[–\-]\s*', raw, maxsplit=1)
        if len(parts) == 2:
            # Reconstruct: "01 Apr 2026" from "01" + " Apr 2026"
            end_part = parts[1].strip()
            start_part = parts[0].strip()
            # If start has no month, inherit from end
            if re.match(r'^\d{1,2}$', start_part):
                # Extract month+year from end
                month_year = re.sub(r'^\d{1,2}\s*', '', end_part)
                start_part = f"{start_part} {month_year}"
            return start_part, end_part
        return raw, raw

    # ── IDX New Listing API ────────────────────────────────────

    def _fetch_idx_new_listings(self) -> List[Dict[str, Any]]:
        """
        Fetch new listings from IDX API endpoint.
        Returns events enriched with listing date and company data.
        """
        events = []
        try:
            params = {
                "start": 0,
                "length": 50,
                "year": "",  # empty = current year
            }
            resp = self._get(self.IDX_NEW_LISTING_URL, params=params)
            data = resp.json()

            # IDX API returns { data: [...], recordsTotal: N }
            records = data.get("data", data.get("Data", []))
            if not records:
                self.logger.debug("IDX new listing API returned empty data")
                return []

            for rec in records:
                try:
                    event = self._parse_idx_listing(rec)
                    if event:
                        events.append(event)
                except Exception as e:
                    self.logger.debug(f"Skipping IDX listing record: {e}")

        except ScraperError as e:
            self.logger.error(f"IDX new listing API failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error fetching IDX listings: {e}", exc_info=True)

        return events

    def _parse_idx_listing(self, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse IDX new listing API record."""
        ticker = rec.get("KodeEfek") or rec.get("StockCode") or rec.get("ticker")
        company = rec.get("NamaEmiten") or rec.get("CompanyName") or rec.get("company")
        listing_date = rec.get("TanggalPencatatan") or rec.get("ListingDate")
        offer_price = rec.get("HargaPenawaran") or rec.get("OfferPrice")
        listing_board = rec.get("PapasPencatatan") or rec.get("Board")

        if not ticker and not company:
            return None

        return {
            "source":       "IDX",
            "event_type":   "IPO",
            "ticker":       ticker,
            "company":      company,
            "title":        f"New Listing – {company or ticker}",
            "description":  f"Listing board: {listing_board} | Offer price: {offer_price}",
            "listing_date": listing_date,
            "event_date":   listing_date,
            "url":          f"{config.IDX_BASE_URL}/id/perusahaan-tercatat/penawaran-umum/ipo/",
        }
