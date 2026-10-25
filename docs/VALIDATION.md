# Validation

Initial release checks on 25 October 2026, macOS on Apple Silicon, Python 3.12.

## Verified locally

- 35 tests pass with Anki/aqt 26.9.3, the version installed on this Mac.
- The same 35 tests also pass against Anki/aqt 25.9.2.
- Tests use real, disposable Anki collections: all four note types generate and
  render cards; Reversed and multi-number Cloze generate multiple cards.
- Duplicate notes are skipped within a batch and across decks without changing
  existing answers. Invalid batches do not import partially.
- A simulated failure during import rolls back added notes and note types.
  Successful imports undo and redo as a single step.
- The package installs using Anki’s own AddonManager into a temporary add-ons
  folder, loads, registers Tools → Anki Star, and opens its native Qt dialog.
- Qt tests cover row editing and selection, stale-preview protection, explicit
  clipboard copying, Learn repetition, Test scoring/accepting alternatives, and
  unambiguous Match pairs.
- Pasted HTML and Anki sound directives remain inert text.
- The macOS package includes an ad-hoc-signed universal Apple Vision helper.
  Its ARM executable extracts text from a synthetic image through the packaged
  Python wrapper and rejects a missing image with a readable error.
- Source, review and practice screenshots were rendered from the actual Qt
  interface and visually inspected. These are not mockups.
- Ruff lint and formatting checks pass. Build output passes ZIP integrity checks
  and includes the required manifest and root-level entry point.

## Limits of this evidence

Tests open the add-on UI with a minimal main-window fixture and exercise the real
Anki collection and add-on manager. They do not reproduce every full-app event,
third-party add-on interaction, sync state or profile-switch scenario.

The universal helper includes Intel code, but runtime OCR was tested only on
Apple Silicon. Windows/Linux OCR is not implemented. The generic package’s
non-OCR workflow has not been exercised on those operating systems.

No real user collection was modified during testing. No real coursework was sent
to an assistant. Source-grounded accuracy still requires the user to review the
external assistant’s response. OCR of handwriting, equations and complex page
layouts is not validated by the simple printed-English fixture.

Practice sessions are deliberately separate from Anki scheduling. Learn uses a
small local mastery rule, not Quizlet’s private adaptive model. Typed scoring is
text comparison with a self-override, not semantic grading.
