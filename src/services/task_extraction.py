from __future__ import annotations

from typing import List
import re

from models.task import Task
from models.nlp import PreprocessedSentence
from ..utils.text_utils import normalize_text


# --- 1. Patterns & keyword lists ---------------------------------------------

# Imperative / action verbs common in tech meetings
ACTION_VERBS = [
    "fix", "update", "design", "implement", "create", "write", "test",
    "refactor", "review", "deploy", "configure", "set up", "setup",
    "optimize", "add", "remove", "check", "investigate", "analyze",
    "resolve", "handle", "build", "develop", "install", "integrate",
    "modify", "improve", "enhance", "debug", "troubleshoot", "verify",
    "validate", "document", "prepare", "organize", "schedule", "plan",
]

# Phrases that often indicate action items
ACTION_PHRASES = [
    "need to", "should", "must", "let's", "lets", "have to",
    "we will", "we'll", "i will", "i'll", "going to", "gonna",
    "plan to", "make sure to", "ensure that", "make sure",
    "will need", "would need", "could", "might need",
]

# Phrases that *often* indicate decisions / summary rather than tasks
NON_TASK_HINTS = [
    "we discussed", "we talked about", "we already", "as we know",
    "remember that", "we decided", "we agreed", "we concluded",
    "it was", "it is", "that was", "this is", "we have",
]


# --- 2. Decide if a sentence is task-like ------------------------------------


def is_task_sentence(sent: PreprocessedSentence) -> bool:
    """
    Heuristic check if a sentence sounds like an action item / task.

    Uses multiple strategies:
    - Leading imperative verbs ("Fix the login bug", "Update the API")
    - Modal phrases ("We need to deploy", "You should test")
    - Action verbs anywhere in sentence with context
    - Avoids non-task summary phrases
    """
    cleaned = normalize_text(sent.cleaned_text)
    if not cleaned:
        return False

    # Quick rejection: if sentence is extremely short
    words = cleaned.split()
    if len(words) < 3:
        return False

    # Rule 0: avoid obvious non-task sentences
    for phrase in NON_TASK_HINTS:
        if phrase in cleaned:
            return False

    # Rule 1: starts with an action verb ("fix the bug", "update the UI")
    first_word = words[0] if words else ""
    first_two = " ".join(words[:2]) if len(words) >= 2 else ""
    first_three = " ".join(words[:3]) if len(words) >= 3 else ""
    
    for verb in ACTION_VERBS:
        verb_words = verb.split()
        # Single word verbs
        if len(verb_words) == 1:
            if first_word == verb or cleaned.startswith(verb + " "):
                return True
        # Multi-word verbs (e.g., "set up")
        elif len(verb_words) == 2:
            if first_two == verb or cleaned.startswith(verb + " "):
                return True

    # Rule 2: contains action phrases with verification
    for phrase in ACTION_PHRASES:
        if phrase in cleaned:
            # Verify there's an action verb after the phrase
            phrase_idx = cleaned.find(phrase)
            text_after_phrase = cleaned[phrase_idx + len(phrase):].strip()
            
            # Check if any action verb appears after the phrase
            for verb in ACTION_VERBS:
                verb_words = verb.split()
                if len(verb_words) == 1:
                    if text_after_phrase.startswith(verb) or f" {verb} " in text_after_phrase:
                        return True
                elif len(verb_words) == 2:
                    if text_after_phrase.startswith(verb) or verb in text_after_phrase:
                        return True
            
            # If phrase is at start and sentence is action-oriented, accept it
            if phrase_idx < 10:  # Phrase near the start
                return True

    # Rule 3: Question-style assignments ("Can you ...", "Will you ...")
    question_patterns = [
        r"^(can|will|could|would)\s+you\s+",
        r"^(please|kindly)\s+",
    ]
    for pattern in question_patterns:
        if re.match(pattern, cleaned):
            return True

    # Rule 4: "Let's ..." or "We should ..." style
    if cleaned.startswith(("let's ", "lets ", "we should ", "we need ", "we must ")):
        return True

    # Rule 5: Action verb appears anywhere with task context
    # Look for action verbs that aren't at the start but have task indicators
    for verb in ACTION_VERBS:
        if verb in cleaned:
            verb_idx = cleaned.find(verb)
            # Check if verb is preceded by task indicators
            before_verb = cleaned[max(0, verb_idx - 20):verb_idx]
            task_indicators = ["need", "should", "must", "will", "going to", "plan"]
            if any(indicator in before_verb for indicator in task_indicators):
                return True

    return False


# --- 3. Extract Task objects from preprocessed sentences ---------------------


def extract_tasks_from_sentences(
    sentences: List[PreprocessedSentence],
    starting_id: int = 1,
) -> List[Task]:
    """
    Iterate over preprocessed sentences and extract Task objects
    for those that look like action items.

    Returns:
        List of Task objects with:
        - id
        - description (cleaned_text)
        - source_sentence_id
    """
    tasks: List[Task] = []
    current_id = starting_id

    for s in sentences:
        if not is_task_sentence(s):
            continue

        # Use cleaned_text as task description; raw_text can be used later for context if needed
        description = s.cleaned_text.strip()
        if not description:
            continue

        task = Task(
            id=current_id,
            description=description,
            source_sentence_id=s.id,
        )
        tasks.append(task)
        current_id += 1

    return tasks
