from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from tax_copilot.core.models import TaxProfile

# Import agentic components
from tax_copilot.agents.providers import create_provider
from tax_copilot.agents.precheck import QuestioningAgent
from tax_copilot.agents.storage import SessionStore, ProfileBuilder

# Load environment variables from .env file
load_dotenv(override=True)


def _load_profile(path: str) -> TaxProfile:
    p = Path(path)
    if not p.exists():
        raise click.ClickException(f"File not found: {path}")
    data = p.read_bytes()
    try:
        return TaxProfile.model_validate_json(data)
    except Exception as e:
        raise click.ClickException(f"Failed to parse TaxProfile JSON at {path}: {e!r}")


@click.group()
def cli() -> None:
    """tax-copilot CLI."""


@cli.command()
def test() -> None:
    """Test the CLI."""
    print("Test command executed")


@cli.command()
@click.option("--prior", type=str, required=False, help="Path to prior-year TaxProfile JSON")
@click.option("--current", type=str, required=True, help="Path to current-year TaxProfile JSON")
@click.option("--out", "out_dir", type=str, required=True, help="Output directory")
def review(prior: Optional[str], current: str, out_dir: str) -> None:
    """
    [DEPRECATED] Old rule-based review command.

    This command has been replaced by the new agentic system.
    Use 'tax-copilot precheck' to collect tax information instead.
    """
    click.echo(
        "=" * 60 + "\n"
        "DEPRECATED: This rule-based review command is no longer supported.\n\n"
        "The tax-copilot system has transitioned to a pure agentic approach.\n\n"
        "To collect tax information, use:\n"
        "  tax-copilot precheck --user <user_id> --year <tax_year>\n\n"
        "To view saved profiles, use:\n"
        "  tax-copilot profile --user <user_id> --year <tax_year>\n"
        + "=" * 60
    )


@cli.command()
@click.option("--user", type=str, help="User ID for new interview")
@click.option("--year", type=int, help="Tax year for new interview")
@click.option("--session", type=str, help="Resume existing session by ID")
@click.option("--list", "list_sessions", is_flag=True, help="List active sessions")
@click.option(
    "--force-complete",
    is_flag=True,
    help="Force completion of a stuck session (use with --session)",
)
@click.option(
    "--llm-provider",
    type=click.Choice(["anthropic", "openai"], case_sensitive=False),
    default=lambda: os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
    help="LLM provider to use (default: from DEFAULT_LLM_PROVIDER env var or 'openai')",
)
def precheck(
    user: Optional[str],
    year: Optional[int],
    session: Optional[str],
    list_sessions: bool,
    force_complete: bool,
    llm_provider: str,
) -> None:
    """
    Interactive tax information collection via dynamic questioning.

    Start a new interview:
        tax-copilot precheck --user john --year 2024

    Resume an existing session:
        tax-copilot precheck --session sess_20240115_103000_abc123

    Force complete a stuck session:
        tax-copilot precheck --session sess_xxx --force-complete

    List all sessions:
        tax-copilot precheck --list

    List sessions for a specific user:
        tax-copilot precheck --list --user john
    """
    asyncio.run(_run_precheck(user, year, session, list_sessions, force_complete, llm_provider))


