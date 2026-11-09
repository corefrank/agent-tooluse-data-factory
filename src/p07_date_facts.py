"""Conservative date fact matching for P07's rule-based Agent verifier.

Supports ISO, numeric slash/dot, Chinese written dates, and English month names.
This is lexical date equivalence, NOT semantic entailment verification.
"""
from __future__ import annotations

import re
from datetime import date

_MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)
_MONTH_MAP = {name: i for i, name in enumerate(_MONTH_NAMES, 1)}
_MONTH_MAP.update({name[:3]: i for i, name in enumerate(_MONTH_NAMES, 1)})
_MONTH_MAP["sept"] = 9

# 2026-12-04, 2026/12/4, 2026.12.4, 2026 年 12 月 4 日
_NUMERIC = re.compile(
    r"(?<!\d)(?P<year>\d{4})\s*(?:[-/.]|年)\s*"
    r"(?P<month>\d{1,2})\s*(?:[-/.]|月)\s*"
    r"(?P<day>\d{1,2})\s*日?(?!\d)"
)
# December 4, 2026; Dec. 4, 2026
_MONTH_FIRST = re.compile(
    r"\b(?P<month>[A-Za-z]+)\.?\s+"
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?\s*,?\s+"
    r"(?P<year>\d{4})\b", re.IGNORECASE
)
# 4 December 2026; 4 Dec 2026
_DAY_FIRST = re.compile(
    r"\b(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(?P<month>[A-Za-z]+)\.?\s*,?\s+"
    r"(?P<year>\d{4})\b", re.IGNORECASE
)
_ISO_EXPECTED = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def _to_iso(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def extract_iso_dates(text: str) -> set[str]:
    """Return parsed calendar dates occurring in text, ignoring invalid dates."""
    found: set[str] = set()
    for match in _NUMERIC.finditer(text):
        parsed = _to_iso(int(match['year']), int(match['month']), int(match['day']))
        if parsed is not None:
            found.add(parsed)
    for pattern in (_MONTH_FIRST, _DAY_FIRST):
        for match in pattern.finditer(text):
            month = _MONTH_MAP.get(match['month'].lower())
            if month is None:
                continue
            parsed = _to_iso(int(match['year']), month, int(match['day']))
            if parsed is not None:
                found.add(parsed)
    return found


def match_date_fact(answer: str, keyword: str) -> bool | None:
    """For ISO-date keywords return fact presence; return None for other facts.

    Does not interpret negation or contradictory date statements. Keep a
    separate human/semantic audit for open-ended real-world answers.
    """
    if not _ISO_EXPECTED.fullmatch(keyword):
        return None
    try:
        target = date.fromisoformat(keyword).isoformat()
    except ValueError:
        return False
    return target in extract_iso_dates(answer)
