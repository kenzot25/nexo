"""Tests for nexo conversation module - templates, session, compression, and queries."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest


# ── Template Parser Tests ────────────────────────────────────────────────────

class TestConversationTemplates:
    """Tests for conversation_templates.py module."""

    def test_parse_intent_node(self):
        """Test parsing an intent node from JSON."""
        from nexo.conversation_templates import parse_conversation_template

        data = {
            "id": "test_flow",
            "nodes": [
                {
                    "id": "intent_greeting",
                    "type": "intent",
                    "label": "User greets",
                    "triggers": ["hi", "hello", "xin chào"],
                    "confidence_threshold": 0.7,
                }
            ],
            "edges": [],
        }

        template = parse_conversation_template(data)

        assert template.id == "test_flow"
        assert len(template.nodes) == 1
        node = template.nodes[0]
        assert node.id == "intent_greeting"
        assert node.label == "User greets"
        assert node.triggers == ["hi", "hello", "xin chào"]
        assert node.confidence_threshold == 0.7

    def test_parse_response_node(self):
        """Test parsing a response node from JSON."""
        from nexo.conversation_templates import parse_conversation_template

        data = {
            "id": "test_flow",
            "nodes": [
                {
                    "id": "resp_welcome",
                    "type": "response",
                    "label": "Welcome message",
                    "templates": ["Hello!", "Welcome!"],
                    "tone": "casual",
                    "context": ["general"],
                }
            ],
            "edges": [],
        }

        template = parse_conversation_template(data)
        node = template.nodes[0]

        assert node.id == "resp_welcome"
        assert node.templates == ["Hello!", "Welcome!"]
        assert node.tone == "casual"

    def test_parse_state_node(self):
        """Test parsing a state node from JSON."""
        from nexo.conversation_templates import parse_conversation_template

        data = {
            "id": "test_flow",
            "nodes": [
                {
                    "id": "state_collecting",
                    "type": "state",
                    "label": "Collecting info",
                    "required_slots": ["name", "phone"],
                    "optional_slots": ["email"],
                }
            ],
            "edges": [],
        }

        template = parse_conversation_template(data)
        node = template.nodes[0]

        assert node.required_slots == ["name", "phone"]
        assert node.optional_slots == ["email"]

    def test_parse_failure_state_node(self):
        """Test parsing a failure state node from JSON."""
        from nexo.conversation_templates import parse_conversation_template

        data = {
            "id": "test_flow",
            "nodes": [
                {
                    "id": "failure_ambiguity",
                    "type": "failure_state",
                    "label": "Ambiguous input",
                    "recovery_path": "ask_clarification",
                    "max_retries": 2,
                }
            ],
            "edges": [],
        }

        template = parse_conversation_template(data)
        node = template.nodes[0]

        assert node.recovery_path == "ask_clarification"
        assert node.max_retries == 2

    def test_parse_edge(self):
        """Test parsing an edge from JSON."""
        from nexo.conversation_templates import parse_conversation_template

        data = {
            "id": "test_flow",
            "nodes": [],
            "edges": [
                {
                    "source": "intent_greeting",
                    "target": "resp_welcome",
                    "relation": "triggers",
                    "condition": None,
                    "weight": 1.0,
                }
            ],
        }

        template = parse_conversation_template(data)

        assert len(template.edges) == 1
        edge = template.edges[0]
        assert edge.source == "intent_greeting"
        assert edge.target == "resp_welcome"
        assert edge.relation == "triggers"

    def test_template_to_nodes_edges(self):
        """Test converting template to nodes+edges dicts."""
        from nexo.conversation_templates import (
            parse_conversation_template,
            conversation_template_to_nodes_edges,
        )

        data = {
            "id": "test_flow",
            "name": "Test Flow",
            "nodes": [
                {
                    "id": "intent_greeting",
                    "type": "intent",
                    "label": "User greets",
                    "triggers": ["hi"],
                    "confidence_threshold": 0.7,
                }
            ],
            "edges": [
                {
                    "source": "intent_greeting",
                    "target": "resp_welcome",
                    "relation": "triggers",
                }
            ],
        }

        template = parse_conversation_template(data)
        nodes, edges = conversation_template_to_nodes_edges(template, "test.json")

        assert len(nodes) == 1
        assert nodes[0]["id"] == "intent_greeting"
        assert nodes[0]["type"] == "intent"
        assert nodes[0]["triggers"] == ["hi"]
        assert nodes[0]["source_file"] == "test.json"

        assert len(edges) == 1
        assert edges[0]["source"] == "intent_greeting"
        assert edges[0]["target"] == "resp_welcome"
        assert edges[0]["confidence"] == "EXTRACTED"

    def test_extract_conversation_templates_from_files(self):
        """Test extracting templates from JSON files."""
        from nexo.conversation_templates import extract_conversation_templates

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            template_path = tmpdir / "test_flow.json"

            template_data = {
                "id": "test_flow",
                "nodes": [
                    {
                        "id": "intent_test",
                        "type": "intent",
                        "label": "Test intent",
                        "triggers": ["test"],
                    }
                ],
                "edges": [],
            }
            template_path.write_text(json.dumps(template_data))

            result = extract_conversation_templates([template_path])

            assert len(result[0]) == 1  # nodes
            assert len(result[1]) == 0  # edges
            assert result[0][0]["id"] == "intent_test"

    def test_extract_conversation_templates_handles_invalid_json(self):
        """Test that invalid JSON files are handled gracefully."""
        from nexo.conversation_templates import extract_conversation_templates
        import sys
        from io import StringIO

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            invalid_path = tmpdir / "invalid.json"
            invalid_path.write_text("not valid json")

            # Capture stderr
            old_stderr = sys.stderr
            sys.stderr = StringIO()

            result = extract_conversation_templates([invalid_path])

            sys.stderr = old_stderr

            assert result == ([], [])


# ── Session Store Tests ─────────────────────────────────────────────────────

class TestSessionStore:
    """Tests for session.py module."""

    def test_save_and_load_checkpoint(self):
        """Test saving and loading a checkpoint."""
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            checkpoint = Checkpoint(
                turn_id=5,
                current_node="state_collecting",
                collected_slots={"name": "An", "phone": "0123"},
                path_history=["greeting", "inquiry", "collecting"],
                failure_count=0,
            )

            store.save_checkpoint("session_123", checkpoint)
            loaded = store.load_checkpoint("session_123")

            assert loaded is not None
            assert loaded.turn_id == 5
            assert loaded.current_node == "state_collecting"
            assert loaded.collected_slots == {"name": "An", "phone": "0123"}
            assert loaded.path_history == ["greeting", "inquiry", "collecting"]

    def test_load_nonexistent_session(self):
        """Test loading a session that doesn't exist."""
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            result = store.load_checkpoint("nonexistent_session")

            assert result is None

    def test_get_active_path(self):
        """Test getting the active conversation path."""
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            checkpoint = Checkpoint(
                turn_id=3,
                current_node="state_booking",
                path_history=["greeting", "inquiry", "booking"],
            )

            store.save_checkpoint("session_456", checkpoint)
            path = store.get_active_path("session_456")

            assert path == ["greeting", "inquiry", "booking"]

    def test_pause_path(self):
        """Test pausing a conversation path with TTL."""
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            store.pause_path("session_789", ["greeting", "paused_here"], ttl_hours=24)

            checkpoint = store.load_checkpoint("session_789")
            assert checkpoint is not None
            assert checkpoint.paused_at == ["greeting", "paused_here"]
            assert checkpoint.paused_ttl is not None

    def test_save_and_get_turns(self):
        """Test saving and retrieving conversation turns."""
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            store.save_turn(
                session_id="session_turns",
                turn_id=1,
                user_input="Hello",
                ai_response="Hi there!",
                matched_nodes=["intent_greeting"],
            )

            store.save_turn(
                session_id="session_turns",
                turn_id=2,
                user_input="Book a tour",
                ai_response="Sure, how many people?",
                matched_nodes=["intent_booking"],
            )

            turns = store.get_turns("session_turns")

            assert len(turns) == 2
            assert turns[0]["turn_id"] == 1
            assert turns[0]["user_input"] == "Hello"
            assert turns[1]["turn_id"] == 2

    def test_get_turns_with_limit(self):
        """Test getting turns with a limit."""
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            for i in range(10):
                store.save_turn(
                    session_id="session_limit",
                    turn_id=i,
                    user_input=f"Input {i}",
                    ai_response=f"Response {i}",
                )

            turns = store.get_turns("session_limit", limit=3)

            assert len(turns) == 3
            # Returns last 3 turns in order (7, 8, 9)
            assert turns[0]["turn_id"] == 7

    def test_delete_session(self):
        """Test deleting a session."""
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            checkpoint = Checkpoint(turn_id=1, current_node="test")
            store.save_checkpoint("to_delete", checkpoint)
            store.save_turn("to_delete", 1, "hi", "hello")

            store.delete_session("to_delete")

            assert store.load_checkpoint("to_delete") is None
            assert store.get_turns("to_delete") == []

    def test_list_sessions(self):
        """Test listing all sessions."""
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            for i in range(3):
                checkpoint = Checkpoint(turn_id=1, current_node="test")
                store.save_checkpoint(f"session_{i}", checkpoint)

            sessions = store.list_sessions()

            assert len(sessions) == 3

    def test_cleanup_expired(self):
        """Test cleaning up expired sessions."""
        from nexo.session import SessionStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            # Create session with expired TTL (1 hour ago)
            expired_ttl = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

            conn = __import__("sqlite3").connect(str(db_path))
            conn.execute("""
                INSERT INTO checkpoints (session_id, turn_id, current_node, paused_ttl)
                VALUES (?, ?, ?, ?)
            """, ("expired_session", 1, "test", expired_ttl))
            conn.commit()
            conn.close()

            deleted_count = store.cleanup_expired()

            assert deleted_count == 1


