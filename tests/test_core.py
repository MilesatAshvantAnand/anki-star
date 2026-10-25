import json

import pytest

from addon.core import Draft, FormatError, build_prompt, parse_notes, safe_html, to_json
from addon.practice import Question, choices, normalize, questions


def test_mixed_json_roundtrip_and_card_counts():
    notes = [
        Draft("basic", "Q", "A", source="Lecture 2, p. 3", tags=("course::a",)),
        Draft("reversed", "hello", "bonjour"),
        Draft("typing", "2^5", "32"),
        Draft("cloze", "{{c1::alpha}} and {{c2::beta::hint}} and {{c1::gamma}}"),
    ]
    assert parse_notes("```json\n" + to_json(notes) + "\n```") == notes
    assert [n.card_count for n in notes] == [1, 2, 1, 2]


def test_quoted_tsv_and_header():
    notes = parse_notes('Front\tBack\tTags\n"what\nnow"\t"A\tB"\tcourse::a\n')
    assert notes[0].front == "what\nnow"
    assert notes[0].back == "A\tB"
    assert notes[0].tags == ("course::a",)


@pytest.mark.parametrize(
    "data",
    [
        {"front": ""},
        {"front": "Q", "back": 3},
        {"front": "Q", "type": []},
        {"front": "Q", "back": "A", "tags": ["with space"]},
        {"front": "Q", "back": "A", "media": "x"},
        {"type": "cloze", "front": "{{c0::no}}"},
        {"type": "cloze", "front": "{{c1::}}"},
        {"type": "cloze", "front": "{{c1:: ::hint}}"},
        {"type": "cloze", "front": "{{c1::good}} {{c2::broken}"},
        {"type": "basic", "front": "{{c1::answer}}", "back": "a"},
        {"front": "Q\u001fhidden", "back": "A"},
    ],
)
def test_invalid_notes_rejected(data):
    with pytest.raises(FormatError, match="Note 1"):
        parse_notes(json.dumps({"notes": [data]}))


@pytest.mark.parametrize(
    "raw",
    ["", "not a table", "[]", '{"notes": []}', '{"notes": [], "other": 2}', "[", "Q\tA\tB\tC"],
)
def test_invalid_responses_rejected(raw):
    with pytest.raises(FormatError):
        parse_notes(raw)


def test_html_and_media_are_inert():
    value = safe_html('<script>alert(1)</script><img src="https://x">\n[sound:x.mp3] &')
    assert "<script>" not in value and "<img" not in value and "[sound:" not in value
    assert "<br>" in value and "&amp;" in value


def test_prompt_has_context_and_schema():
    prompt = build_prompt("my coursework", "mechanisms", 5, "cloze")
    assert "my coursework" in prompt and "mechanisms" in prompt
    assert "up to 5" in prompt and "only the cloze" in prompt
    assert "{{c1::hidden answer}}" in prompt


def test_practice_cloze_and_reversed():
    pool = questions(
        [
            Draft("cloze", "{{c1::A::letter}} with {{c2::B}} and {{c1::C}}"),
            Draft("reversed", "bonjour", "hello"),
        ]
    )
    assert pool[0] == Question("[letter] with B and […]", "A; C")
    assert pool[1] == Question("A with […] and C", "B")
    assert pool[-1] == Question("hello", "bonjour")
    assert choices(pool[0], [pool[0], pool[0]]) == ["A; C"]
    assert normalize("  HéLLo\n World ") == "héllo world"
