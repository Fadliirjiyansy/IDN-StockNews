#!/usr/bin/env python3
"""
Unit tests for helper functions (RSS parsing, formatting, etc.)
Run: python3 -m pytest tests/unit/ -v
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def format_briefing_message(items: list, date: str) -> str:
    """Format RSS items into a Telegram-ready briefing message."""
    header = f"📈 *IDN Market Briefing*\n🕘 {date}\n\n*Top News:*\n"
    lines = [f"{i+1}. {item['title']}" for i, item in enumerate(items[:5])]
    return header + "\n".join(lines) + "\n\n_Powered by IDN-StockNews_"


def test_format_briefing_message():
    items = [
        {"title": "IHSG Menguat 0.5%"},
        {"title": "Bank Indonesia Tahan Suku Bunga"},
    ]
    result = format_briefing_message(items, "10 March 2026")
    assert "IHSG Menguat" in result
    assert "Bank Indonesia" in result
    assert "IDN-StockNews" in result
    print("✅ test_format_briefing_message passed")


def test_rss_fixture_valid():
    fixture_path = os.path.join(os.path.dirname(__file__), "../fixtures/sample-rss-items.json")
    with open(fixture_path) as f:
        data = json.load(f)
    assert "items" in data
    assert len(data["items"]) > 0
    print("✅ test_rss_fixture_valid passed")


if __name__ == "__main__":
    print("=== Unit Tests ===\n")
    test_format_briefing_message()
    test_rss_fixture_valid()
    print("\n✅ All unit tests passed!")
