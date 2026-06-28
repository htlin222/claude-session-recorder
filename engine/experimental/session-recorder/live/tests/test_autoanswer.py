import json
import os

import autoanswer_questions as aq

Q = {"questions": [{"question": "Which language?", "header": "Language",
                    "options": [{"label": "Python (hello.py)"},
                                {"label": "Bash (hello.sh)"}]}]}


def test_default_picks_first_option():
    chosen = aq.choose_answers(Q, {})
    assert chosen == [{"header": "Language", "answer": "Python (hello.py)"}]


def test_override_by_index_forces_non_default():
    chosen = aq.choose_answers(Q, {"*": 1})
    assert chosen[0]["answer"] == "Bash (hello.sh)"


def test_override_by_substring_case_insensitive():
    chosen = aq.choose_answers(Q, {"*": "bash"})
    assert chosen[0]["answer"] == "Bash (hello.sh)"


def test_override_keyed_by_header():
    chosen = aq.choose_answers(Q, {"Language": "Bash (hello.sh)"})
    assert chosen[0]["answer"] == "Bash (hello.sh)"


def test_deny_payload_states_the_answer():
    payload = aq.deny_payload([{"header": "Language", "answer": "Bash (hello.sh)"}])
    out = payload["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    assert "Bash (hello.sh)" in out["permissionDecisionReason"]


def test_no_questions_denies_with_assume_message():
    payload = aq.deny_payload([])
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "assumption" in payload["hookSpecificOutput"]["permissionDecisionReason"].lower()


def test_target_index_default_is_first_option():
    assert aq.target_index_for(Q["questions"][0], {}) == 0


def test_target_index_override_by_index():
    assert aq.target_index_for(Q["questions"][0], {"*": 1}) == 1


def test_render_mode_allows_and_writes_signal(tmp_path):
    data = {"tool_input": {"questions": Q["questions"]}}
    out = aq.handle(data, answers={}, mode="render", signal_dir=str(tmp_path))
    # render mode must NOT deny (so the selector renders on screen)
    assert out is None or out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
    sig = tmp_path / "pending_q.json"
    assert sig.exists()
    rec = json.loads(sig.read_text())
    assert rec["questions"][0]["options"] == ["Python (hello.py)", "Bash (hello.sh)"]
    assert rec["questions"][0]["target_index"] == 0
    assert rec["questions"][0]["target_label"] == "Python (hello.py)"


def test_render_mode_target_override(tmp_path):
    data = {"tool_input": {"questions": Q["questions"]}}
    aq.handle(data, answers={"*": 1}, mode="render", signal_dir=str(tmp_path))
    rec = json.loads((tmp_path / "pending_q.json").read_text())
    assert rec["questions"][0]["target_index"] == 1
    assert rec["questions"][0]["target_label"] == "Bash (hello.sh)"


def test_render_mode_emits_all_questions(tmp_path):
    two = {"tool_input": {"questions": [
        {"question": "Which language?", "header": "Language",
         "options": [{"label": "Python"}, {"label": "Bash"}]},
        {"question": "Which filename?", "header": "Filename",
         "options": [{"label": "hello.py"}, {"label": "main.py"}]},
    ]}}
    aq.handle(two, answers={"Filename": 1}, mode="render", signal_dir=str(tmp_path))
    rec = json.loads((tmp_path / "pending_q.json").read_text())
    assert len(rec["questions"]) == 2
    assert rec["questions"][0]["header"] == "Language"
    assert rec["questions"][0]["target_index"] == 0
    assert rec["questions"][0]["target_label"] == "Python"
    assert rec["questions"][1]["header"] == "Filename"
    assert rec["questions"][1]["target_index"] == 1
    assert rec["questions"][1]["target_label"] == "main.py"


def test_target_indices_single_select_default():
    assert aq.target_indices_for(Q["questions"][0], {}) == [0]


def test_target_indices_single_select_override():
    assert aq.target_indices_for(Q["questions"][0], {"*": 1}) == [1]


MS = {"question": "Pick some", "header": "Topics", "multiSelect": True,
      "options": [{"label": "alpha"}, {"label": "beta"},
                  {"label": "gamma"}, {"label": "delta"}]}


def test_target_indices_multiselect_default_first():
    assert aq.target_indices_for(MS, {}) == [0]


def test_target_indices_multiselect_list_of_ints():
    assert aq.target_indices_for(MS, {"*": [0, 2]}) == [0, 2]


def test_target_indices_multiselect_list_of_labels():
    assert aq.target_indices_for(MS, {"Topics": ["beta", "delta"]}) == [1, 3]


def test_target_indices_multiselect_single_int_wrapped():
    assert aq.target_indices_for(MS, {"*": 2}) == [2]


def test_render_mode_emits_target_indices_default(tmp_path):
    data = {"tool_input": {"questions": Q["questions"]}}
    aq.handle(data, answers={}, mode="render", signal_dir=str(tmp_path))
    rec = json.loads((tmp_path / "pending_q.json").read_text())
    assert rec["questions"][0]["target_indices"] == [0]


def test_render_mode_multiselect_emits_target_indices(tmp_path):
    data = {"tool_input": {"questions": [MS]}}
    aq.handle(data, answers={"*": [0, 2]}, mode="render", signal_dir=str(tmp_path))
    rec = json.loads((tmp_path / "pending_q.json").read_text())
    assert rec["questions"][0]["target_indices"] == [0, 2]
    assert rec["questions"][0]["multiSelect"] is True


def test_auto_mode_handle_denies(tmp_path):
    out = aq.handle({"tool_input": {"questions": Q["questions"]}}, answers={}, mode="auto", signal_dir=str(tmp_path))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert not (tmp_path / "pending_q.json").exists()