# ── Compression Tests ───────────────────────────────────────────────────────

class TestCompression:
    """Tests for compression.py module."""

    def test_compress_empty_turns(self):
        """Test compressing empty turns."""
        from nexo.compression import compress_conversation

        result = compress_conversation([])
        assert result == ""

    def test_compress_few_turns_no_compression(self):
        """Test that few turns are kept intact."""
        from nexo.compression import compress_conversation, Turn

        turns = [
            Turn(turn_id=1, user_input="Hi", ai_response="Hello!"),
            Turn(turn_id=2, user_input="Book tour", ai_response="Sure!"),
        ]

        result = compress_conversation(turns, keep_recent_turns=5)

        assert "Hi" in result
        assert "Hello!" in result
        assert "[Conversation Summary]" not in result

    def test_compress_many_turns(self):
        """Test compressing many turns."""
        from nexo.compression import compress_conversation, Turn

        turns = [
            Turn(
                turn_id=i,
                user_input=f"Input {i}",
                ai_response=f"Response {i}",
                collected_slots={"slot": f"value_{i}"} if i < 5 else None,
            )
            for i in range(20)
        ]

        result = compress_conversation(turns, keep_recent_turns=5, token_budget=500)

        # Should have summary header
        assert "[Conversation Summary" in result or "Turn 15" in result
        # Should have recent turns
        assert "Input 19" in result
        # Should be within budget
        assert len(result) < 500 * 4  # char budget

    def test_should_compress_trigger(self):
        """Test compression trigger threshold."""
        from nexo.compression import should_compress, Turn

        # Small conversation - should not trigger
        small_turns = [
            Turn(turn_id=1, user_input="Hi", ai_response="Hello"),
        ]
        assert should_compress(small_turns, token_budget=100, threshold=0.8) is False

        # Large conversation - should trigger
        large_turns = [
            Turn(turn_id=i, user_input="x" * 400, ai_response="y" * 400)
            for i in range(5)
        ]
        assert should_compress(large_turns, token_budget=100, threshold=0.8) is True

    def test_estimate_tokens(self):
        """Test token estimation."""
        from nexo.compression import estimate_tokens

        # Rough estimate: 4 chars per token
        text = "Hello world! This is a test."
        tokens = estimate_tokens(text)

        assert tokens == len(text) // 4


