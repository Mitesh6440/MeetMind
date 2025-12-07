from __future__ import annotations

from pathlib import Path
from typing import List
import re

from models.entities import Entity, EntityType
from models.task import Task
from models.nlp import PreprocessedSentence
from models.team import Team, TeamMember

from .skill_matching import SKILL_KEYWORDS  # reuse your skill mapping
from .team_loader import load_team


# --- Helpers ------------------------------------------------------------------


def _norm(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


# --- 1. PERSON NAMES (team members) ------------------------------------------


def extract_person_entities_from_sentence(
    sentence: PreprocessedSentence,
    team: Team,
) -> List[Entity]:
    """
    Find mentions of known team members in the sentence.
    We only care about your project team, not arbitrary names.
    """
    text_norm = _norm(sentence.raw_text)
    entities: List[Entity] = []

    for member in team.members:
        name = member.name
        name_norm = _norm(name)

        # Simple substring search (case-insensitive)
        idx = text_norm.find(name_norm)
        if idx != -1:
            entities.append(
                Entity(
                    text=name,
                    type=EntityType.PERSON,
                    start_char=idx,
                    end_char=idx + len(name_norm),
                )
            )

    return entities


# --- 2. TECHNICAL TERMS (login bug, database, API, etc.) ---------------------


# Extra technical phrases not already nicely covered by SKILL_KEYWORDS
TECH_PHRASES = [
    "login bug",
    "login issue",
    "home page",
    "landing page",
    "dashboard",
    "api response",
    "database migration",
    "null pointer",
    "timeout error",
    "performance issue",
]

def extract_technical_entities_from_sentence(
    sentence: PreprocessedSentence,
) -> List[Entity]:
    """
    Use SKILL_KEYWORDS + TECH_PHRASES to find technical terms.
    """
    entities: List[Entity] = []
    sentence = sentence.cleaned_text
    text_norm = _norm(sentence)

    # 1) From SKILL_KEYWORDS (React, API, database, etc.)
    for skill, keywords in SKILL_KEYWORDS.items():
        for kw in keywords:
            kw_norm = _norm(kw)
            idx = text_norm.find(kw_norm)
            if idx != -1:
                entities.append(
                    Entity(
                        text=skill,  # use canonical skill name as entity text
                        type=EntityType.TECHNICAL,
                        start_char=idx,
                        end_char=idx + len(kw_norm),
                    )
                )
                break  # avoid duplicate entity per skill

    # 2) From additional TECH_PHRASES
    for phrase in TECH_PHRASES:
        phrase_norm = _norm(phrase)
        idx = text_norm.find(phrase_norm)
        if idx != -1:
            entities.append(
                Entity(
                    text=phrase,
                    type=EntityType.TECHNICAL,
                    start_char=idx,
                    end_char=idx + len(phrase_norm),
                )
            )

    # Deduplicate by text
    unique: List[Entity] = []
    seen_texts = set()
    for ent in entities:
        key = (ent.type, ent.text.lower())
        if key not in seen_texts:
            seen_texts.add(key)
            unique.append(ent)

    return unique


# --- 3. TIME EXPRESSIONS (tomorrow, Friday, next week, etc.) -----------------


SIMPLE_TIME_WORDS = [
    "today",
    "tomorrow",
    "tonight",
    "yesterday",
]

RELATIVE_TIME_PHRASES = [
    "day after tomorrow",
    "this evening",
    "this morning",
    "this afternoon",
    "this week",
    "this month",
    "next week",
    "next month",
    "next quarter",
    "end of this week",
    "end of the week",
    "by eod",
    "by end of day",
]

WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

def extract_time_entities_from_sentence(
    sentence: PreprocessedSentence,
) -> List[Entity]:
    """
    Detect simple time expressions like:
    - tomorrow, today
    - next week, this Friday
    - by Monday, before Friday
    """
    entities: List[Entity] = []
    sentence = sentence.cleaned_text
    text_norm = _norm(sentence)

    # 1) Relative phrases
    for phrase in RELATIVE_TIME_PHRASES:
        phrase_norm = _norm(phrase)
        idx = text_norm.find(phrase_norm)
        if idx != -1:
            entities.append(
                Entity(
                    text=phrase,
                    type=EntityType.TIME,
                    start_char=idx,
                    end_char=idx + len(phrase_norm),
                )
            )

    # 2) Simple words (today, tomorrow, etc.)
    for word in SIMPLE_TIME_WORDS:
        word_norm = _norm(word)
        # use regex word boundary
        for match in re.finditer(rf"\b{re.escape(word_norm)}\b", text_norm):
            entities.append(
                Entity(
                    text=word,
                    type=EntityType.TIME,
                    start_char=match.start(),
                    end_char=match.end(),
                )
            )

    # 3) Weekday mentions: "on Friday", "by Monday", "before Tuesday"
    for wd in WEEKDAYS:
        for match in re.finditer(rf"\b{wd}\b", text_norm):
            entities.append(
                Entity(
                    text=wd.capitalize(),
                    type=EntityType.TIME,
                    start_char=match.start(),
                    end_char=match.end(),
                )
            )

    # 4) Simple "by X" or "before X" patterns
    # e.g. "by Friday", "before next week"
    pattern = r"\b(by|before)\s+(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month)\b"
    for match in re.finditer(pattern, text_norm):
        expr = text_norm[match.start():match.end()]
        entities.append(
            Entity(
                text=expr,
                type=EntityType.TIME,
                start_char=match.start(),
                end_char=match.end(),
            )
        )

    # Deduplicate by text
    unique: List[Entity] = []
    seen_texts = set()
    for ent in entities:
        key = (ent.type, ent.text.lower())
        if key not in seen_texts:
            seen_texts.add(key)
            unique.append(ent)

    return unique


# --- 4. Aggregate NER for a given sentence -----------------------------------


def extract_entities_for_sentence(
    sentence: PreprocessedSentence,
    team: Team,
) -> List[Entity]:
    persons = extract_person_entities_from_sentence(sentence, team)
    techs = extract_technical_entities_from_sentence(sentence)
    times = extract_time_entities_from_sentence(sentence)
    return persons + techs + times


# --- 5. Attach entities to Task objects --------------------------------------


def enrich_tasks_with_entities(
    tasks: List[Task],
    sentences: List[PreprocessedSentence],
    team: Team | None = None,
) -> List[Task]:
    """
    For each Task, find the corresponding source sentence and
    populate:
        - mentioned_people
        - technical_terms
        - time_expressions
    """
    # If team not provided, load from default JSON
    if team is None:
        team = load_team()

    # Create a lookup from sentence id -> sentence
    sentence_map = {s.id: s for s in sentences}

    for task in tasks:
        if task.source_sentence_id is None:
            continue

        sent = sentence_map.get(task.source_sentence_id)
        if not sent:
            continue

        entities = extract_entities_for_sentence(sent, team)

        people = []
        tech_terms = []
        time_exprs = []

        for ent in entities:
            if ent.type == EntityType.PERSON:
                if ent.text not in people:
                    people.append(ent.text)
            elif ent.type == EntityType.TECHNICAL:
                if ent.text not in tech_terms:
                    tech_terms.append(ent.text)
            elif ent.type == EntityType.TIME:
                if ent.text not in time_exprs:
                    time_exprs.append(ent.text)

        task.mentioned_people = people
        task.technical_terms = tech_terms
        task.time_expressions = time_exprs

    return tasks
