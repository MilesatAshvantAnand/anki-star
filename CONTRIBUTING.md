# Contributing

Start with a GitHub issue describing the user’s task and Anki/macOS versions.
Please use synthetic source material and remove private coursework from reports.

The `addon` directory is the complete Python package loaded by Anki. `core.py`
and `practice.py` are independent of the Anki UI. `collection.py` handles real
Anki collection operations; `ui.py` uses Anki’s Qt wrappers and background
operation helpers. `native/ocr.swift` is the optional local Apple Vision helper.

Set up the environment using the README. Run tests, lint and formatting before
submitting a pull request. Collection tests use temporary collections, never the
user’s Anki profile. UI tests run with Qt offscreen. Mac OCR is built from source;
do not commit compiled executables or private collections.

To test manually, build the package and install into a separate Anki profile/base
folder. Use all note types, import twice to check duplicates, undo/redo, then
practice. Check light/dark mode and both Apple Silicon and Intel when available.

Keep copy/paste mode working without API keys. Do not add hidden uploads,
clipboard monitoring, browser cookie extraction or silent changes to scheduling.
New network or persistence features need explicit user controls and documentation.
