"""Anki collection adapter: dedicated note types, one undo step, duplicate skipping."""

from dataclasses import dataclass

from .core import plain_text, safe_html, validate_note

MODEL_NAMES = {
    "basic": "Anki Star · Basic",
    "reversed": "Anki Star · Reversed",
    "typing": "Anki Star · Type Answer",
    "cloze": "Anki Star · Cloze",
}
FIELDS = ("Front", "Back", "Extra", "Source")
CSS = """.card { font-family: -apple-system, Arial, sans-serif; font-size: 22px;
text-align: left; line-height: 1.5; max-width: 740px; margin: 36px auto; padding: 0 24px; }
.extra { font-size: 18px; margin-top: 24px; opacity: .85; }
.source { font-size: 14px; margin-top: 24px; opacity: .65; }
.cloze { font-weight: bold; color: #6f61e8; }"""
FOOTER = '<div class="extra">{{Extra}}</div><div class="source">{{Source}}</div>'


@dataclass
class ImportResult:
    changes: object
    added: int
    skipped: int
    cards: int


def validate_model(model, kind):
    expected_type = 1 if kind == "cloze" else 0
    expected_templates = 2 if kind == "reversed" else 1
    if (
        [f["name"] for f in model["flds"]] != list(FIELDS)
        or model["type"] != expected_type
        or len(model["tmpls"]) != expected_templates
    ):
        raise ValueError(
            f"{MODEL_NAMES[kind]} has changed fields, type or card templates. "
            "Restore its structure before importing."
        )


def ensure_model(col, kind):
    from anki.consts import MODEL_CLOZE

    model = col.models.by_name(MODEL_NAMES[kind])
    if model:
        validate_model(model, kind)
        return model
    model = col.models.new(MODEL_NAMES[kind])
    if kind == "cloze":
        model["type"] = MODEL_CLOZE
    for name in FIELDS:
        col.models.add_field(model, col.models.new_field(name))
    front = "{{cloze:Front}}" if kind == "cloze" else "{{Front}}"
    if kind == "typing":
        front += "<br>{{type:Back}}"
    template = col.models.new_template("Recall")
    template["qfmt"] = front
    template["afmt"] = (
        "{{cloze:Front}}"
        if kind == "cloze"
        else "{{FrontSide}}<hr id=answer>{{type:Back}}"
        if kind == "typing"
        else "{{FrontSide}}<hr id=answer>{{Back}}"
    ) + FOOTER
    col.models.add_template(model, template)
    if kind == "reversed":
        reverse = col.models.new_template("Reverse")
        reverse["qfmt"] = "{{Back}}"
        reverse["afmt"] = "{{FrontSide}}<hr id=answer>{{Front}}" + FOOTER
        col.models.add_template(model, reverse)
    model["css"] = CSS
    col.models.add(model)
    return model


def import_notes(col, drafts, deck_name):
    from dataclasses import asdict

    from anki.notes import NoteFieldsCheckResult

    # Validate every note before the first collection mutation.
    drafts = [validate_note(asdict(n), i) for i, n in enumerate(drafts, 1)]
    if not drafts:
        raise ValueError("Select at least one note.")
    deck_name = deck_name.strip()
    if not deck_name or any(not p.strip() for p in deck_name.split("::")):
        raise ValueError("Choose a nonempty deck name, such as Course::Chapter 1.")
    # Preflight modified models before creating decks or notes.
    for kind in {n.type for n in drafts}:
        existing = col.models.by_name(MODEL_NAMES[kind])
        if existing:
            validate_model(existing, kind)
    undo_id = col.add_custom_undo_entry("Import Anki Star notes")
    added = skipped = cards = 0
    try:
        deck_id = col.decks.id(deck_name)
        models = {kind: ensure_model(col, kind) for kind in {n.type for n in drafts}}
        for draft in drafts:
            note = col.new_note(models[draft.type])
            for field, value in zip(FIELDS, (draft.front, draft.back, draft.extra, draft.source)):
                note[field] = safe_html(value)
            note.tags = list(dict.fromkeys(("anki_star", *draft.tags)))
            # Anki checks the exact first field within this note type, across all decks.
            state = note.fields_check()
            if state == NoteFieldsCheckResult.DUPLICATE:
                skipped += 1
                continue
            if state != NoteFieldsCheckResult.NORMAL:
                raise ValueError("Anki rejected the fields or cloze syntax. Check the preview.")
            col.add_note(note, deck_id)
            added += 1
            cards += len(note.card_ids())
    except Exception:
        col.merge_undo_entries(undo_id)
        col.undo()
        raise
    changes = col.merge_undo_entries(undo_id)
    return ImportResult(changes, added, skipped, cards)


def load_practice_notes(col, deck_id):
    from .core import Draft

    kinds = {name: kind for kind, name in MODEL_NAMES.items()}
    ids = col.find_notes(f"did:{int(deck_id)}")
    drafts = []
    for nid in ids[:1000]:
        note = col.get_note(nid)
        kind = kinds.get(note.note_type()["name"])
        if kind and all(f in note for f in FIELDS):
            drafts.append(Draft(kind, *(plain_text(note[f]) for f in FIELDS)))
    return drafts
