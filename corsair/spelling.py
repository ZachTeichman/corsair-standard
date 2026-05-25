from __future__ import annotations

from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional

from .docx_parser import DocumentModel, ParagraphModel


WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'’-]*[A-Za-z]|[A-Za-z]")
URL_OR_EMAIL_PATTERN = re.compile(r"(?:https?://|www\.|@)", re.IGNORECASE)

DICTIONARY_PATHS = (
    Path("/usr/share/dict/words"),
    Path("/usr/share/dict/web2"),
    Path("/usr/share/dict/connectives"),
    Path("/usr/share/dict/propernames"),
)

RESUME_ALLOWLIST = {
    "api",
    "apis",
    "ats",
    "bba",
    "bloomberg",
    "capex",
    "coordinated",
    "coordinate",
    "coordinates",
    "coordinating",
    "corsair",
    "crm",
    "css",
    "csv",
    "dcf",
    "ebitda",
    "excel",
    "fintech",
    "gpa",
    "html",
    "javascript",
    "linkedin",
    "macros",
    "modeling",
    "optimized",
    "optimizing",
    "powerpoint",
    "python",
    "quickbooks",
    "sql",
    "tableau",
    "typescript",
    "uga",
    "valuation",
    "vba",
}

COMMON_MISSPELLINGS = {
    "acheived": "achieved",
    "accomodate": "accommodate",
    "accomodated": "accommodated",
    "accomodating": "accommodating",
    "accomplised": "accomplished",
    "adminstrative": "administrative",
    "analysed": "analyzed",
    "analyzis": "analysis",
    "assited": "assisted",
    "collaberated": "collaborated",
    "committe": "committee",
    "communiction": "communication",
    "comunication": "communication",
    "coordinanted": "coordinated",
    "coordintated": "coordinated",
    "definately": "definitely",
    "developement": "development",
    "effeciency": "efficiency",
    "enviroment": "environment",
    "excelent": "excellent",
    "experiance": "experience",
    "finanical": "financial",
    "forcast": "forecast",
    "forcasting": "forecasting",
    "goverment": "government",
    "implimented": "implemented",
    "improvment": "improvement",
    "inital": "initial",
    "intership": "internship",
    "maintanance": "maintenance",
    "managment": "management",
    "neccessary": "necessary",
    "oppurtunity": "opportunity",
    "optmized": "optimized",
    "organizaiton": "organization",
    "orginized": "organized",
    "perfromed": "performed",
    "preperation": "preparation",
    "presentaion": "presentation",
    "prioritzed": "prioritized",
    "reccomend": "recommend",
    "recieved": "received",
    "relevent": "relevant",
    "represenative": "representative",
    "reserach": "research",
    "responsibilites": "responsibilities",
    "responsiblities": "responsibilities",
    "succesful": "successful",
    "sucessful": "successful",
    "teh": "the",
    "thier": "their",
    "untill": "until",
}


@lru_cache(maxsize=1)
def _dictionary_words() -> set[str]:
    words: set[str] = set()
    for path in DICTIONARY_PATHS:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    word = line.strip().lower()
                    if len(word) >= 2 and word.replace("'", "").isalpha():
                        words.add(word)
        except OSError:
            continue
    words.update(RESUME_ALLOWLIST)
    return words


@lru_cache(maxsize=1)
def _dictionary_candidates() -> tuple[str, ...]:
    return tuple(sorted(_dictionary_words()))


def _is_mixed_or_all_caps(token: str) -> bool:
    letters = [char for char in token if char.isalpha()]
    if not letters:
        return True
    if len(token) > 1 and token.isupper():
        return True
    return any(char.isupper() for char in token[1:])


def _normalize_token(token: str) -> str:
    return token.strip("'’").replace("’", "'").lower()


def _is_known_word(lower: str, dictionary: set[str]) -> bool:
    if lower in dictionary or lower in RESUME_ALLOWLIST:
        return True

    candidates: set[str] = set()
    if lower.endswith("ies") and len(lower) > 4:
        candidates.add(lower[:-3] + "y")
    if lower.endswith("s") and len(lower) > 4:
        candidates.add(lower[:-1])
    if lower.endswith("ed") and len(lower) > 5:
        stem = lower[:-2]
        candidates.update({stem, stem + "e"})
    if lower.endswith("ing") and len(lower) > 6:
        stem = lower[:-3]
        candidates.update({stem, stem + "e"})
    if lower.endswith("ers") and len(lower) > 5:
        candidates.update({lower[:-1], lower[:-3]})
    if lower.endswith("er") and len(lower) > 5:
        candidates.add(lower[:-2])

    return any(candidate in dictionary or candidate in RESUME_ALLOWLIST for candidate in candidates)


def _should_skip_token(token: str, lower: str, dictionary: set[str]) -> bool:
    if lower in COMMON_MISSPELLINGS:
        return False
    if len(lower) < 4:
        return True
    if not lower.replace("'", "").isalpha():
        return True
    if _is_known_word(lower, dictionary):
        return True
    if _is_mixed_or_all_caps(token):
        return True
    if token[0].isupper() and lower not in COMMON_MISSPELLINGS:
        return True
    return False


def _suggestion(lower: str, dictionary: set[str]) -> Optional[str]:
    if lower in COMMON_MISSPELLINGS:
        return COMMON_MISSPELLINGS[lower]
    if not dictionary:
        return None
    matches = get_close_matches(lower, _dictionary_candidates(), n=1, cutoff=0.88)
    if not matches:
        return None
    suggestion = matches[0]
    if abs(len(suggestion) - len(lower)) > 2:
        return None
    return suggestion


def _paragraph_findings(paragraph: ParagraphModel, dictionary: set[str]) -> List[Dict[str, Any]]:
    if paragraph.is_blank or URL_OR_EMAIL_PATTERN.search(paragraph.text):
        return []

    findings: List[Dict[str, Any]] = []
    seen_words: set[str] = set()
    for match in WORD_PATTERN.finditer(paragraph.text):
        token = match.group(0)
        lower = _normalize_token(token)
        if lower in seen_words:
            continue
        if _should_skip_token(token, lower, dictionary):
            continue
        suggestion = _suggestion(lower, dictionary)
        if suggestion is None:
            continue
        seen_words.add(lower)
        findings.append(
            {
                "word": token,
                "suggestion": suggestion,
                "target_ranges": [{"start": match.start(), "end": match.end(), "text": token}],
            }
        )
        if len(findings) >= 3:
            break
    return findings


def find_spelling_issues(
    document: DocumentModel,
    excluded_paragraph_indices: Iterable[int] = (),
) -> List[Dict[str, Any]]:
    dictionary = _dictionary_words()
    if not dictionary:
        return []

    excluded = set(excluded_paragraph_indices)
    issues: List[Dict[str, Any]] = []
    for paragraph in document.paragraphs:
        if paragraph.index in excluded:
            continue
        findings = _paragraph_findings(paragraph, dictionary)
        if not findings:
            continue
        issues.append({"paragraph": paragraph, "findings": findings})
        if len(issues) >= 8:
            break
    return issues
