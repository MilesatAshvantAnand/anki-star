import pytest
from anki.collection import Collection

from addon.collection import MODEL_NAMES, import_notes, load_practice_notes
from addon.core import Draft


@pytest.fixture
def col(tmp_path):
    collection = Collection(str(tmp_path / "collection.anki2"))
    yield collection
    collection.close()


def test_actual_anki_cards_render_and_undo(col):
    drafts = [
        Draft("basic", "What <tag>?", "An & answer", source="Lecture 1"),
        Draft("reversed", "hello", "bonjour"),
        Draft("typing", "2^5?", "32"),
        Draft("cloze", "{{c1::A}} + {{c2::B}}", extra="Two facts"),
    ]
    result = import_notes(col, drafts, "Test::Course")
    assert result.added == 4 and result.cards == 6
    assert col.note_count() == 4 and col.card_count() == 6
    for cid in col.find_cards(""):
        card = col.get_card(cid)
        assert card.question() and card.answer()
        assert "Lecture 1" in card.answer() if "&lt;tag&gt;" in card.question() else True
    assert len(load_practice_notes(col, col.decks.id("Test::Course"))) == 4
    col.undo()
    assert col.note_count() == 0 and col.card_count() == 0
    assert col.models.by_name(MODEL_NAMES["basic"]) is None
    col.redo()
    assert col.note_count() == 4 and col.card_count() == 6


def test_duplicates_skip_within_batch_and_across_decks(col):
    note = Draft("basic", "Q", "A")
    result = import_notes(col, [note, note], "One")
    assert (result.added, result.skipped) == (1, 1)
    result = import_notes(col, [Draft("basic", "Q", "Changed answer")], "Two")
    assert (result.added, result.skipped) == (0, 1)
    assert col.get_note(col.find_notes("")[0])["Back"] == "A"


def test_invalid_batch_never_partially_imported(col):
    with pytest.raises(ValueError):
        import_notes(col, [Draft("basic", "ok", "yes"), Draft("cloze", "broken")], "One")
    assert col.note_count() == 0


def test_failure_rolls_back_created_notes_and_models(col, monkeypatch):
    original = col.add_note
    calls = 0

    def failing(note, did):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected failure")
        return original(note, did)

    monkeypatch.setattr(col, "add_note", failing)
    with pytest.raises(RuntimeError, match="injected"):
        import_notes(col, [Draft("basic", "q1", "a1"), Draft("basic", "q2", "a2")], "One")
    assert col.note_count() == 0
    assert col.models.by_name(MODEL_NAMES["basic"]) is None


def test_changed_template_structure_rejected_before_import(col):
    import_notes(col, [Draft("basic", "existing", "answer")], "One")
    model = col.models.by_name(MODEL_NAMES["basic"])
    extra = col.models.new_template("Extra")
    extra["qfmt"], extra["afmt"] = "{{Back}}", "{{Front}}"
    col.models.add_template(model, extra)
    col.models.save(model)
    with pytest.raises(ValueError, match="changed fields, type or card templates"):
        import_notes(col, [Draft("basic", "new", "answer")], "Two")
    assert col.note_count() == 1