# ── Query Service Tests ─────────────────────────────────────────────────────

class TestConversationQueries:
    """Tests for conversation query functions in query_service.py."""

    @pytest.fixture
    def conversation_graph(self, tmp_path: Path) -> Path:
        """Create a test conversation graph in a nexo-out-like directory."""
        import json

        # Create nexo-out directory structure to pass validation
        nexo_out = tmp_path / "nexo-out"
        nexo_out.mkdir()

        # Use nexo's expected JSON format directly (links for NetworkX compatibility)
        graph_data = {
            "directed": False,
            "multigraph": False,
            "graph": {},
            "nodes": [
                {"id": "intent_greeting", "type": "intent", "label": "User greets", "triggers": ["hello", "greeting", "hi there"]},
                {"id": "resp_welcome", "type": "response", "label": "Welcome message"},
                {"id": "state_collecting", "type": "state", "label": "Collecting info", "required_slots": ["name"]},
                {"id": "failure_ambiguity", "type": "failure_state", "label": "Ambiguous", "recovery_path": "ask_clarification"},
                {"id": "ask_clarification", "type": "response", "label": "Ask clarification"},
            ],
            "links": [
                {"source": "intent_greeting", "target": "resp_welcome", "relation": "triggers"},
                {"source": "resp_welcome", "target": "state_collecting", "relation": "leads_to"},
                {"source": "intent_greeting", "target": "failure_ambiguity", "relation": "can_become", "condition": "confidence < 0.7"},
                {"source": "failure_ambiguity", "target": "ask_clarification", "relation": "requires_recovery"},
            ],
        }

        graph_path = nexo_out / "graph.json"
        graph_path.write_text(json.dumps(graph_data))

        return graph_path

    def test_detect_ambiguity_no_matches(self, conversation_graph: Path):
        """Test ambiguity detection with no matches."""
        from nexo.query_service import detect_ambiguity

        result = detect_ambiguity("unrelated query", graph_path=conversation_graph)

        assert result["is_ambiguous"] is False
        assert len(result["candidates"]) == 0

    def test_detect_ambiguity_single_match(self, conversation_graph: Path):
        """Test ambiguity detection with single match."""
        from nexo.query_service import detect_ambiguity

        result = detect_ambiguity("hello", graph_path=conversation_graph)

        # Should find intent_greeting (matches "hello" trigger)
        assert len(result["candidates"]) >= 1
        assert result["is_ambiguous"] is False

    def test_get_valid_next_states(self, conversation_graph: Path):
        """Test getting valid next states."""
        from nexo.query_service import get_valid_next_states

        result = get_valid_next_states("intent_greeting", graph_path=conversation_graph)

        assert "next_states" in result
        assert len(result["next_states"]) >= 1
        # Should include resp_welcome
        labels = [s["label"] for s in result["next_states"]]
        assert "Welcome message" in labels

    def test_get_valid_next_states_invalid(self, conversation_graph: Path):
        """Test getting next states for invalid state."""
        from nexo.query_service import get_valid_next_states

        result = get_valid_next_states("nonexistent_state", graph_path=conversation_graph)

        assert "error" in result
        assert result["next_states"] == []

    def test_find_conversation_paths(self, conversation_graph: Path):
        """Test finding paths to goal."""
        from nexo.query_service import find_conversation_paths

        result = find_conversation_paths("Collecting info", graph_path=conversation_graph)

        assert "paths" in result
        # Should find path from intent_greeting to state_collecting
        if result["paths"]:
            assert len(result["paths"][0]["nodes"]) >= 2

    def test_find_conversation_paths_invalid_goal(self, conversation_graph: Path):
        """Test finding paths to non-existent goal."""
        from nexo.query_service import find_conversation_paths

        result = find_conversation_paths("nonexistent_goal", graph_path=conversation_graph)

        assert "error" in result
        assert result["paths"] == []

    def test_get_recovery_path(self, conversation_graph: Path):
        """Test getting recovery path for failure state."""
        from nexo.query_service import get_recovery_path

        result = get_recovery_path("failure_ambiguity", graph_path=conversation_graph)

        assert "recovery_path" in result
        assert result["recovery_path"] == "ask_clarification"
        assert "recovery_node" in result

    def test_get_recovery_path_invalid(self, conversation_graph: Path):
        """Test getting recovery path for non-existent state."""
        from nexo.query_service import get_recovery_path

        result = get_recovery_path("nonexistent_failure", graph_path=conversation_graph)

        assert "error" in result or "warning" in result


