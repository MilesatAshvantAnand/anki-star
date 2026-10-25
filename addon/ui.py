"""Native Qt desktop workflow; no embedded browser, credentials, or network client."""

import json
import random
import tempfile
import time
from pathlib import Path

from aqt.operations import CollectionOp, QueryOp
from aqt.qt import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    Qt,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .collection import import_notes, load_practice_notes
from .core import KINDS, FormatError, build_prompt, parse_notes, to_json, validate_note
from .ocr import recognize
from .practice import choices, normalize, questions

EXAMPLE = {
    "notes": [
        {
            "type": "basic",
            "front": "What does RAM stand for?",
            "back": "Random-access memory",
            "source": "Demo — check against your coursework",
        },
        {
            "type": "cloze",
            "front": "A stack follows {{c1::last in, first out::ordering}}.",
            "extra": "Push adds to the top; pop removes from the top.",
            "tags": ["computing"],
        },
        {"type": "typing", "front": "What is 2 raised to the power of 5?", "back": "32"},
        {"type": "reversed", "front": "bonjour", "back": "hello", "tags": ["french"]},
    ]
}


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    widget.setAutoDefault(False)
    if primary:
        widget.setStyleSheet(
            "QPushButton { background: #6754d9; color: white; "
            "border-radius: 6px; padding: 9px 16px; font-weight: bold; }"
            "QPushButton:disabled { background: #888; }"
        )
    return widget


def label(text):
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