async def _run_precheck(
    user: Optional[str],
    year: Optional[int],
    session_id: Optional[str],
    list_sessions: bool,
    force_complete: bool,
    llm_provider: str,
) -> None:
    """Async implementation of precheck command."""

    # Initialize storage
    storage = SessionStore()

    # Handle --force-complete flag
    if force_complete:
        if not session_id:
            click.echo("Error: --force-complete requires --session", err=True)
            return

        click.echo(f"\n=== Force Completing Session {session_id} ===\n")

        # Initialize LLM provider
        try:
            provider = create_provider(provider_name=llm_provider)
        except Exception as e:
            click.echo(f"Error initializing {llm_provider} provider: {e}", err=True)
            return

        # Initialize agent and force complete
        agent = QuestioningAgent(llm_provider=provider, storage=storage)

        try:
            # Load session
            from tax_copilot.agents.precheck.data_organizer import DataOrganizer
            from tax_copilot.core.conversation import ConversationState

            session = storage.load_session(session_id)

            click.echo(f"Current state: {session.state.value}")
            click.echo(f"Topics covered: {session.topics_covered}")
            click.echo(f"Topics remaining: {session.topics_remaining}\n")

            # Force transition to COMPLETED
            session.transition_state(ConversationState.COMPLETED)

            # Reorganize data
            click.echo("Reorganizing extracted data...")
            organizer = DataOrganizer(provider)
            organized_data = await organizer.organize(session)
            session.extracted_data = organized_data
            storage.save_session(session)

            # Build profile
            click.echo("Building tax profile...")
            profile = agent.profile_builder.build_from_session(session)

            # Save profile
            agent.profile_builder.save_profile(profile, user_id=session.user_id)

            click.echo("\n" + "=" * 50)
            click.echo("Session Force Completed Successfully!")
            click.echo("=" * 50)
            click.echo(f"\nTax profile saved to:")
            click.echo(f"  ~/.tax_copilot/profiles/{session.user_id}_{session.tax_year}.json\n")

        except Exception as e:
            click.echo(f"\nError during force completion: {e}", err=True)
            import traceback
            traceback.print_exc()

        return

    # Handle --list flag
    if list_sessions:
        sessions = storage.list_sessions(user_id=user, tax_year=year)

        if not sessions:
            filter_msg = ""
            if user:
                filter_msg += f" for user '{user}'"
            if year:
                filter_msg += f" for year {year}"
            click.echo(f"No sessions found{filter_msg}.")
            return

        click.echo("\n=== Active Sessions ===\n")
        for sess in sessions:
            click.echo(f"Session ID: {sess.session_id}")
            click.echo(f"  User: {sess.user_id}")
            click.echo(f"  Tax Year: {sess.tax_year}")
            click.echo(f"  State: {sess.state.value}")
            click.echo(f"  Updated: {sess.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"  Messages: {len(sess.messages)}")
            click.echo()

        return

    # Initialize LLM provider
    try:
        print(f"Initializing {llm_provider} provider")
        provider = create_provider(provider_name=llm_provider)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return
    except Exception as e:
        click.echo(
            f"Error initializing {llm_provider} provider: {e}\n"
            f"Make sure you've set the appropriate API key environment variable.",
            err=True,
        )
        return

    # Initialize agent
    agent = QuestioningAgent(llm_provider=provider, storage=storage)

    # Resume or start new interview
    if session_id:
        # Resume existing session
        resume_info = await agent.resume_interview(session_id)

        if "error" in resume_info:
            click.echo(f"Error: {resume_info['error']}", err=True)
            return

        click.echo(f"\n=== Resuming Interview (Tax Year {resume_info['tax_year']}) ===")
        click.echo(f"Session: {resume_info['session_id']}")
        click.echo(f"State: {resume_info['session_state']}")
        click.echo(f"Messages so far: {resume_info['messages_count']}\n")
        click.echo(f"Agent: {resume_info['last_question']}\n")

        current_session_id = session_id
        user = resume_info['user_id']

    else:
        # Start new interview
        if not user or not year:
            click.echo(
                "Error: --user and --year required for new interview.\n"
                "Or use --session to resume existing interview.",
                err=True,
            )
            return

        click.echo(f"\n=== Starting New Interview (Tax Year {year}) ===\n")

        result = await agent.start_interview(user_id=user, tax_year=year)
        current_session_id = result["session_id"]

        click.echo(f"Agent: {result['first_question']}\n")

    # Interactive conversation loop
    while True:
        try:
            # Get user input
            user_input = click.prompt("You", type=str, prompt_suffix=": ")

            # Handle exit commands
            if user_input.lower() in ["exit", "quit", "bye"]:
                click.echo(
                    f"\nInterview paused. Resume anytime with:\n"
                    f"  tax-copilot precheck --session {current_session_id}\n"
                )
                break

            # Process user input
            result = await agent.continue_interview(current_session_id, user_input)

            if "error" in result:
                click.echo(f"\nError: {result['error']}\n", err=True)
                continue

            # Display agent response
            click.echo(f"\nAgent: {result['agent_response']}\n")

            # Check if complete
            if result["is_complete"]:
                profile = result.get("profile")

                if profile:
                    click.echo("=" * 50)
                    click.echo("Interview Complete!")
                    click.echo("=" * 50)
                    click.echo(
                        f"\nYour tax profile has been saved to:\n"
                        f"  ~/.tax_copilot/profiles/{user}_{profile.tax_year}.json\n"
                    )
                    click.echo("You can now use this profile for tax analysis.")
                else:
                    click.echo("\nInterview complete, but profile could not be saved.")

                break

        except KeyboardInterrupt:
            click.echo(
                f"\n\nInterview paused. Resume anytime with:\n"
                f"  tax-copilot precheck --session {current_session_id}\n"
            )
            break
        except EOFError:
            break


@cli.command()
@click.option("--user", type=str, required=True, help="User ID")
@click.option("--year", type=int, required=True, help="Tax year")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["summary", "json"], case_sensitive=False),
    default="summary",
    help="Output format (default: summary)",
)
@click.option("--out", type=str, help="Output file path (for json format)")
def profile(user: str, year: int, output_format: str, out: Optional[str]) -> None:
    """
    View or export saved tax profiles.

    View profile summary:
        tax-copilot profile --user john --year 2024

    Export to JSON file:
        tax-copilot profile --user john --year 2024 --format json --out profile.json
    """
    builder = ProfileBuilder()

    try:
        tax_profile = builder.load_profile(user_id=user, tax_year=year)
    except FileNotFoundError:
        click.echo(f"Profile not found for user '{user}' and year {year}.", err=True)
        click.echo(
            f"\nTip: Create a profile first using:\n"
            f"  tax-copilot precheck --user {user} --year {year}"
        )
        return

    if output_format == "json":
        # Export to JSON
        if out:
            output_path = Path(out)
            output_path.write_text(tax_profile.model_dump_json(indent=2))
            click.echo(f"Profile exported to: {output_path}")
        else:
            # Print to stdout
            click.echo(tax_profile.model_dump_json(indent=2))

    else:
        # Display summary
        click.echo(f"\n=== Tax Profile: {user} ({year}) ===\n")
        click.echo(f"Filing Status: {tax_profile.filing_status}")

        if tax_profile.state:
            click.echo(f"State: {tax_profile.state}")

        click.echo(f"\nIncome:")
        click.echo(f"  Total Income: {tax_profile.income.total_income}")
        click.echo(f"  W-2 Jobs: {tax_profile.income.w2_count}")
        click.echo(f"  IRA Contribution: {tax_profile.income.ira_contribution}")

        click.echo(f"\nDeductions:")
        click.echo(
            f"  Student Loan Interest: {tax_profile.deductions.student_loan_interest}"
        )
        click.echo(f"  Itemized: {tax_profile.deductions.itemized}")
        if tax_profile.deductions.itemized:
            click.echo(
                f"  Itemized Total: {tax_profile.deductions.itemized_total}"
            )

        click.echo(f"\nDependents:")
        click.echo(f"  Count: {tax_profile.dependents.count}")
        if tax_profile.dependents.count > 0:
            click.echo(f"  Ages: {tax_profile.dependents.ages}")
            click.echo(
                f"  Claiming Child Tax Credit: {tax_profile.dependents.claiming_child_tax_credit}"
            )

        click.echo(f"\nMetadata:")
        click.echo(f"  Collected via: {tax_profile.collected_via}")
        if tax_profile.session_id:
            click.echo(f"  Session ID: {tax_profile.session_id}")
        if tax_profile.created_at:
            click.echo(f"  Created: {tax_profile.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if tax_profile.updated_at:
            click.echo(f"  Updated: {tax_profile.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if tax_profile.confidence_scores:
            click.echo(f"\nConfidence Scores:")
            for field, score in sorted(tax_profile.confidence_scores.items()):
                click.echo(f"  {field}: {score:.2f}")

        click.echo()


@cli.command()
@click.option("--user", type=str, help="User ID (loads latest profile for this user)")
@click.option("--profile-id", type=str, help="Specific profile ID to analyze")
@click.option(
    "--interactive",
    is_flag=True,
    help="Enable interactive mode (ask follow-up questions)",
)
@click.option(
    "--output",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    help="Output format (default: markdown)",
)
@click.option("--save", is_flag=True, help="Save report to disk")
@click.option(
    "--llm-provider",
    type=click.Choice(["anthropic", "openai"], case_sensitive=False),
    default=lambda: os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
    help="LLM provider to use (default: from DEFAULT_LLM_PROVIDER env var or 'openai')",
)
def analyze(
    user: Optional[str],
    profile_id: Optional[str],
    interactive: bool,
    output: str,
    save: bool,
    llm_provider: str,
) -> None:
    """
    Analyze tax profile and generate advisory report.

    Analyze latest profile for user:
        tax-copilot analyze --user john

    Analyze specific profile:
        tax-copilot analyze --profile-id prof_20240115_abc123

    Interactive mode (ask follow-up questions):
        tax-copilot analyze --user john --interactive

    Save report to disk:
        tax-copilot analyze --user john --save

    Export to JSON:
        tax-copilot analyze --user john --output json > report.json
    """
    asyncio.run(_run_analyze(user, profile_id, interactive, output, save, llm_provider))


async def _run_analyze(
    user: Optional[str],
    profile_id: Optional[str],
    interactive: bool,
    output: str,
    save: bool,
    llm_provider: str,
) -> None:
    """Async implementation of analyze command."""
    from tax_copilot.agents.advisory import AdvisoryAgent

    # Initialize LLM provider
    try:
        provider = create_provider(provider_name=llm_provider)
    except Exception as e:
        click.echo(
            f"Error initializing {llm_provider} provider: {e}\n"
            f"Make sure you've set the appropriate API key environment variable.",
            err=True,
        )
        return

    # Initialize advisory agent
    advisor = AdvisoryAgent(llm_provider=provider)

    # Load profile
    try:
        if profile_id:
            # Load specific profile by ID
            profile = advisor.profile_builder.load_profile_by_id(profile_id)
        elif user:
            # Load latest profile for user
            profile = advisor.get_latest_profile(user_id=user)
            if not profile:
                click.echo(
                    f"No profiles found for user '{user}'.\n\n"
                    f"Create a profile first using:\n"
                    f"  tax-copilot precheck --user {user} --year 2024",
                    err=True,
                )
                return
        else:
            click.echo(
                "Error: Either --user or --profile-id required.\n\n"
                "Examples:\n"
                "  tax-copilot analyze --user john\n"
                "  tax-copilot analyze --profile-id prof_20240115_abc123",
                err=True,
            )
            return

    except FileNotFoundError as e:
        click.echo(f"Profile not found: {e}", err=True)
        return

    # Display profile info
    click.echo(f"\n=== Analyzing Tax Profile ===")
    click.echo(f"User: {getattr(profile, 'user_id', 'unknown')}")
    click.echo(f"Tax Year: {profile.tax_year}")
    click.echo(f"Income: {profile.income.total_income}")
    click.echo(f"Filing Status: {profile.filing_status}")
    click.echo()

    # Run analysis
    try:
        report = await advisor.analyze_profile(profile, interactive=interactive)

        # Save report if requested
        if save:
            report_path = advisor.save_report(
                report, user_id=getattr(profile, "user_id", "unknown")
            )
            click.echo(f"\nReport saved to: {report_path}\n")

        # Display report
        if output == "json":
            # JSON output
            click.echo(advisor.report_generator.to_json(report))
        else:
            # Markdown output
            markdown = advisor.report_generator.to_markdown(report, profile)
            click.echo("\n" + markdown)

    except Exception as e:
        click.echo(f"\nError during analysis: {e}", err=True)
        import traceback
        traceback.print_exc()


@cli.command()
@click.option("--user", type=str, help="Filter by user ID")
@click.option("--report-id", type=str, help="View specific report")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["summary", "markdown", "json"], case_sensitive=False),
    default="summary",
    help="Output format (default: summary)",
)
def reports(user: Optional[str], report_id: Optional[str], output_format: str) -> None:
    """
    List or view saved advisory reports.

    List all reports:
        tax-copilot reports

    List reports for specific user:
        tax-copilot reports --user john

    View specific report:
        tax-copilot reports --report-id rpt_20240115_abc123

    View report as JSON:
        tax-copilot reports --report-id rpt_xxx --format json
    """
    asyncio.run(_run_reports(user, report_id, output_format))


