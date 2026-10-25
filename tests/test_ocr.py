import platform
import zipfile
from pathlib import Path

import pytest
from aqt.qt import QColor, QFont, QImage, QPainter

from addon import ocr

PACKAGE = Path(__file__).resolve().parents[1] / "dist/anki-star-0.1.0-macos.ankiaddon"
pytestmark = pytest.mark.skipif(
    platform.system() != "Darwin" or not PACKAGE.exists(),
    reason="Build the macOS OCR package first",
)


def test_packaged_ocr_reads_image_and_rejects_missing_file(app, tmp_path, monkeypatch):
    with zipfile.ZipFile(PACKAGE) as archive:
        archive.extractall(tmp_path / "installed")
    monkeypatch.setattr(ocr, "__file__", str(tmp_path / "installed/ocr.py"))
    picture = QImage(1200, 240, QImage.Format.Format_RGB32)
    picture.fill(QColor("white"))
    painter = QPainter(picture)
    painter.setPen(QColor("black"))
    painter.setFont(QFont("Arial", 48))
    painter.drawText(40, 100, "Anki Star coursework")
    painter.drawText(40, 190, "A stack uses LIFO.")
    painter.end()
    image_path = tmp_path / "text.png"
    assert picture.save(str(image_path))
    text = ocr.recognize(image_path)
    assert "Anki Star" in text and "LIFO" in text
    with pytest.raises(RuntimeError, match="could not be opened"):
        ocr.recognize(tmp_path / "missing.png")
