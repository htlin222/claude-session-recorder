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