class StarDialog(QDialog):
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.busy = False
        self.validated = False
        self.setWindowTitle("Anki Star · Coursework to cards")
        self.resize(1120, 780)
        layout = QVBoxLayout(self)
        title = label("✦  Anki Star")
        title.setStyleSheet("font-size: 28px; font-weight: bold; padding: 8px 0;")
        layout.addWidget(title)
        layout.addWidget(
            label("Your coursework → your AI assistant → cards you have checked. No API key.")
        )
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.build_source()
        self.build_review()
        self.build_practice()
        self.build_guide()
        self.status = label(
            "Start with source text, or go straight to ‘2 · Review & import’ with a response."
        )
        layout.addWidget(self.status)
        self.refresh_decks()

    def page(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        self.tabs.addTab(page, title)
        return layout

    def build_source(self):
        layout = self.page("1 · Prepare a prompt")
        layout.addWidget(
            label(
                "Paste notes here or extract text from an image. If your coursework is already in "
                "NotebookLM, leave this empty and copy the prompt into that notebook’s chat."
            )
        )
        self.context = QPlainTextEdit()
        self.context.setPlaceholderText(
            "Lecture notes, selected textbook passages, or text from an image…"
        )
        layout.addWidget(self.context, 2)
        row = QHBoxLayout()
        self.ocr_file = button("Read text from image…", self.image_file)
        self.ocr_clip = button("Read clipboard image", self.clipboard_image)
        row.addWidget(self.ocr_file)
        row.addWidget(self.ocr_clip)
        row.addWidget(label("Runs locally on macOS. Review the extracted text."))
        layout.addLayout(row)
        form = QFormLayout()
        self.focus = QLineEdit()
        self.focus.setPlaceholderText(
            "e.g. definitions, mechanisms and worked principles from Lecture 3"
        )
        self.count = QSpinBox()
        self.count.setRange(1, 500)
        self.count.setValue(20)
        self.style = QComboBox()
        self.style.addItems(["mixed", *KINDS])
        form.addRow("Focus", self.focus)
        form.addRow("Maximum notes", self.count)
        form.addRow("Note style", self.style)
        layout.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(button("Copy prompt for NotebookLM / ChatGPT", self.copy_prompt, True))
        row.addWidget(
            label("Paste it into your chosen assistant, then copy its full JSON response back.")
        )
        layout.addLayout(row)
        self.prompt_preview = QPlainTextEdit()
        self.prompt_preview.setReadOnly(True)
        self.prompt_preview.setPlaceholderText("Your prompt will appear here when you copy it.")
        layout.addWidget(self.prompt_preview, 1)
        layout.addWidget(
            label(
                "Nothing is uploaded by this add-on. Copying puts text on your system clipboard; "
                "pasting it into an assistant shares it with that service."
            )
        )

    def build_review(self):
        layout = self.page("2 · Review && import")
        layout.addWidget(
            label(
                "Paste the complete JSON response, or two-column text separated by tabs. "
                "Validate, edit cells, and uncheck unwanted notes. All content is plain text."
            )
        )
        self.raw = QPlainTextEdit()
        self.raw.setPlaceholderText(
            '{"notes": [{"type": "basic", "front": "Question?", "back": "Answer"}]}'
        )
        self.raw.setMaximumHeight(140)
        self.raw.textChanged.connect(self.invalidate)
        layout.addWidget(self.raw)
        row = QHBoxLayout()
        row.addWidget(
            button(
                "Paste clipboard", lambda: self.raw.setPlainText(QApplication.clipboard().text())
            )
        )
        row.addWidget(button("Open response file…", self.open_response))
        row.addWidget(
            button("Try example", lambda: self.raw.setPlainText(json.dumps(EXAMPLE, indent=2)))
        )
        row.addStretch()
        row.addWidget(button("Validate && preview", self.validate, True))
        layout.addLayout(row)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Use", "Type", "Front / Cloze text", "Back", "Extra", "Source", "Tags"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 45)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(3, 180)
        self.table.setColumnWidth(4, 140)
        self.table.setColumnWidth(5, 140)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self.preview_changed)
        layout.addWidget(self.table, 1)
        self.preview_status = label("No preview yet.")
        layout.addWidget(self.preview_status)
        form = QFormLayout()
        self.deck = QComboBox()
        self.deck.setEditable(True)
        form.addRow("Destination deck", self.deck)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.export_btn = button("Save reviewed JSON…", self.export_json)
        row.addWidget(self.export_btn)
        row.addStretch()
        self.import_btn = button("Import selected notes", self.import_selected, True)
        row.addWidget(self.import_btn)
        layout.addLayout(row)
        self.import_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

    def build_practice(self):
        layout = self.page("3 · Practice")
        layout.addWidget(
            label(
                "Warm up with your reviewed batch, or load a deck previously created by Anki Star. "
                "These sessions do not change Anki due dates or review history."
            )
        )
        form = QFormLayout()
        self.practice_source = QComboBox()
        self.practice_source.addItems(["Current reviewed batch", "Saved Anki Star notes in deck"])
        self.practice_deck = QComboBox()
        self.mode = QComboBox()
        self.mode.addItems(["Flashcards", "Learn", "Test", "Match"])
        self.session_size = QSpinBox()
        self.session_size.setRange(2, 100)
        self.session_size.setValue(20)
        form.addRow("Study from", self.practice_source)
        form.addRow("Saved deck", self.practice_deck)
        form.addRow("Practice mode", self.mode)
        form.addRow("Maximum questions", self.session_size)
        layout.addLayout(form)
        layout.addWidget(button("Start practice", self.start_practice, True))
        layout.addWidget(
            label(
                "Flashcards: reveal and self-check. Learn: reach two correct answers per question, "
                "with missed questions repeated. Test: one pass with a score and answer review. "
                "Match: pair up to six prompts and answers against a timer."
            )
        )
        layout.addWidget(
            label(
                "Choice answers come from other cards; use a coherent topic. Typed answers ignore "
                "case and spacing; use ‘Accept my answer’ for valid alternatives. "
                "This is a lightweight local practice tool, not Quizlet’s adaptive algorithm."
            )
        )
        layout.addStretch()

    def build_guide(self):
        layout = self.page("Card types & help")
        guide = QPlainTextEdit()
        guide.setReadOnly(True)
        guide.setPlainText("""A NOTE stores information; a CARD tests part of that information.
One Reversed note produces two independently scheduled cards.

BASIC — question → answer
Example: What does RAM stand for? → Random-access memory.
Good default for concepts and explanations. One precise recall target per card.

REVERSED — A → B and B → A
Example: bonjour ↔ hello. Use when both directions make sense.

TYPE ANSWER — type a short answer, then compare
Example: 2^5? → 32. Anki shows text differences; you still choose your rating.

CLOZE — hide part of a sentence
Example: A stack follows {{c1::last in, first out}}.
Use {{c2::another fact}} for a second card; reuse c1 to hide parts together.
An optional hint looks like {{c1::mitochondrion::organelle}}.

OPTIONAL REVERSE — built into Anki; reverse only selected notes.
For this add-on, choose Basic or Reversed on each row instead.

IMAGE OCCLUSION — cover labels or parts of a diagram.
Built into Anki 23.10+. Use Add → Type → Image Occlusion.
OCR reads text; it does not understand or mask diagram regions.

FILES ARE DIFFERENT FROM NOTE TYPES
TXT / TSV / CSV: delimited fields, imported with File → Import.
APKG: a deck package that can include note types and media.
COLPKG: a whole collection export; not the usual choice for new coursework.
ANKIADDON: installs an add-on, not a study deck.
Anki Star uses JSON to exchange mixed note types with your assistant.

WORKFLOW
1. Copy the prompt into the NotebookLM notebook containing your sources,
   or into an assistant chat with your source text/images attached.
2. Copy the complete JSON reply into Review & import.
3. Validate, check factual accuracy, edit cells, choose a deck and import.
4. Use Anki’s normal reviews for spaced repetition. Practice is optional.

IMPORT DETAILS
Exact duplicate first fields in the same Anki Star note type are skipped
across all decks. Existing notes are never updated by this import.
Anki’s Edit → Undo reverses the most recent import in one step.
Plain text is escaped; HTML, remote images and scripts are not rendered.
Source references are retained, not verified. Check AI answers against your notes.

PRIVACY
No API key, AI calls, account login, analytics or background clipboard watching.
Your prompt is copied only when you click Copy. Source text and unsaved drafts
stay in memory until this dialog is discarded when the profile closes.
Saved JSON files and imported notes persist locally; normal Anki sync may sync notes.

Anki Star is an independent community project, not affiliated with Anki or Quizlet.
""")
        layout.addWidget(guide)

    def refresh_decks(self):
        decks = self.mw.col.decks.all_names_and_ids()
        current = self.deck.currentText() or "Anki Star::Coursework"
        self.deck.clear()
        self.practice_deck.clear()
        for deck in decks:
            self.deck.addItem(deck.name)
            self.practice_deck.addItem(deck.name, deck.id)
        self.deck.setCurrentText(current)

    def error(self, error):
        QMessageBox.warning(self, "Anki Star", str(error))

    def invalidate(self):
        self.validated = False
        self.import_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.preview_status.setText("Response changed. Validate again to refresh the preview.")

    def validate(self):
        try:
            drafts = parse_notes(self.raw.toPlainText())
        except FormatError as error:
            self.error(error)
            return
        self.table.blockSignals(True)
        self.table.setRowCount(len(drafts))
        for row, note in enumerate(drafts):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row, 0, check)
            for col, value in enumerate(
                (note.type, note.front, note.back, note.extra, note.source, " ".join(note.tags)), 1
            ):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.blockSignals(False)
        self.validated = True
        self.import_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.preview_changed()

    def selected_notes(self):
        if not self.validated:
            raise FormatError("Validate the response before continuing.")
        result = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() != Qt.CheckState.Checked:
                continue
            values = {
                key: self.table.item(row, col).text()
                for col, key in enumerate(("type", "front", "back", "extra", "source", "tags"), 1)
            }
            result.append(validate_note(values, row + 1))
        if not result:
            raise FormatError("Select at least one note in the preview.")
        return result

    def preview_changed(self, *_):
        if not self.validated:
            return
        try:
            notes = self.selected_notes()
            self.preview_status.setText(
                f"{len(notes)} notes selected → {sum(n.card_count for n in notes)} cards. "
                "Duplicate first fields will be skipped at import. Double-click a cell to edit."
            )
        except FormatError as error:
            self.preview_status.setText(str(error))

    def copy_prompt(self):
        prompt = build_prompt(
            self.context.toPlainText(),
            self.focus.text(),
            self.count.value(),
            self.style.currentText(),
        )
        self.prompt_preview.setPlainText(prompt)
        QApplication.clipboard().setText(prompt)
        self.status.setText(
            "Prompt copied. Paste into your assistant, then bring the JSON response to step 2."
        )

    def open_response(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open response", "", "Text responses (*.json *.txt *.tsv);;All files (*)"
        )
        if path:
            try:
                if Path(path).stat().st_size > 2_000_000:
                    raise FormatError("File is too large. Split it into batches under 2 MB.")
                self.raw.setPlainText(Path(path).read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, FormatError) as error:
                self.error(error)

    def export_json(self):
        try:
            content = to_json(self.selected_notes())
        except FormatError as error:
            self.error(error)
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save reviewed notes", "anki-star-notes.json", "JSON (*.json)"
        )
        if path:
            try:
                Path(path).write_text(content + "\n", encoding="utf-8")
            except OSError as error:
                self.error(error)

    def set_busy(self, busy):
        self.busy = busy
        self.tabs.setEnabled(not busy)

    def import_selected(self):
        try:
            notes = self.selected_notes()
        except FormatError as error:
            self.error(error)
            return
        deck = self.deck.currentText()
        self.set_busy(True)

        def done(result):
            self.set_busy(False)
            self.refresh_decks()
            self.status.setText(
                f"Imported {result.added} notes / {result.cards} cards into {deck}. "
                f"Skipped {result.skipped} duplicates. Use Edit → Undo to reverse the import."
            )

        def failed(error):
            self.set_busy(False)
            self.error(error)

        CollectionOp(parent=self, op=lambda col: import_notes(col, notes, deck)).success(
            done
        ).failure(failed).run_in_background()

    def image_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Read text from image", "", "Images (*.png *.jpg *.jpeg *.heic *.tif *.tiff)"
        )
        if path:
            self.run_ocr(path)

    def clipboard_image(self):
        image = QApplication.clipboard().image()
        if image.isNull():
            self.error("Copy an image first, or choose an image file.")
            return
        handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        path = handle.name
        handle.close()
        if not image.save(path):
            Path(path).unlink(missing_ok=True)
            self.error("Could not read the clipboard image.")
            return
        self.run_ocr(path, cleanup=True)

    def run_ocr(self, path, cleanup=False):
        self.set_busy(True)
        self.status.setText("Reading image text locally…")

        def work(_col):
            try:
                return recognize(path)
            finally:
                if cleanup:
                    Path(path).unlink(missing_ok=True)

        def done(text):
            self.set_busy(False)
            self.context.appendPlainText(text)
            self.status.setText(
                "Image text added. Check names, symbols and equations before copying the prompt."
            )

        def failed(error):
            self.set_busy(False)
            self.status.setText("Image text could not be read.")
            self.error(error)

        QueryOp(parent=self, op=work, success=done).failure(
            failed
        ).without_collection().run_in_background()

    def start_practice(self):
        mode, limit = self.mode.currentText(), self.session_size.value()

        def start(notes):
            pool = questions(notes)
            if len(pool) < 2:
                self.error(
                    "Select at least two cards. Saved practice loads only Anki Star note types."
                )
                return
            pool = random.sample(pool, min(limit, len(pool)))
            PracticeDialog(self, pool, mode).exec()

        if self.practice_source.currentIndex() == 0:
            try:
                start(self.selected_notes())
            except FormatError as error:
                self.error(error)
        else:
            did = self.practice_deck.currentData()
            if did is None:
                self.error("Select a saved deck first.")
                return
            QueryOp(
                parent=self, op=lambda col: load_practice_notes(col, did), success=start
            ).failure(self.error).run_in_background()

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            event.accept()


