"""Formatting helpers for downloadable research reports."""

import re


def report_filename(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:60]
    return f"{slug or 'fact-check-report'}.md"


def report_to_markdown(report: dict) -> str:
    lines = [
        f"# Fact-check report: {report.get('topic', 'Research topic')}",
        "",
        f"**Completed:** {report.get('created_at', 'Unknown')}",
    ]

    document_name = report.get("document_name")
    if document_name:
        lines.extend(
            [
                f"**User-provided document:** {document_name}",
                "",
                "> Document content is provided for context and is not independently verified.",
            ]
        )

    lines.extend(["", report.get("research_draft", "").strip(), ""])

    conflicts = report.get("conflicts", [])
    if conflicts:
        lines.extend(["## Conflicting claims", ""])
        for conflict in conflicts:
            lines.extend(
                [
                    f"### {conflict.get('claim', 'Disagreement')}",
                    f"- Source A: {conflict.get('source_a_says', '')} "
                    f"({conflict.get('source_a_url', '')})",
                    f"- Source B: {conflict.get('source_b_says', '')} "
                    f"({conflict.get('source_b_url', '')})",
                    "",
                ]
            )

    checks = report.get("fact_checks", [])
    if checks:
        lines.extend(["## Claim verification", ""])
        for check in checks:
            evidence_url = check.get("evidence_url")
            evidence = f" — [Evidence]({evidence_url})" if evidence_url else ""
            reason = f"\n\n{check['reason']}" if check.get("reason") else ""
            lines.append(
                f"- **{check.get('verdict', 'Uncertain')}** "
                f"({check.get('confidence', 0):.0%} confidence): "
                f"{check.get('claim', '')}{evidence}{reason}"
            )
        lines.append("")
    elif report.get("fact_check_reason"):
        lines.extend(["## Claim verification", "", report["fact_check_reason"], ""])

    sources = report.get("sources", [])
    if sources:
        lines.extend(["## Sources", ""])
        lines.extend(f"- [S{index}]({url})" for index, url in enumerate(sources, 1))
        lines.append("")

    search_errors = report.get("search_errors", [])
    if search_errors:
        lines.extend(["## Search limitations", ""])
        lines.extend(f"- {error}" for error in search_errors)
        lines.append("")

    return "\n".join(lines).strip() + "\n"
