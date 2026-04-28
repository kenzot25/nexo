"""Tests for nexo dashboard module."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


class TestConversationDashboard:
    """Tests for dashboard.py module."""

    def test_compute_metrics_empty(self):
        """Test computing metrics with no sessions."""
        from nexo.dashboard import ConversationDashboard
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)
            dashboard = ConversationDashboard(store)

            metrics = dashboard.compute_metrics()

            assert metrics.total_sessions == 0
            assert metrics.total_turns == 0
            assert metrics.completion_rate == 0.0

    def test_compute_metrics_with_sessions(self):
        """Test computing metrics with actual sessions."""
        from nexo.dashboard import ConversationDashboard
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            # Create completed session
            checkpoint1 = Checkpoint(
                turn_id=2,
                current_node="booking_complete",
                path_history=["greeting", "booking", "complete"],
                collected_slots={"date": "2026-05-01"},
            )
            store.save_checkpoint("session_completed", checkpoint1)
            store.save_turn("session_completed", 1, "hello", "Hi!")
            store.save_turn("session_completed", 2, "book tour", "Done!")

            # Create abandoned session
            checkpoint2 = Checkpoint(
                turn_id=1,
                current_node="state_collecting",
                path_history=["greeting"],
            )
            store.save_checkpoint("session_abandoned", checkpoint2)
            store.save_turn("session_abandoned", 1, "hello", "Hi!")

            dashboard = ConversationDashboard(store)
            metrics = dashboard.compute_metrics()

            assert metrics.total_sessions == 2
            assert metrics.total_turns == 3
            assert metrics.avg_turns_per_session == 1.5

    def test_generate_report(self):
        """Test report generation."""
        from nexo.dashboard import ConversationDashboard
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)
            dashboard = ConversationDashboard(store)

            report = dashboard.generate_report()

            assert "CONVERSATION DASHBOARD REPORT" in report
            assert "Total Sessions:" in report
            assert "Completion Rate:" in report

    def test_get_metrics_json(self):
        """Test JSON metrics export."""
        from nexo.dashboard import ConversationDashboard
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)
            dashboard = ConversationDashboard(store)

            metrics_json = dashboard.get_metrics_json()

            assert "generated_at" in metrics_json
            assert "overview" in metrics_json
            assert "success" in metrics_json
            assert "quality" in metrics_json

    def test_export_report_md(self):
        """Test exporting report as markdown."""
        from nexo.dashboard import ConversationDashboard
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)
            dashboard = ConversationDashboard(store)

            output_path = Path(tmpdir) / "report.md"
            dashboard.export_report(output_path, format="md")

            assert output_path.exists()
            content = output_path.read_text()
            assert "CONVERSATION DASHBOARD REPORT" in content

    def test_export_report_json(self):
        """Test exporting report as JSON."""
        from nexo.dashboard import ConversationDashboard
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)
            dashboard = ConversationDashboard(store)

            output_path = Path(tmpdir) / "report.json"
            dashboard.export_report(output_path, format="json")

            assert output_path.exists()
            data = json.loads(output_path.read_text())
            assert "generated_at" in data
            assert "overview" in data

    def test_recommendations_generation(self):
        """Test that recommendations are generated based on metrics."""
        from nexo.dashboard import ConversationDashboard, ConversationMetrics
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)
            dashboard = ConversationDashboard(store)

            # Create metrics with high ambiguity rate
            metrics = ConversationMetrics(
                total_turns=100,
                total_sessions=10,
                ambiguous_inputs=25,  # 25% ambiguity rate
                fallback_count=20,  # 20% fallback rate
                completed_flows=3,  # 30% completion rate
                abandoned_flows=7,
                ambiguity_rate=0.25,
                fallback_rate=0.20,
                completion_rate=0.30,
            )

            report = dashboard.generate_report(metrics)

            assert "High ambiguity rate" in report
            assert "High fallback rate" in report
            assert "Low completion rate" in report

    def test_drop_off_points_tracking(self):
        """Test that drop-off points are tracked correctly."""
        from nexo.dashboard import ConversationDashboard
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            # Create sessions with turns that abandon at same point
            for i in range(3):
                checkpoint = Checkpoint(
                    turn_id=2,
                    current_node="state_collecting",
                    path_history=["greeting", "state_collecting"],
                )
                store.save_checkpoint(f"session_{i}", checkpoint)
                store.save_turn(f"session_{i}", 1, "hello", "Hi!")
                store.save_turn(f"session_{i}", 2, "book", "When?")

            dashboard = ConversationDashboard(store)
            metrics = dashboard.compute_metrics()

            # Drop-off points tracked for non-completed sessions
            assert metrics.abandoned_flows == 3


class TestDashboardCLI:
    """Tests for dashboard CLI functionality."""

    def test_create_dashboard_default_path(self):
        """Test creating dashboard with default db path."""
        from nexo.dashboard import create_dashboard

        dashboard = create_dashboard()

        assert dashboard is not None
        assert dashboard.store.db_path.exists()

    def test_create_dashboard_custom_path(self):
        """Test creating dashboard with custom db path."""
        from nexo.dashboard import create_dashboard

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "custom.db"
            dashboard = create_dashboard(db_path)

            assert dashboard.store.db_path == db_path
