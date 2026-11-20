"""Helpers for displaying claim confidence and source-domain diversity."""

import math
from collections.abc import Iterable
from urllib.parse import urlsplit


def confidence_assessment(value: object) -> tuple[str, str, float | None]:
    if isinstance(value, bool):
        return "Unavailable", "No valid confidence score was provided.", None

    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError):
        return "Unavailable", "No valid confidence score was provided.", None

    if not math.isfinite(score) or not 0 <= score <= 1:
        return "Unavailable", "No valid confidence score was provided.", None
    if score >= 0.8:
        return (
            "High confidence",
            "Strong confidence in this assessment; review the cited evidence.",
            score,
        )
    if score >= 0.5:
        return (
            "Medium confidence",
            "Evidence is mixed or partial; review the cited sources.",
            score,
        )
    return (
        "Low confidence",
        "Evidence is limited; manual review is recommended.",
        score,
    )


def source_diversity(sources: Iterable[str]) -> dict[str, int]:
    counts = {
        "Academic (.edu)": 0,
        "Government (.gov)": 0,
        "Organization (.org)": 0,
        "Commercial (.com)": 0,
        "Other": 0,
    }

    for source in sources:
        if not isinstance(source, str) or not source.strip():
            continue
        try:
            parsed = urlsplit(source.strip())
            hostname = parsed.hostname
        except ValueError:
            hostname = None

        if not hostname or parsed.scheme.lower() not in {"http", "https"}:
            category = "Other"
        else:
            hostname = hostname.lower().rstrip(".")
            suffix = hostname.rsplit(".", 1)[-1]
            category = {
                "edu": "Academic (.edu)",
                "gov": "Government (.gov)",
                "org": "Organization (.org)",
                "com": "Commercial (.com)",
            }.get(suffix, "Other")
        counts[category] += 1

    return counts