class PracticeDialog(QDialog):
    def __init__(self, parent, pool, mode):
        super().__init__(parent)
        self.pool, self.mode = pool, mode
        self.queue = list(range(len(pool)))
        self.mastery = [0] * len(pool)
        self.attempts = self.correct = 0
        self.history = []
        self.awaiting = False
        self.started = time.monotonic()
        self.setWindowTitle(f"Anki Star · {mode}")
        self.resize(780, 620)
        self.layout = QVBoxLayout(self)
        self.progress = label("")
        self.layout.addWidget(self.progress)
        if mode == "Match":
            self.build_match()
            return
        self.question_label = label("")
        self.question_label.setStyleSheet("font-size: 24px; padding: 24px 4px;")
        self.layout.addWidget(self.question_label)
        self.option = QComboBox()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type your answer…")
        self.layout.addWidget(self.option)
        self.layout.addWidget(self.input)
        self.feedback = label("")
        self.feedback.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.layout.addWidget(self.feedback, 1)
        row = QHBoxLayout()
        self.check = button("Check answer", self.check_answer, True)
        self.accept = button("Accept my answer", self.accept_answer)
        self.next = button("Next", self.next_question)
        self.again = button("Missed it", lambda: self.finish_answer(False))
        self.known = button("Got it", lambda: self.finish_answer(True))
        for widget in (self.check, self.accept, self.next, self.again, self.known):
            row.addWidget(widget)
        self.layout.addLayout(row)
        self.input.returnPressed.connect(self.check_answer)
        self.render_question()

    def render_question(self):
        if not self.queue:
            self.show_results()
            return
        self.current_index = self.queue[0]
        self.current = self.pool[self.current_index]
        self.awaiting = False
        self.progress.setText(
            f"{self.mode} · {self.correct}/{self.attempts} correct · "
            f"{sum(m >= 2 for m in self.mastery)}/{len(self.pool)} mastered"
            if self.mode == "Learn"
            else f"{self.mode} · Question {self.attempts + 1} of {len(self.pool)}"
        )
        self.question_label.setText(self.current.front)
        self.feedback.clear()
        self.input.clear()
        self.input.setEnabled(True)
        self.option.setEnabled(True)
        options = choices(self.current, self.pool)
        self.is_choice = (
            self.mode != "Flashcards"
            and len(options) >= 2
            and (
                self.mastery[self.current_index] == 0
                if self.mode == "Learn"
                else self.attempts % 2 == 0
            )
        )
        self.option.clear()
        self.option.addItem("Choose an answer…", None)
        for value in options:
            self.option.addItem(value, value)
        self.option.setVisible(self.is_choice)
        self.input.setVisible(not self.is_choice and self.mode != "Flashcards")
        self.check.setText("Reveal answer" if self.mode == "Flashcards" else "Check answer")
        self.check.setEnabled(True)
        for widget in (self.accept, self.next, self.again, self.known):
            widget.hide()
        if self.input.isVisible():
            self.input.setFocus()

    def check_answer(self):
        if self.awaiting:
            return
        if self.mode == "Flashcards":
            self.feedback.setText(self.current.answer)
            self.check.setEnabled(False)
            self.again.show()
            self.known.show()
            return
        answer = self.option.currentData() if self.is_choice else self.input.text()
        if answer is None or not answer.strip():
            self.feedback.setText("Enter or choose an answer first.")
            return
        self.awaiting = True
        self.last_answer = answer
        self.was_correct = normalize(answer) == normalize(self.current.answer)
        self.feedback.setText(
            ("Correct.\n\n" if self.was_correct else "Compare your answer.\n\n")
            + self.current.answer
        )
        self.check.setEnabled(False)
        self.input.setEnabled(False)
        self.option.setEnabled(False)
        self.accept.setVisible(not self.was_correct)
        self.next.show()

    def accept_answer(self):
        if self.awaiting:
            self.was_correct = True
            self.feedback.setText("Marked correct by you.\n\n" + self.current.answer)
            self.accept.hide()

    def next_question(self):
        if self.awaiting:
            self.finish_answer(self.was_correct)

    def finish_answer(self, correct):
        self.attempts += 1
        self.correct += int(correct)
        self.history.append((self.current.front, self.current.answer, correct))
        index = self.queue.pop(0)
        if self.mode == "Learn":
            self.mastery[index] = self.mastery[index] + 1 if correct else 0
            if self.mastery[index] < 2:
                self.queue.append(index)
        self.render_question()

    def show_results(self):
        for widget in (
            self.option,
            self.input,
            self.check,
            self.accept,
            self.next,
            self.again,
            self.known,
        ):
            widget.hide()
        self.progress.setText(f"Session complete · {self.correct}/{self.attempts} correct")
        self.question_label.setText("You’ve finished this session.")
        self.feedback.setText(
            "\n\n".join(
                f"{'✓' if ok else '✕'} {front}\nAnswer: {answer}"
                for front, answer, ok in self.history
            )
        )
        # Long answer reviews need a scrollable widget.
        self.feedback.hide()
        review = QPlainTextEdit()
        review.setReadOnly(True)
        review.setPlainText(self.feedback.text())
        self.layout.insertWidget(2, review, 1)

    def build_match(self):
        # Repeated prompts/answers make a matching game ambiguous, so use unique pairs.
        pairs = []
        for q in self.pool:
            if all(
                normalize(q.front) != normalize(p.front)
                and normalize(q.answer) != normalize(p.answer)
                for p in pairs
            ):
                pairs.append(q)
        self.pairs = pairs[:6]
        self.progress.setText("Match each prompt to an answer. The timer is running.")
        options = [q.answer for q in self.pairs]
        random.shuffle(options)
        grid = QGridLayout()
        self.matches = []
        for row, q in enumerate(self.pairs):
            grid.addWidget(label(q.front), row, 0)
            combo = QComboBox()
            combo.addItem("Choose a match…", None)
            for answer in options:
                combo.addItem(answer, answer)
            grid.addWidget(combo, row, 1)
            self.matches.append(combo)
        self.layout.addLayout(grid)
        self.match_feedback = label("")
        self.layout.addWidget(self.match_feedback)
        self.layout.addWidget(button("Check matches", self.check_matches, True))
        self.layout.addStretch()

    def check_matches(self):
        correct = 0
        for combo, pair in zip(self.matches, self.pairs):
            ok = combo.currentData() == pair.answer
            combo.setEnabled(not ok)
            correct += int(ok)
        elapsed = time.monotonic() - self.started
        self.match_feedback.setText(
            f"{correct}/{len(self.pairs)} matched · {elapsed:.1f} seconds"
            + (" · Complete!" if correct == len(self.pairs) else " · Try the remaining pairs.")
        )
