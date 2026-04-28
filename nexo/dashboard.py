"""Monitoring dashboard for conversation analytics.

Tracks metrics like fallback rate, ambiguity rate, drop-off points,
and failure mode distribution for conversation flows.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexo.session import SessionStore


@dataclass
class ConversationMetrics:
    """Aggregated metrics for conversation flows."""
    total_turns: int = 0
    total_sessions: int = 0
    ambiguous_inputs: int = 0
    fallback_count: int = 0
    completed_flows: int = 0
    abandoned_flows: int = 0
    failure_counts: dict[str, int] = field(default_factory=dict)
    drop_off_points: dict[str, int] = field(default_factory=dict)
    avg_turns_per_session: float = 0.0
    ambiguity_rate: float = 0.0
    fallback_rate: float = 0.0
    completion_rate: float = 0.0


class ConversationDashboard:
    """Dashboard for monitoring conversation health and performance.

    Usage:
        dashboard = ConversationDashboard(session_store)
        metrics = dashboard.compute_metrics()
        report = dashboard.generate_report(metrics)
    """

    def __init__(self, session_store: SessionStore):
        """Initialize dashboard with session store.

        Args:
            session_store: SessionStore instance to read conversation data from
        """
        self.store = session_store

    def compute_metrics(self) -> ConversationMetrics:
        """Compute aggregated metrics from all sessions.

        Returns:
            ConversationMetrics with computed statistics
        """
        metrics = ConversationMetrics()

        sessions = self.store.list_sessions()
        metrics.total_sessions = len(sessions)

        if not sessions:
            return metrics

        total_turns = 0
        ambiguous_count = 0
        fallback_count = 0
        failure_counts: dict[str, int] = defaultdict(int)
        drop_off_points: dict[str, int] = defaultdict(int)
        completed = 0
        abandoned = 0

        for session_id in sessions:
            turns = self.store.get_turns(session_id)
            checkpoint = self.store.load_checkpoint(session_id)

            if not turns:
                abandoned += 1
                continue

            total_turns += len(turns)

            # Analyze each turn
            for turn in turns:
                matched_nodes = turn.get("matched_nodes", [])

                # Check for ambiguity (multiple nodes matched)
                if len(matched_nodes) > 1:
                    ambiguous_count += 1

                # Check for failure states
                for node in matched_nodes:
                    if "failure" in node.lower():
                        failure_counts[node] += 1
                        fallback_count += 1

            # Determine session outcome
            if checkpoint:
                current_node = checkpoint.current_node
                if checkpoint.path_history:
                    last_node = checkpoint.path_history[-1]

                    # Check if completed (reached a "complete" or "resolved" state)
                    if any(kw in last_node.lower() for kw in ["complete", "resolved", "done"]):
                        completed += 1
                    else:
                        # Track drop-off point
                        drop_off_points[last_node] += 1

                        # Consider abandoned if no activity for a while
                        if checkpoint.paused_ttl:
                            try:
                                ttl = datetime.fromisoformat(checkpoint.paused_ttl)
                                if ttl < datetime.now(timezone.utc):
                                    abandoned += 1
                            except ValueError:
                                pass
                        else:
                            abandoned += 1

        metrics.total_turns = total_turns
        metrics.total_sessions = len(sessions)
        metrics.ambiguous_inputs = ambiguous_count
        metrics.fallback_count = fallback_count
        metrics.failure_counts = dict(failure_counts)
        metrics.drop_off_points = dict(drop_off_points)
        metrics.completed_flows = completed
        metrics.abandoned_flows = abandoned

        # Calculate rates
        if total_turns > 0:
            metrics.ambiguity_rate = ambiguous_count / total_turns
            metrics.fallback_rate = fallback_count / total_turns

        if len(sessions) > 0:
            metrics.avg_turns_per_session = total_turns / len(sessions)
            metrics.completion_rate = completed / len(sessions)

        return metrics

    def generate_report(self, metrics: ConversationMetrics | None = None) -> str:
        """Generate a human-readable metrics report.

        Args:
            metrics: Pre-computed metrics or None to compute

        Returns:
            Formatted report string
        """
        if metrics is None:
            metrics = self.compute_metrics()

        lines = [
            "=" * 60,
            "CONVERSATION DASHBOARD REPORT",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "=" * 60,
            "",
            "## Overview",
            "",
            f"Total Sessions: {metrics.total_sessions}",
            f"Total Turns: {metrics.total_turns}",
            f"Avg Turns/Session: {metrics.avg_turns_per_session:.2f}",
            "",
            "## Success Metrics",
            "",
            f"Completed Flows: {metrics.completed_flows}",
            f"Abandoned Flows: {metrics.abandoned_flows}",
            f"Completion Rate: {metrics.completion_rate:.1%}",
            "",
            "## Quality Metrics",
            "",
            f"Ambiguous Inputs: {metrics.ambiguous_inputs}",
            f"Ambiguity Rate: {metrics.ambiguity_rate:.1%}",
            "",
            f"Fallback Count: {metrics.fallback_count}",
            f"Fallback Rate: {metrics.fallback_rate:.1%}",
            "",
        ]

        if metrics.failure_counts:
            lines.extend([
                "## Failure Mode Distribution",
                "",
            ])
            for failure, count in sorted(metrics.failure_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {failure}: {count}")
            lines.append("")

        if metrics.drop_off_points:
            lines.extend([
                "## Top Drop-off Points",
                "",
            ])
            sorted_drops = sorted(metrics.drop_off_points.items(), key=lambda x: -x[1])[:10]
            for node, count in sorted_drops:
                lines.append(f"  {node}: {count} sessions")
            lines.append("")

        lines.extend([
            "=" * 60,
            "## Recommendations",
            "",
        ])

        # Generate recommendations based on metrics
        recommendations = []

        if metrics.ambiguity_rate > 0.2:
            recommendations.append(
                f"- High ambiguity rate ({metrics.ambiguity_rate:.1%}): "
                "Consider adding more specific triggers or improving intent definitions"
            )

        if metrics.fallback_rate > 0.15:
            recommendations.append(
                f"- High fallback rate ({metrics.fallback_rate:.1%}): "
                "Review failure state handling and recovery paths"
            )

        if metrics.completion_rate < 0.5:
            recommendations.append(
                f"- Low completion rate ({metrics.completion_rate:.1%}): "
                "Analyze drop-off points and simplify conversation flows"
            )

        if metrics.drop_off_points:
            top_drop = max(metrics.drop_off_points.items(), key=lambda x: x[1])
            recommendations.append(
                f"- Top drop-off point '{top_drop[0]}' ({top_drop[1]} sessions): "
                "Consider redesigning this step or adding escape options"
            )

        if not recommendations:
            recommendations.append("- All metrics within acceptable ranges")

        lines.extend(recommendations)
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def get_metrics_json(self, metrics: ConversationMetrics | None = None) -> dict[str, Any]:
        """Get metrics as a JSON-serializable dict.

        Args:
            metrics: Pre-computed metrics or None to compute

        Returns:
            Dict with all metrics
        """
        if metrics is None:
            metrics = self.compute_metrics()

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overview": {
                "total_sessions": metrics.total_sessions,
                "total_turns": metrics.total_turns,
                "avg_turns_per_session": metrics.avg_turns_per_session,
            },
            "success": {
                "completed_flows": metrics.completed_flows,
                "abandoned_flows": metrics.abandoned_flows,
                "completion_rate": metrics.completion_rate,
            },
            "quality": {
                "ambiguous_inputs": metrics.ambiguous_inputs,
                "ambiguity_rate": metrics.ambiguity_rate,
                "fallback_count": metrics.fallback_count,
                "fallback_rate": metrics.fallback_rate,
            },
            "failure_distribution": metrics.failure_counts,
            "drop_off_points": metrics.drop_off_points,
        }

    def export_report(self, output_path: Path | str, format: str = "md") -> Path:
        """Export report to file.

        Args:
            output_path: Path to write report
            format: Output format ('md' or 'json')

        Returns:
            Path to written file
        """
        output_path = Path(output_path)
        metrics = self.compute_metrics()

        if format == "json":
            content = json.dumps(self.get_metrics_json(metrics), indent=2)
        else:
            content = self.generate_report(metrics)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return output_path


def create_dashboard(db_path: Path | str | None = None) -> ConversationDashboard:
    """Create a dashboard instance with optional custom db path.

    Args:
        db_path: Path to sessions database (default: ~/.nexo/sessions.db)

    Returns:
        ConversationDashboard instance
    """
    store = SessionStore(db_path)
    return ConversationDashboard(store)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Conversation dashboard")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to sessions database",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for report",
    )
    parser.add_argument(
        "--format",
        choices=["md", "json"],
        default="md",
        help="Output format",
    )

    args = parser.parse_args()

    dashboard = create_dashboard(args.db)

    if args.output:
        path = dashboard.export_report(args.output, format=args.format)
        print(f"Report written to: {path}")
    else:
        print(dashboard.generate_report())
