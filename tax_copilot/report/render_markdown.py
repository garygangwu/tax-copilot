from __future__ import annotations

from pathlib import Path

from tax_copilot.core.models import Report, Severity


def render_report_markdown(report: Report) -> str:
    lines: list[str] = []

    title = f"tax-copilot Review Report ({report.current_tax_year})"
    lines.append(f"# {title}")
    lines.append("")

    if report.prior_tax_year is not None:
        lines.append(f"Compared against prior year: {report.prior_tax_year}")
    lines.append(f"Generated at: {report.generated_at}")
    lines.append("")

    c = report.summary_counts
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- 🔴 HIGH: {c.get(Severity.HIGH.value, 0)}")
    lines.append(f"- 🟡 MEDIUM: {c.get(Severity.MEDIUM.value, 0)}")
    lines.append(f"- 🟢 LOW: {c.get(Severity.LOW.value, 0)}")
    lines.append("")

    def section(sev: Severity, header: str) -> None:
        items = [f for f in report.findings if f.severity == sev]
        lines.append(f"## {header}")
        lines.append("")
        if not items:
            lines.append("(None)")
            lines.append("")
            return
        for i, f in enumerate(items, start=1):
            lines.append(f"### {i}. {f.title} ({f.rule_id})")
            lines.append("")
            lines.append(f"**What we saw**: {f.description}")
            lines.append("")
            lines.append(f"**What to do**: {f.suggested_action}")
            if f.requires_confirmation:
                lines.append("")
                lines.append("**Needs confirmation**: Yes")
            if f.affected_fields:
                lines.append("")
                lines.append(f"**Fields**: {', '.join(f.affected_fields)}")
            lines.append("")

    section(Severity.HIGH, "High risk (fix / verify before filing)")
    section(Severity.MEDIUM, "Needs confirmation (sanity checks)")
    section(Severity.LOW, "FYI")

    lines.append("## Before you file")
    lines.append("")
    for item in report.checklist_items:
        lines.append(f"- [ ] {item}")
    lines.append("")

    lines.append("---")
    lines.append("**Disclaimer**: tax-copilot is for informational purposes only and is not tax advice.")
    lines.append("")

    return "\n".join(lines)


def write_report_markdown(report: Report, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "report.md"
    path.write_text(render_report_markdown(report), encoding="utf-8")
    return path
