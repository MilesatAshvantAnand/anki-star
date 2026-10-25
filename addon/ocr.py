import json
import platform
import subprocess
from pathlib import Path


def recognize(path):
    if platform.system() != "Darwin":
        raise RuntimeError("Local image text recognition currently requires macOS 13 or later.")
    binary = Path(__file__).parent / "bin" / "anki-star-ocr"
    if not binary.exists():
        raise RuntimeError(
            "The OCR helper is missing. Install the macOS release package, "
            "or copy text with macOS Live Text and paste it here."
        )
    binary.chmod(binary.stat().st_mode | 0o100)
    try:
        result = subprocess.run(
            [str(binary), str(Path(path).resolve())],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Text recognition timed out. Try a smaller image.") from error
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[:600] or "Could not read this image.")
    text = json.loads(result.stdout)["text"]
    if not text.strip():
        raise RuntimeError("No readable text found. Try a clearer, upright image.")
    return text
