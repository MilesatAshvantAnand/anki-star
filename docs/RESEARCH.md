# Anki, Quizlet, and the case for Anki Star

Research checked 25 October 2026. This is a review of official documentation and
project descriptions, not a hands-on certification of third-party add-ons.

## What “Anki format” means

There are two separate decisions: **how a note tests you**, and **how information
gets into Anki**. A note holds fields; a card is a question generated from those
fields. One note may create several independently scheduled cards.

| Note type | Example | Best use |
| --- | --- | --- |
| Basic | “What is osmosis?” → short definition | Questions, concepts, cause and effect |
| Basic and reversed | “bonjour” ↔ “hello” | Vocabulary and other unambiguous pairs; creates two cards |
| Optional reversed | Basic plus an optional reverse | Mix one-way and two-way pairs |
| Type in the answer | “2⁵?” → type “32” | Spelling, short exact answers; Anki shows a text comparison, you rate recall |
| Cloze | “A stack follows {{c1::last in, first out}}.” | Facts in context; c1 and c2 generate separate cards |
| Image Occlusion | Cover a diagram label and recall it | Anatomy, maps, diagrams; built into Anki 23.10+ |

Start with Basic and Cloze. Reverse only when both directions make sense. Keep
questions specific and answers short; use an explanation field for context.
Sources: [Anki concepts and note types](https://docs.ankiweb.net/manual/getting-started),
[editing and image occlusion](https://docs.ankiweb.net/manual/editing).

| File / exchange format | Purpose |
| --- | --- |
| UTF-8 TXT / TSV / CSV | Rows of fields, usually Front and Back; map columns in Anki’s import dialog |
| APKG | Deck package, including note types and potentially media |
| COLPKG | Collection export; not the usual choice for adding a few new course notes |
| ANKIADDON | An add-on installer, not a deck |
| Anki Star JSON | Our plain-text exchange schema for mixed note types; Anki itself does not import this JSON directly |

Anki’s text importer supports delimited fields, quoting, tags, HTML and media
references, subject to its import options. Its flexibility means careless column
mapping can lose information. Anki Star uses explicit fields and validates the
whole batch first. See [Anki text imports](https://docs.ankiweb.net/manual/importing/text-files)
and [add-on packaging](https://docs.ankiweb.net/addons/sharing).

## Which Quizlet features can be recreated?

Quizlet documents Flashcards, Learn, Test and Match; Learn uses progressively
challenging question formats. Smart Assist creates editable draft flashcards
from pasted notes, uploads or prompts. Availability and limits can depend on
Quizlet’s current plan and product changes.
Sources: [study modes](https://quizlet.com/ca/features/studymodes),
[Learn](https://quizlet.com/features/learn),
[Smart Assist](https://help.quizlet.com/hc/en-ca/articles/39606772122509-Creating-study-sets-with-Smart-Assist).

| Capability | In Anki / feasibility | Anki Star v0.1 |
| --- | --- | --- |
| Traditional flashcards | Built in | Additional reveal/self-check practice |
| Long-term spaced repetition | Built in; keep Anki responsible for scheduling | Practice never writes review history |
| Learn-style practice | Feasible as a separate session | Multiple choice, then typed recall; repeats misses until two consecutive correct responses per question |
| Mixed practice test | Feasible without AI if answers already exist | Alternates choice and typed questions; score and answer review |
| Match | Feasible locally | Up to six unique prompt/answer pairs and elapsed time |
| Notes/images → draft cards | Model needed for semantic question generation | External assistant generates; Mac OCR extracts text locally |
| Edit drafts before import | Straightforward | Editable table, selection, validation, retained source references |
| Diagram label hiding | Built into Anki | Explained in guide; use native Image Occlusion editor |
| Audio / pronunciation | Anki supports audio/TTS templates | Deferred; no audio generation in v0.1 |
| Stars / difficult material | Anki has flags, marked notes, tags and filtered decks | Tags supported; no separate stars database |
| Shared sets / classrooms / Live | Needs a service, moderation, accounts and multiplayer infrastructure | Deferred; GitHub shares the code, not private coursework |
| AI tutoring and generated distractors | Needs a model or external assistant | Deferred; choices reuse other cards’ answers |

We can recreate useful interactions independently. We are not copying Quizlet’s
branding, content library, private algorithms or visual assets. Multiple choice
is a warm-up; a plausible wrong answer cannot be guaranteed when distractors are
simply taken from nearby cards.

## Existing open-source options and their tradeoffs

There **are** overlapping tools. “Nobody has built this” would be an inaccurate
reason to start another project. The narrower case is a Mac-first native add-on
combining a manual assistant handoff, image text extraction, mixed note preview
and a few local study modes in one installer.

| Project | Useful capabilities | Documented limitation / assessment |
| --- | --- | --- |
| [Chat to Flashcards / Chat to Anki](https://github.com/voidash/chatGPT-to-Anki) | No API key; uses existing ChatGPT/Claude/Perplexity chats; preview/edit and Anki integration | README describes two components and manual browser developer-mode installation; NotebookLM is not in its supported-platform list. This is the closest overlap, so trying it first is reasonable. |
| [NotebookLM Flashcard Generator](https://github.com/DrTakotsubo/Notebooklm-flashcard-generator) | PDF → cards through NotebookLM, no API key, custom prompts | Requires auth-helper execution and Playwright/browser login; README describes expiring authentication and cookie problems. It removes numeric citations, whereas we retain explicit source fields. Reliability here is an inference from its setup, not a newly reproduced bug. |
| [anki-llm](https://github.com/endovix/anki-llm) | Explicit manual copy/paste mode without a key, validation and duplicate tooling | Terminal/TUI workflow and configuration make it a different fit for someone wanting an ordinary Anki window. Strong alternative for technical users. |
| [Notosaurus](https://github.com/cchabanois/notosaurus) | Photos of lessons → reviewed Anki cards, open source, standalone and add-on options | Current AnkiWeb description asks users to choose an AI service and paste its key; good fit if API setup becomes acceptable. [Listing](https://ankiweb.net/shared/info/1956931509). |
| [Quizlet Importer Extended](https://github.com/sviatoslav-lebediev/anki-quizlet-importer-extended) | Imports existing Quizlet sets with text, images/audio and optional reverse | Moves existing sets; it does not solve coursework → question generation or recreate Learn/Test/Match. Source-site access and extraction are dependencies. |
| Native Anki Image Occlusion | Hides regions directly on an image | Already solves diagram masking. OCR/question generation is a separate need; another masking editor would duplicate good existing work. |

AnkiGPT Smart Prompts also surfaced in search, but its linked GitHub repository
returned 404 during this review. Its current implementation could not be
inspected, so this report makes no maintenance or quality claim about it.

## Implementation decisions

- The assistant is used manually in the user’s own browser. No stored cookies,
  embedded web login, provider API keys, browser scraping, or dependency on a
  particular assistant’s page layout.
- A generated prompt asks for grounded, atomic cards with source references.
  References are retained but not independently verified.
- JSON supports mixed note types. Two-column TSV is accepted for simple pairs.
- AI text is escaped before storage, so pasted scripts, remote image tags and
  Anki sound directives are not interpreted as active content.
- Dedicated note types keep the user’s existing note templates intact.
  Duplicate checks use Anki’s first-field / note-type rule across decks.
- Import is a single undo step, with rollback on exceptions. It skips existing
  notes instead of silently updating their answers.
- Local OCR uses Apple Vision in a small universal executable. It reads image
  text; it does not infer the meaning of diagrams. Handwriting, mathematical
  notation, columns and unsupported languages need manual review.
- v0.1 is an initial release. The exact tested versions and limitations are
  recorded in [VALIDATION.md](VALIDATION.md).

## Suggested next steps

1. Test the workflow on a real lecture and refine the prompt against your exam.
2. Add draft sessions saved explicitly by the user and a friendlier multiline editor.
3. Add import previews for pre-existing custom note types and duplicate diffs.
4. Add optional local model support only if desired; keep manual mode first-class.
5. Broaden practice to selected existing notes, with explicit field mapping.
6. Consider AnkiWeb distribution after real-user testing and compatibility checks.
