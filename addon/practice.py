"""Local practice only; no scheduling or review-history writes."""

import random
import re
import unicodedata
from dataclasses import dataclass

from .core import CLOZE


@dataclass(frozen=True)
class Question:
    front: str
    answer: str


def questions(notes):
    result = []
    for note in notes:
        if note.type == "cloze":
            for index in sorted({m.group(1) for m in CLOZE.finditer(note.front)}, key=int):
                answers = []

                def replace(match):
                    answer, *hint = match.group(2).split("::", 1)
                    if match.group(1) == index:
                        answers.append(answer)
                        return f"[{hint[0] if hint else '…'}]"
                    return answer

                front = CLOZE.sub(replace, note.front)
                result.append(Question(front, "; ".join(answers)))
        else:
            result.append(Question(note.front, note.back))
            if note.type == "reversed":
                result.append(Question(note.back, note.front))
    return result


def normalize(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).strip()).casefold()


def choices(question, pool, rng=None):
    rng = rng or random
    distractors = list(
        dict.fromkeys(q.answer for q in pool if normalize(q.answer) != normalize(question.answer))
    )
    options = rng.sample(distractors, min(3, len(distractors))) + [question.answer]
    rng.shuffle(options)
    return options
