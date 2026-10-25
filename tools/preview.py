"""Render synthetic example screenshots without touching an Anki user profile."""

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anki.collection import Collection  # noqa: E402
from aqt.qt import QApplication, QMainWindow  # noqa: E402

from addon.practice import questions  # noqa: E402
from addon.ui import EXAMPLE, PracticeDialog, StarDialog  # noqa: E402


def main():
    app = QApplication([])
    with tempfile.TemporaryDirectory() as scratch:
        mw = QMainWindow()
        mw.col = Collection(str(Path(scratch) / "collection.anki2"))
        dialog = StarDialog(mw)
        dialog.show()
        dialog.context.setPlainText(
            "A stack follows last in, first out.\nRAM means random-access memory."
        )
        app.processEvents()
        output = ROOT / "docs/images"
        output.mkdir(exist_ok=True)
        dialog.grab().save(str(output / "prepare.png"))
        dialog.raw.setPlainText(json.dumps(EXAMPLE, ensure_ascii=False, indent=2))
        dialog.validate()
        dialog.tabs.setCurrentIndex(1)
        app.processEvents()
        dialog.grab().save(str(output / "review.png"))
        practice = PracticeDialog(dialog, questions(dialog.selected_notes()), "Learn")
        practice.show()
        app.processEvents()
        practice.grab().save(str(output / "practice.png"))
        practice.close()
        dialog.close()
        mw.col.close()
        print(f"Rendered screenshots in {output}")


if __name__ == "__main__":
    main()
