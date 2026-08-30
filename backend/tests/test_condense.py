def test_first_turn_short_circuits_with_no_model_call(monkeypatch):
    from chat.graph.nodes import condense as node

    def boom(*a, **k):
        raise AssertionError("condense must not call the model with empty history")

    monkeypatch.setattr(node, "structured", boom)
    out = node.condense({"question": "what did he build at Majara", "history": []})
    assert out["condensed"] == "what did he build at Majara"


def test_follow_up_is_rewritten_standalone(monkeypatch):
    from chat.graph.nodes import condense as node
    from chat.graph.nodes.condense import Standalone

    captured = {}

    def fake(prompt, schema, *, fast=False):
        captured["prompt"] = prompt
        captured["fast"] = fast
        return Standalone(standalone_question="What did he build at Majara?"), {}

    monkeypatch.setattr(node, "structured", fake)
    out = node.condense({
        "question": "and there?",
        "history": [
            {"role": "user", "content": "where does he work"},
            {"role": "assistant", "content": "He interns at Majara."},
        ],
    })
    assert out["condensed"] == "What did he build at Majara?"
    assert "Majara" in captured["prompt"]
    assert captured["fast"] is True


def test_a_blank_rewrite_falls_back_to_the_raw_question(monkeypatch):
    from chat.graph.nodes import condense as node
    from chat.graph.nodes.condense import Standalone

    monkeypatch.setattr(node, "structured",
                        lambda *a, **k: (Standalone(standalone_question="  "), {}))
    out = node.condense({"question": "and there?", "history": [{"role": "user", "content": "x"}]})
    assert out["condensed"] == "and there?"


def test_an_unparseable_rewrite_falls_back_to_the_raw_question(monkeypatch):
    from chat.graph.nodes import condense as node

    monkeypatch.setattr(node, "structured", lambda *a, **k: (None, {}))
    out = node.condense({"question": "and there?", "history": [{"role": "user", "content": "x"}]})
    assert out["condensed"] == "and there?"
