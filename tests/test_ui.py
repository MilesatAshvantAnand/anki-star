import json

from aqt.qt import QApplication, Qt

from addon.practice import Question
from addon.ui import EXAMPLE, PracticeDialog


def test_review_selection_edit_and_stale_response(window):
    window.raw.setPlainText(json.dumps(EXAMPLE))
    window.validate()
    assert window.table.rowCount() == 4
    assert len(window.selected_notes()) == 4
    window.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    window.table.item(2, 3).setText("thirty-two")
    assert len(window.selected_notes()) == 3
    assert window.selected_notes()[1].back == "thirty-two"
    window.raw.appendPlainText(" ")
    assert not window.import_btn.isEnabled()


def test_prompt_copy_is_explicit(window, app):
    QApplication.clipboard().setText("prior clipboard")
    window.context.setPlainText("Lecture context")
    assert QApplication.clipboard().text() == "prior clipboard"
    window.copy_prompt()
    assert "Lecture context" in QApplication.clipboard().text()


def test_test_mode_records_results_and_accepts_alternative(app):
    pool = [Question("q1", "a1"), Question("q2", "a2")]
    dialog = PracticeDialog(None, pool, "Test")
    dialog.option.setCurrentIndex(dialog.option.findData("a1"))
    dialog.check_answer()
    dialog.next_question()
    dialog.input.setText("alternative")
    dialog.check_answer()
    assert not dialog.was_correct
    dialog.accept_answer()
    dialog.next_question()
    assert dialog.correct == 2 and dialog.attempts == 2
    assert "complete" in dialog.progress.text()
    dialog.close()


def test_learn_repeats_misses_and_requires_two_correct(app):
    pool = [Question("q1", "a1"), Question("q2", "a2")]
    dialog = PracticeDialog(None, pool, "Learn")
    dialog.finish_answer(False)
    assert dialog.queue == [1, 0]
    for _ in range(4):
        dialog.finish_answer(True)
    assert dialog.mastery == [2, 2]
    assert not dialog.queue
    dialog.close()


def test_match_disambiguates_duplicate_pairs(app):
    dialog = PracticeDialog(
        None, [Question("q1", "a"), Question("q2", "a"), Question("q3", "b")], "Match"
    )
    assert len(dialog.pairs) == 2
    for combo, pair in zip(dialog.matches, dialog.pairs):
        combo.setCurrentIndex(combo.findData(pair.answer))
    dialog.check_matches()
    assert "Complete!" in dialog.match_feedback.text()
    dialog.close()
