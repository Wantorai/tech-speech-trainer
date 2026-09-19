"""Deterministic word alignment and transcription accuracy, without AI."""

import re
import unicodedata
from dataclasses import dataclass

CONTRACTIONS = {
    "can't": "can not",
    "cannot": "can not",
    "won't": "will not",
    "shan't": "shall not",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "haven't": "have not",
    "hasn't": "has not",
    "hadn't": "had not",
    "couldn't": "could not",
    "wouldn't": "would not",
    "shouldn't": "should not",
    "mustn't": "must not",
    "i'm": "i am",
    "you're": "you are",
    "we're": "we are",
    "they're": "they are",
    "i've": "i have",
    "you've": "you have",
    "we've": "we have",
    "they've": "they have",
    "i'll": "i will",
    "you'll": "you will",
    "he'll": "he will",
    "she'll": "she will",
    "it'll": "it will",
    "we'll": "we will",
    "they'll": "they will",
}
NUMBERS = {
    word: str(number)
    for number, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
    )
}


def normalize(text: str) -> list[str]:
    """Ignore case and punctuation; preserve meaningful internal apostrophes."""
    text = (
        unicodedata.normalize("NFKC", text).lower().replace("’", "'").replace("‘", "'")
    )
    words = re.findall(r"[^\W_]+(?:'[^\W_]+)*", text)
    return [
        NUMBERS.get(part, part)
        for word in words
        for part in CONTRACTIONS.get(word, word).split()
    ]


@dataclass(frozen=True)
class Difference:
    kind: str
    expected: str
    heard: str
    possible_typo: bool = False


@dataclass(frozen=True)
class Comparison:
    score: float
    reference_count: int
    errors: int
    alignment: tuple[Difference, ...]

    @property
    def matches(self) -> int:
        """Count matching words in the normalized alignment."""
        return sum(item.kind == "match" for item in self.alignment)

    @property
    def differences(self) -> tuple[Difference, ...]:
        """Return substitutions, missing words, and extra words in order."""
        return tuple(item for item in self.alignment if item.kind != "match")


def _distances(reference, answer) -> list[list[int]]:
    """Levenshtein edit costs for all prefixes of two sequences."""
    costs = [list(range(len(answer) + 1))]
    for i, expected in enumerate(reference, start=1):
        row = [i]
        for j, heard in enumerate(answer, start=1):
            row.append(
                min(
                    costs[i - 1][j] + 1,
                    row[j - 1] + 1,
                    costs[i - 1][j - 1] + (expected != heard),
                )
            )
        costs.append(row)
    return costs


def _possible_typo(expected: str, heard: str) -> bool:
    """A spelling hint only: never discounts an error or infers its cause."""
    if min(len(expected), len(heard)) < 4 or abs(len(expected) - len(heard)) > 1:
        return False
    if _distances(expected, heard)[-1][-1] == 1:
        return True
    if len(expected) == len(heard):
        positions = [i for i, (a, b) in enumerate(zip(expected, heard)) if a != b]
        if len(positions) == 2:
            i, j = positions
            return j == i + 1 and expected[i] == heard[j] and expected[j] == heard[i]
    return False


def compare(transcript: str, answer: str) -> Comparison:
    """Align normalized words and calculate differences and accuracy."""
    reference, written = normalize(transcript), normalize(answer)
    if not reference:
        raise ValueError("The reference must contain words")
    costs = _distances(reference, written)
    i, j = len(reference), len(written)
    alignment = []
    # Tie order is stable: match, replacement, missing word, extra word.
    while i or j:
        if i and j and reference[i - 1] == written[j - 1]:
            alignment.append(Difference("match", reference[i - 1], written[j - 1]))
            i, j = i - 1, j - 1
        elif i and j and costs[i][j] == costs[i - 1][j - 1] + 1:
            expected, heard = reference[i - 1], written[j - 1]
            alignment.append(
                Difference(
                    "replacement", expected, heard, _possible_typo(expected, heard)
                )
            )
            i, j = i - 1, j - 1
        elif i and costs[i][j] == costs[i - 1][j] + 1:
            alignment.append(Difference("missing", reference[i - 1], ""))
            i -= 1
        else:
            alignment.append(Difference("extra", "", written[j - 1]))
            j -= 1
    errors = costs[-1][-1]
    return Comparison(
        score=round(max(0, 100 * (1 - errors / len(reference))), 1),
        reference_count=len(reference),
        errors=errors,
        alignment=tuple(reversed(alignment)),
    )