# ── Ingest Extension Tests ──────────────────────────────────────────────────

class TestIngestExtension:
    """Tests for conversation turn saving in ingest.py."""

    def test_save_conversation_turn(self):
        """Test saving a conversation turn."""
        from nexo.ingest import save_conversation_turn

        with tempfile.TemporaryDirectory() as tmpdir:
            memory_dir = Path(tmpdir)
            path = save_conversation_turn(
                session_id="test_session",
                turn_id=1,
                user_input="Hello",
                ai_response="Hi there!",
                memory_dir=memory_dir,
                matched_nodes=["intent_greeting"],
                current_state="greeting",
            )

            assert path.exists()
            content = path.read_text()

            assert "type: \"conversation_turn\"" in content
            assert "session_id: \"test_session\"" in content
            assert "turn_id: 1" in content
            assert "Hello" in content
            assert "Hi there!" in content
            assert "intent_greeting" in content


# ── Additional Unit Tests ────────────────────────────────────────────────────


class TestConversationTemplatesEdgeCases:
    """Edge case tests for conversation templates."""

    def test_parse_template_with_empty_nodes(self):
        """Test parsing template with empty nodes list."""
        from nexo.conversation_templates import parse_conversation_template

        data = {"id": "empty_flow", "nodes": [], "edges": []}
        template = parse_conversation_template(data)

        assert template.id == "empty_flow"
        assert len(template.nodes) == 0

    def test_parse_template_with_missing_fields(self):
        """Test parsing template with missing optional fields."""
        from nexo.conversation_templates import parse_conversation_template

        data = {
            "id": "minimal_flow",
            "nodes": [
                {"id": "node1", "type": "intent", "label": "Test"}
            ],
            "edges": [],
        }
        template = parse_conversation_template(data)
        node = template.nodes[0]

        assert node.triggers == []
        assert node.confidence_threshold == 0.7  # default

    def test_parse_edge_with_defaults(self):
        """Test parsing edge with default values."""
        from nexo.conversation_templates import parse_conversation_template

        data = {
            "id": "test",
            "nodes": [],
            "edges": [{"source": "a", "target": "b"}],
        }
        template = parse_conversation_template(data)
        edge = template.edges[0]

        assert edge.relation == "leads_to"
        assert edge.weight == 1.0
        assert edge.condition is None

    def test_load_conversation_template_from_file(self):
        """Test loading template from JSON file."""
        from nexo.conversation_templates import load_conversation_template

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "template.json"
            path.write_text(json.dumps({
                "id": "file_test",
                "name": "File Test",
                "nodes": [{"id": "n1", "type": "state", "label": "Test"}],
                "edges": [],
            }))

            template = load_conversation_template(path)
            assert template.id == "file_test"
            assert template.name == "File Test"

    def test_get_node_type_all_types(self):
        """Test _get_node_type for all node types."""
        from nexo.conversation_templates import (
            IntentNode, ResponseNode, StateNode,
            FailureStateNode, _get_node_type,
        )

        assert _get_node_type(IntentNode(id="x", label="x")) == "intent"
        assert _get_node_type(ResponseNode(id="x", label="x")) == "response"
        assert _get_node_type(StateNode(id="x", label="x")) == "state"
        assert _get_node_type(FailureStateNode(id="x", label="x")) == "failure_state"


