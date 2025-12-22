from __future__ import annotations

from pathlib import Path

from tax_copilot.core.models import Finding, Report, Severity


def checklist_from_findings(findings: list[Finding]) -> list[str]:
    items: list[str] = []

    # Prioritize HIGH/MED and confirmations
    for f in findings:
        if f.severity in (Severity.HIGH, Severity.MEDIUM) or f.requires_confirmation:
            # Keep the checklist short and actionable
            items.append(f"{f.title}: {f.suggested_action}")

    # Deduplicate while preserving order
    seen = set()
    deduped: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            deduped.append(it)
    return deduped


def write_checklist_markdown(report: Report, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "checklist.md"
    lines = [f"# Before-you-file Checklist ({report.current_tax_year})", ""]
    for item in report.checklist_items:
        lines.append(f"- [ ] {item}")
    lines.append("")
    lines.append("---")
    lines.append("**Disclaimer**: tax-copilot is for informational purposes only and is not tax advice.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
