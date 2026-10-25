import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from anki.collection import Collection
from aqt.qt import QApplication, QMainWindow

from addon.ui import StarDialog


@pytest.fixture(scope="session")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def window(app, tmp_path):
    mw = QMainWindow()
    mw.col = Collection(str(tmp_path / "collection.anki2"))
    dialog = StarDialog(mw)
    yield dialog
    dialog.close()
    mw.col.close()