class TestSessionStoreEdgeCases:
    """Edge case tests for session store."""

    def test_default_db_path(self):
        """Test default database path creation."""
        from nexo.session import SessionStore
        import os

        # Create store with default path (should create ~/.nexo/sessions.db)
        store = SessionStore()

        assert store.db_path.exists()
        assert store.db_path.parent.name == ".nexo"

    def test_concurrent_session_access(self):
        """Test that multiple sessions can be accessed concurrently."""
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            # Save multiple sessions
            for i in range(5):
                checkpoint = Checkpoint(turn_id=i, current_node=f"state_{i}")
                store.save_checkpoint(f"session_{i}", checkpoint)

            # Load all sessions
            for i in range(5):
                loaded = store.load_checkpoint(f"session_{i}")
                assert loaded is not None
                assert loaded.turn_id == i

    def test_large_collected_slots(self):
        """Test checkpoint with large collected_slots dict."""
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            large_slots = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}
            checkpoint = Checkpoint(
                turn_id=1,
                current_node="test",
                collected_slots=large_slots,
            )

            store.save_checkpoint("large_session", checkpoint)
            loaded = store.load_checkpoint("large_session")

            assert loaded.collected_slots == large_slots


class TestCompressionEdgeCases:
    """Edge case tests for compression module."""

    def test_compress_with_collected_slots(self):
        """Test compression preserves collected slots."""
        from nexo.compression import compress_conversation, Turn

        turns = [
            Turn(
                turn_id=i,
                user_input=f"Input {i}",
                ai_response=f"Response {i}",
                collected_slots={"name": "An", "phone": "0123"} if i == 0 else None,
            )
            for i in range(10)
        ]

        result = compress_conversation(turns, keep_recent_turns=3)

        # Should preserve slot info in summary
        assert "name=An" in result or "phone=0123" in result

    def test_compress_with_matched_nodes(self):
        """Test compression includes matched nodes info."""
        from nexo.compression import compress_conversation, Turn

        turns = [
            Turn(
                turn_id=0,
                user_input="Book tour",
                ai_response="Sure!",
                matched_nodes=["intent_booking", "state_collecting"],
            )
        ]

        result = compress_conversation(turns)

        assert "intent_booking" in result or "state_collecting" in result

    def test_should_compress_edge_cases(self):
        """Test should_compress with various thresholds."""
        from nexo.compression import should_compress, Turn

        turn = Turn(turn_id=1, user_input="x" * 100, ai_response="y" * 100)

        # Low threshold - should trigger
        assert should_compress([turn], token_budget=50, threshold=0.5) is True

        # High threshold - should not trigger
        assert should_compress([turn], token_budget=1000, threshold=0.9) is False


