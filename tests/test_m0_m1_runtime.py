from __future__ import annotations

import unittest
from pathlib import Path

from replay.loader import load_builtin_replay
from replay.runner import ReplayRunner, run_replay_file
from replay.schema_support import EXAMPLE_DIR, load_json
from runtime.events.log import EventLog
from runtime.projector.state import EventProjector


ROOT = Path(__file__).resolve().parent.parent
FLOWS = ROOT / "schemas" / "examples" / "flows"


class M0M1RuntimeTests(unittest.TestCase):
    def test_event_log_deduplicates(self) -> None:
        log = EventLog()
        event = load_json(EXAMPLE_DIR / "event-envelope.example.json")
        self.assertTrue(log.append(event))
        self.assertFalse(log.append(event))
        self.assertEqual(len(log), 1)

    def test_replay_loader_reads_both_fixtures(self) -> None:
        research = load_builtin_replay("research-brief-flow.json")
        crm = load_builtin_replay("crm-followup-flow.json")
        self.assertEqual(research.replay_id, "replay_research_brief_001")
        self.assertEqual(crm.replay_id, "replay_crm_followup_001")

    def test_projector_rebuild_matches_incremental_state(self) -> None:
        result = run_replay_file(FLOWS / "research-brief-flow.json")
        rebuilt = EventProjector().rebuild(result.event_log.as_list(), as_of=result.state.last_event_at)
        self.assertEqual(rebuilt.task_states, result.state.task_states)
        self.assertEqual(rebuilt.nodes, result.state.nodes)
        self.assertEqual(rebuilt.facts, result.state.facts)

    def test_candidate_fact_never_promotes_without_verification_directive(self) -> None:
        result = run_replay_file(FLOWS / "research-brief-flow.json")
        conflict_facts = [fact for fact in result.state.facts.values() if fact.get("conflict_set")]
        self.assertEqual(len(conflict_facts), 2)
        self.assertTrue(all(fact["status"] == "candidate" for fact in conflict_facts))

    def test_verified_fact_downgrades_to_stale_when_expired(self) -> None:
        runner = ReplayRunner(load_builtin_replay("crm-followup-flow.json"))
        result = runner.run(step_limit=2)
        rebuilt = EventProjector().rebuild(result.event_log.as_list(), as_of=runner._time_for_step(200, 0))
        self.assertEqual(rebuilt.facts["fact_node_read_crm_record_baseline"]["status"], "stale")

    def test_conflicting_facts_coexist_until_resolution(self) -> None:
        result = run_replay_file(FLOWS / "research-brief-flow.json")
        self.assertIn("fact_node_extract_facts_a", result.state.facts)
        self.assertIn("fact_node_extract_facts_b", result.state.facts)
        self.assertEqual(result.state.facts["fact_node_extract_facts_a"]["conflict_set"], ["conflict.vendor.claims"])
        self.assertEqual(result.state.facts["fact_node_extract_facts_b"]["conflict_set"], ["conflict.vendor.claims"])

    def test_dispatch_without_active_grant_is_rejected(self) -> None:
        runner = ReplayRunner(load_builtin_replay("research-brief-flow.json"))
        runner._run_step(runner.fixture.timeline[0])
        step = runner.fixture.timeline[1]
        with self.assertRaisesRegex(ValueError, "dispatch denied"):
            runner._emit_token(step, "action.dispatched", 99)

    def test_terminal_transition_without_verification_is_rejected(self) -> None:
        runner = ReplayRunner(load_builtin_replay("research-brief-flow.json"))
        runner._run_step(runner.fixture.timeline[0])
        with self.assertRaisesRegex(ValueError, "verification required"):
            runner._emit_event(
                step_number=1,
                event_type="node.state_changed",
                payload={
                    "task_id": runner.fixture.task_id,
                    "node_id": runner.fixture.root_node_id,
                    "from_state": "ready",
                    "to_state": "completed",
                    "changed_at": runner._time_for_step(1, 1).isoformat(),
                },
                node_id=runner.fixture.root_node_id,
                suffix="illegal-terminal",
            )

    def test_selector_chooses_low_attention_valid_path_for_replay_a(self) -> None:
        runner = ReplayRunner(load_builtin_replay("research-brief-flow.json"))
        runner.run(step_limit=1)
        selection = runner.selection_history[-1]
        self.assertEqual(selection["node_id"], "node_collect_sources")
        self.assertEqual(selection["max_interruptions"], 0)
        self.assertEqual(selection["path_kind"], "structured")

    def test_capsule_export_preserves_hard_constraints_and_freshness_markers(self) -> None:
        runner = ReplayRunner(load_builtin_replay("research-brief-flow.json"))
        runner.run()
        capsule = runner.export_capsule("node_prepare_brief")
        self.assertIn("truth_source=event_log", capsule["hard_constraints"])
        self.assertIn("terminal_requires_verification", capsule["hard_constraints"])
        self.assertIn("fact_node_extract_facts_a", capsule["freshness_markers"])

    def test_replay_b_completes_and_promotes_observed_fact(self) -> None:
        result = run_replay_file(FLOWS / "crm-followup-flow.json")
        self.assertEqual(result.state.current_task_terminal(result.fixture.task_id), "completed")
        self.assertEqual(result.state.facts["fact_node_read_crm_record_baseline"]["status"], "verified")

    def test_m2_commit_grant_requires_explicit_approval(self) -> None:
        runner = ReplayRunner(load_builtin_replay("crm-followup-flow.json"))
        runner.run(step_limit=3)
        step = runner.fixture.timeline[3]
        with self.assertRaisesRegex(ValueError, "approval required"):
            runner._build_grant(step, token_index=2)

    def test_m2_commit_recovery_records_compensation_path(self) -> None:
        result = run_replay_file(FLOWS / "crm-followup-flow.json")
        recoveries = list(result.state.recoveries.values())
        self.assertEqual(len(recoveries), 1)
        self.assertEqual(recoveries[0]["action"], "compensate")
        self.assertEqual(recoveries[0]["status"], "armed")

    def test_m2_selector_rationale_uses_composite_risk(self) -> None:
        result = run_replay_file(FLOWS / "crm-followup-flow.json")
        risk_snapshots = [item for item in result.selection_history if item["node_id"] is not None]
        self.assertTrue(risk_snapshots)
        self.assertIn("composite_risk", risk_snapshots[0]["rationale"])

    def test_m2_approval_drives_awaiting_approval_transition(self) -> None:
        result = run_replay_file(FLOWS / "crm-followup-flow.json")
        approval_events = [event for event in result.event_log.as_list() if event["event_type"] == "approval.recorded"]
        state_events = [event for event in result.event_log.as_list() if event["event_type"] == "node.state_changed"]
        self.assertEqual(len(approval_events), 2)
        self.assertTrue(any(event["payload"]["to_state"] == "awaiting_approval" for event in state_events))
        self.assertTrue(any(event["payload"]["from_state"] == "awaiting_approval" for event in state_events))


if __name__ == "__main__":
    unittest.main()