async def _run_reports(
    user: Optional[str], report_id: Optional[str], output_format: str
) -> None:
    """Async implementation of reports command."""
    from tax_copilot.agents.advisory import AdvisoryAgent
    from tax_copilot.agents.providers.openai_provider import OpenAIProvider

    # Initialize advisor (just for report access, no LLM calls)
    try:
        provider = create_provider(provider_name="openai")
    except:
        # Fallback - we don't actually need LLM for listing reports
        provider = None

    if provider:
        advisor = AdvisoryAgent(llm_provider=provider)
    else:
        # Create minimal advisor just for report access
        from tax_copilot.agents.providers.base import LLMProvider

        class DummyProvider(LLMProvider):
            async def generate(self, **kwargs):
                pass

        advisor = AdvisoryAgent(llm_provider=DummyProvider())

    # View specific report
    if report_id:
        try:
            report = advisor.load_report(report_id)

            if output_format == "json":
                click.echo(advisor.report_generator.to_json(report))
            elif output_format == "markdown":
                # Need to load profile to render markdown properly
                if report.profile_id:
                    try:
                        profile = advisor.profile_builder.load_profile_by_id(report.profile_id)
                    except:
                        # Create minimal profile from report data
                        from tax_copilot.core.models import TaxProfile, Income, Deductions, Dependents
                        profile = TaxProfile(
                            tax_year=report.tax_year,
                            filing_status="unknown",
                            income=Income(),
                            deductions=Deductions(),
                            dependents=Dependents(),
                        )
                else:
                    from tax_copilot.core.models import TaxProfile, Income, Deductions, Dependents
                    profile = TaxProfile(
                        tax_year=report.tax_year,
                        filing_status="unknown",
                        income=Income(),
                        deductions=Deductions(),
                        dependents=Dependents(),
                    )

                markdown = advisor.report_generator.to_markdown(report, profile)
                click.echo(markdown)
            else:
                # Summary format
                click.echo(f"\n=== Tax Advisory Report ===")
                click.echo(f"Report ID: {report.report_id}")
                click.echo(f"User: {report.user_id}")
                click.echo(f"Tax Year: {report.tax_year}")
                click.echo(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                click.echo(f"\nTotal Tax: {report.tax_calculation.total_tax}")
                click.echo(f"Effective Rate: {report.tax_calculation.effective_tax_rate:.1f}%")
                click.echo(
                    f"Potential Savings: {advisor.report_generator._format_money_cents(report.optimization_report.total_potential_savings.cents + report.deduction_finder_report.total_potential_savings.cents)}"
                )
                click.echo(f"\nStrategies: {len(report.optimization_report.strategies)}")
                click.echo(
                    f"Missed Deductions: {len(report.deduction_finder_report.missed_deductions)}"
                )
                click.echo()

        except FileNotFoundError:
            click.echo(f"Report not found: {report_id}", err=True)
            return
        except Exception as e:
            click.echo(f"Error loading report: {e}", err=True)
            import traceback
            traceback.print_exc()
            return

    else:
        # List reports
        report_summaries = advisor.list_reports(user_id=user)

        if not report_summaries:
            filter_msg = f" for user '{user}'" if user else ""
            click.echo(f"No reports found{filter_msg}.")
            return

        click.echo("\n=== Saved Reports ===\n")
        for summary in report_summaries:
            click.echo(f"Report ID: {summary['report_id']}")
            click.echo(f"  User: {summary['user_id']}")
            click.echo(f"  Tax Year: {summary['tax_year']}")

            if summary.get("generated_at"):
                from datetime import datetime
                try:
                    gen_time = datetime.fromisoformat(summary["generated_at"])
                    click.echo(f"  Generated: {gen_time.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    click.echo(f"  Generated: {summary['generated_at']}")

            # Format total_tax and potential_savings
            if isinstance(summary.get("total_tax"), dict):
                total_tax_cents = summary["total_tax"].get("cents", 0)
            else:
                total_tax_cents = summary.get("total_tax", 0)

            if isinstance(summary.get("potential_savings"), dict):
                savings_cents = summary["potential_savings"].get("cents", 0)
            else:
                savings_cents = summary.get("potential_savings", 0)

            click.echo(f"  Total Tax: ${total_tax_cents / 100:,.2f}")
            click.echo(f"  Potential Savings: ${savings_cents / 100:,.2f}")
            click.echo()


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