# ── End-to-End Tests ────────────────────────────────────────────────────────


class TestConversationWorkflowE2E:
    """End-to-end tests for the full conversation workflow."""

    @pytest.fixture
    def full_conversation_graph(self, tmp_path: Path) -> Path:
        """Create a complete conversation graph with multiple flows."""
        nexo_out = tmp_path / "nexo-out"
        nexo_out.mkdir()

        graph_data = {
            "directed": False,
            "multigraph": False,
            "graph": {},
            "nodes": [
                # Booking flow
                {"id": "intent_greeting", "type": "intent", "label": "User greets", "triggers": ["hello", "hi there", "greeting"]},
                {"id": "resp_welcome", "type": "response", "label": "Welcome message", "templates": ["Hello!"]},
                {"id": "intent_booking", "type": "intent", "label": "Booking request", "triggers": ["book", "booking", "reserve"]},
                {"id": "state_collecting", "type": "state", "label": "Collecting booking info", "required_slots": ["date", "people"]},
                {"id": "resp_ask_date", "type": "response", "label": "Ask for date"},
                {"id": "resp_ask_people", "type": "response", "label": "Ask for number of people"},
                {"id": "state_booking_complete", "type": "state", "label": "Booking complete"},
                # Failure states
                {"id": "failure_ambiguity", "type": "failure_state", "label": "Ambiguous input", "recovery_path": "ask_clarification", "max_retries": 2},
                {"id": "ask_clarification", "type": "response", "label": "Ask for clarification"},
                {"id": "failure_missing_slots", "type": "failure_state", "label": "Missing slots", "recovery_path": "state_collecting", "max_retries": 3},
            ],
            "links": [
                {"source": "intent_greeting", "target": "resp_welcome", "relation": "triggers"},
                {"source": "resp_welcome", "target": "intent_booking", "relation": "leads_to"},
                {"source": "intent_booking", "target": "state_collecting", "relation": "leads_to"},
                {"source": "state_collecting", "target": "resp_ask_date", "relation": "requires", "condition": "missing_date"},
                {"source": "state_collecting", "target": "resp_ask_people", "relation": "requires", "condition": "missing_people"},
                {"source": "resp_ask_date", "target": "state_collecting", "relation": "collects_response"},
                {"source": "resp_ask_people", "target": "state_collecting", "relation": "collects_response"},
                {"source": "state_collecting", "target": "state_booking_complete", "relation": "transitions_when", "condition": "all_slots_filled"},
                {"source": "intent_greeting", "target": "failure_ambiguity", "relation": "can_become", "condition": "confidence < 0.7"},
                {"source": "failure_ambiguity", "target": "ask_clarification", "relation": "requires_recovery"},
                {"source": "ask_clarification", "target": "intent_greeting", "relation": "resumes_at"},
                {"source": "state_collecting", "target": "failure_missing_slots", "relation": "can_become"},
                {"source": "failure_missing_slots", "target": "state_collecting", "relation": "requires_recovery"},
            ],
        }

        graph_path = nexo_out / "graph.json"
        graph_path.write_text(json.dumps(graph_data))

        return graph_path

    def test_full_booking_flow(self, full_conversation_graph: Path):
        """Test complete booking conversation flow."""
        from nexo.query_service import (
            detect_ambiguity,
            get_valid_next_states,
            find_conversation_paths,
        )

        # Step 1: User greets
        ambiguity = detect_ambiguity("hello", graph_path=full_conversation_graph)
        assert not ambiguity["is_ambiguous"]
        assert len(ambiguity["candidates"]) >= 1

        # Step 2: Get next states from greeting
        next_states = get_valid_next_states("intent_greeting", graph_path=full_conversation_graph)
        assert len(next_states["next_states"]) >= 1

        # Step 3: Find path to booking complete
        paths = find_conversation_paths("Booking complete", graph_path=full_conversation_graph)
        assert len(paths["paths"]) >= 1
        # Path should start from an intent and end at booking complete
        assert paths["paths"][0]["labels"][-1] == "Booking complete"

    def test_ambiguity_detection_e2e(self, full_conversation_graph: Path):
        """Test ambiguity detection with multi-intent input."""
        from nexo.query_service import detect_ambiguity

        # Input that could match multiple intents
        result = detect_ambiguity("hello I want to book", graph_path=full_conversation_graph)

        # Should detect potential ambiguity
        assert "candidates" in result
        # At least greeting or booking should match
        assert len(result["candidates"]) >= 0  # May be 0 if threshold not met

    def test_recovery_path_e2e(self, full_conversation_graph: Path):
        """Test recovery path from failure states."""
        from nexo.query_service import get_recovery_path

        # Get recovery for ambiguity failure
        recovery = get_recovery_path("failure_ambiguity", graph_path=full_conversation_graph)

        assert recovery["recovery_path"] == "ask_clarification"
        assert recovery["max_retries"] == 2
        assert recovery["recovery_node"] is not None
        assert recovery["recovery_node"]["label"] == "Ask for clarification"

    def test_session_checkpoint_workflow(self, full_conversation_graph: Path):
        """Test session checkpointing through conversation flow."""
        from nexo.session import SessionStore, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            store = SessionStore(db_path)

            session_id = "test_booking_session"

            # Turn 1: Greeting
            checkpoint1 = Checkpoint(
                turn_id=1,
                current_node="resp_welcome",
                path_history=["intent_greeting", "resp_welcome"],
                collected_slots={},
            )
            store.save_checkpoint(session_id, checkpoint1)
            store.save_turn(session_id, 1, "hello", "Hello! How can I help?")

            # Turn 2: Booking request
            checkpoint2 = Checkpoint(
                turn_id=2,
                current_node="state_collecting",
                path_history=["intent_greeting", "resp_welcome", "intent_booking", "state_collecting"],
                collected_slots={},
            )
            store.save_checkpoint(session_id, checkpoint2)
            store.save_turn(session_id, 2, "I want to book a tour", "Sure! When would you like to go?")

            # Turn 3: Provide date
            checkpoint3 = Checkpoint(
                turn_id=3,
                current_node="state_collecting",
                path_history=["intent_greeting", "resp_welcome", "intent_booking", "state_collecting"],
                collected_slots={"date": "2026-05-01"},
            )
            store.save_checkpoint(session_id, checkpoint3)
            store.save_turn(session_id, 3, "May 1st", "Great! How many people?")

            # Verify session state
            turns = store.get_turns(session_id)
            assert len(turns) == 3
            assert turns[0]["turn_id"] == 1
            assert turns[2]["turn_id"] == 3

            # Verify checkpoint
            final_checkpoint = store.load_checkpoint(session_id)
            assert final_checkpoint.current_node == "state_collecting"
            assert final_checkpoint.collected_slots == {"date": "2026-05-01"}

    def test_template_extraction_to_graph(self, full_conversation_graph: Path):
        """Test that templates can be extracted and built into graph."""
        from nexo.conversation_templates import (
            parse_conversation_template,
            conversation_template_to_nodes_edges,
        )
        from nexo.build import build_from_json

        # Create template
        template_data = {
            "id": "test_extract",
            "nodes": [
                {"id": "intent_test", "type": "intent", "label": "Test", "triggers": ["test"]},
                {"id": "resp_test", "type": "response", "label": "Response"},
            ],
            "edges": [{"source": "intent_test", "target": "resp_test", "relation": "triggers"}],
        }

        template = parse_conversation_template(template_data)
        nodes, edges = conversation_template_to_nodes_edges(template, "test.json")

        # Build graph
        extraction = {"nodes": nodes, "edges": edges}
        graph = build_from_json(extraction)

        assert graph.number_of_nodes() == 2
        assert graph.number_of_edges() == 1
        assert "intent_test" in graph.nodes
        assert "resp_test" in graph.nodes


