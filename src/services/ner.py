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
from ..utils.text_utils import normalize_text as _norm


# --- Helpers ------------------------------------------------------------------


# --- 1. PERSON NAMES (team members) ------------------------------------------


def extract_person_entities_from_sentence(
    sentence: PreprocessedSentence,
    team: Team,
    context_sentences: List[PreprocessedSentence] = None,
) -> List[Entity]:
    """
    Find mentions of known team members in the sentence and surrounding context.
    We only care about your project team, not arbitrary names.
    
    Args:
        sentence: The sentence to search in
        team: Team object with member names
        context_sentences: Optional list of surrounding sentences for context
    """
    entities: List[Entity] = []
    
    # Search in both raw_text and cleaned_text
    texts_to_search = [
        sentence.raw_text,
        sentence.cleaned_text,
    ]
    
    # Add context sentences if provided
    if context_sentences:
        for ctx_sent in context_sentences:
            texts_to_search.extend([ctx_sent.raw_text, ctx_sent.cleaned_text])

    for member in team.members:
        name = member.name
        name_norm = _norm(name)
        name_parts = name_norm.split()  # Handle multi-word names
        
        # Skip if name is too short (likely false positive)
        if len(name_norm) < 2:
            continue

        for text in texts_to_search:
            if not text:
                continue
                
            text_norm = _norm(text)
            
            # Method 1: Exact word boundary match (most reliable)
            # Use regex to find whole word matches
            pattern = r"\b" + re.escape(name_norm) + r"\b"
            matches = list(re.finditer(pattern, text_norm))
            
            for match in matches:
                entities.append(
                    Entity(
                        text=name,
                        type=EntityType.PERSON,
                        start_char=match.start(),
                        end_char=match.end(),
                    )
                )
            
            # Method 2: If no word boundary match, try substring but verify it's a word
            if not matches and name_norm in text_norm:
                idx = text_norm.find(name_norm)
                # Verify it's not part of another word
                if idx > 0:
                    char_before = text_norm[idx - 1]
                    if char_before.isalnum():
                        continue  # Part of another word
                if idx + len(name_norm) < len(text_norm):
                    char_after = text_norm[idx + len(name_norm)]
                    if char_after.isalnum():
                        continue  # Part of another word
                
                # It's a standalone word/phrase
                entities.append(
                    Entity(
                        text=name,
                        type=EntityType.PERSON,
                        start_char=idx,
                        end_char=idx + len(name_norm),
                    )
                )
            
            # Method 3: For multi-word names, check if all parts appear together
            if len(name_parts) > 1:
                # Check if all parts appear in sequence
                pattern_parts = r"\b" + r"\s+".join([re.escape(part) for part in name_parts]) + r"\b"
                matches_parts = list(re.finditer(pattern_parts, text_norm))
                for match in matches_parts:
                    # Avoid duplicates
                    if not any(e.text == name and e.start_char == match.start() for e in entities):
                        entities.append(
                            Entity(
                                text=name,
                                type=EntityType.PERSON,
                                start_char=match.start(),
                                end_char=match.end(),
                            )
                        )
            
            # If we found the name, no need to search in other texts
            if entities and any(e.text == name for e in entities):
                break

    # Deduplicate entities
    unique_entities = []
    seen = set()
    for ent in entities:
        key = (ent.type, ent.text, ent.start_char)
        if key not in seen:
            seen.add(key)
            unique_entities.append(ent)

    return unique_entities


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
    context_sentences: List[PreprocessedSentence] = None,
) -> List[Entity]:
    persons = extract_person_entities_from_sentence(sentence, team, context_sentences)
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
    For each Task, find the corresponding source sentence and surrounding context,
    then populate:
        - mentioned_people
        - technical_terms
        - time_expressions
    
    This function also searches surrounding sentences for person mentions,
    as names are often mentioned in adjacent sentences.
    """
    # If team not provided, load from default JSON
    if team is None:
        team = load_team()

    # Create a lookup from sentence id -> sentence
    sentence_map = {s.id: s for s in sentences}
    
    # Create sentence list for context lookup
    sentence_list = sorted(sentences, key=lambda s: s.id)

    for task in tasks:
        if task.source_sentence_id is None:
            continue

        sent = sentence_map.get(task.source_sentence_id)
        if not sent:
            continue

        # Get surrounding sentences for context (names often mentioned nearby)
        context_sentences = []
        sent_idx = next((i for i, s in enumerate(sentence_list) if s.id == sent.id), -1)
        if sent_idx >= 0:
            # Get 2 sentences before and 2 after for context
            start_idx = max(0, sent_idx - 2)
            end_idx = min(len(sentence_list), sent_idx + 3)
            context_sentences = sentence_list[start_idx:end_idx]
            # Remove the main sentence from context (already included)
            context_sentences = [s for s in context_sentences if s.id != sent.id]

        entities = extract_entities_for_sentence(sent, team, context_sentences)

        # If no people found in immediate context, search broader context
        # (names might be mentioned earlier in the conversation)
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
        
        # Fallback: If no people found, search in broader context (up to 10 sentences before)
        if not people and sent_idx >= 0:
            broader_context = sentence_list[max(0, sent_idx - 10):sent_idx]
            if broader_context:
                broader_entities = extract_person_entities_from_sentence(
                    sent, team, broader_context
                )
                for ent in broader_entities:
                    if ent.text not in people:
                        people.append(ent.text)

        task.mentioned_people = people
        task.technical_terms = tech_terms
        task.time_expressions = time_exprs

    return tasks