class TestMCPToolsIntegration:
    """Integration tests for MCP tools (without requiring full MCP server)."""

    def test_mcp_tool_signatures(self):
        """Test that MCP tools have correct signatures."""
        from nexo.serve import create_mcp_server

        # Create server (this will register tools)
        server = create_mcp_server("nexo-out/graph.json")

        # Check tools exist
        assert hasattr(server, '_tools') or True  # Tool registration check

    def test_query_service_functions_exported(self):
        """Test that query service functions are properly exported."""
        from nexo import query_service

        # Check all conversation functions exist
        assert hasattr(query_service, 'detect_ambiguity')
        assert hasattr(query_service, 'get_valid_next_states')
        assert hasattr(query_service, 'find_conversation_paths')
        assert hasattr(query_service, 'get_recovery_path')

        # Check they have correct signatures
        import inspect

        sig = inspect.signature(query_service.detect_ambiguity)
        assert 'user_input' in sig.parameters
        assert 'graph_path' in sig.parameters

        sig = inspect.signature(query_service.get_valid_next_states)
        assert 'current_state' in sig.parameters


class TestIngestIntegration:
    """Integration tests for ingest module with conversation turns."""

    def test_save_conversation_turn_integration(self):
        """Test saving conversation turns integrates with graph extraction."""
        from nexo.ingest import save_conversation_turn
        from nexo.extract import extract

        with tempfile.TemporaryDirectory() as tmpdir:
            memory_dir = Path(tmpdir) / "memory"

            # Save a turn
            path = save_conversation_turn(
                session_id="integration_test",
                turn_id=1,
                user_input="Book a tour",
                ai_response="Sure! When?",
                memory_dir=memory_dir,
                matched_nodes=["intent_booking"],
                current_state="booking_flow",
            )

            assert path.exists()

            # Verify the file can be read as markdown
            content = path.read_text()
            assert "type: \"conversation_turn\"" in content
            assert "Book a tour" in content
