from __future__ import annotations

from typing import List
import re

from models.task import Task
from models.nlp import PreprocessedSentence


# --- 1. Patterns & keyword lists ---------------------------------------------

# Imperative / action verbs common in tech meetings
ACTION_VERBS = [
    "fix",
    "update",
    "design",
    "implement",
    "create",
    "write",
    "test",
    "refactor",
    "review",
    "deploy",
    "configure",
    "set up",
    "setup",
    "optimize",
    "add",
    "remove",
    "check",
    "investigate",
    "analyze",
    "resolve",
    "handle",
]

# Phrases that often indicate action items
ACTION_PHRASES = [
    "need to",
    "should",
    "must",
    "let's",
    "lets",
    "have to",
    "we will",
    "we'll",
    "plan to",
    "make sure to",
    "ensure that",
]

# Phrases that *often* indicate decisions / summary rather than tasks
NON_TASK_HINTS = [
    "we discussed",
    "we talked about",
    "we already",
    "as we know",
    "remember that",
]


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# --- 2. Decide if a sentence is task-like ------------------------------------


def is_task_sentence(sent: PreprocessedSentence) -> bool:
    """
    Heuristic check if a sentence sounds like an action item / task.

    Uses:
    - Leading imperative verbs ("Fix the login bug", "Update the API")
    - Modal phrases ("We need to deploy", "You should test")
    - Avoids some non-task summary phrases
    """
    cleaned = _norm(sent.cleaned_text)
    if not cleaned:
        return False

    # Quick rejection: if sentence is extremely short
    if len(cleaned.split()) < 3:
        return False

    # Rule 0: avoid obvious non-task sentences
    for phrase in NON_TASK_HINTS:
        if phrase in cleaned:
            return False

    tokens = cleaned.split()

    # Rule 1: starts with an action verb ("fix the bug", "update the UI")
    first_two = " ".join(tokens[:2])
    for verb in ACTION_VERBS:
        # Check "fix" and "set up" type verbs
        if cleaned.startswith(verb + " ") or first_two.startswith(verb + " "):
            return True

    # Rule 2: contains action phrases like "need to", "should", etc.
    for phrase in ACTION_PHRASES:
        if phrase in cleaned:
            # Also make sure there's a verb-ish word after it
            # e.g., "need to fix", "should update", "must design"
            return True

    # Rule 3: "Can you ...", "Will you ..." style
    if cleaned.startswith("can you ") or cleaned.startswith("will you "):
        return True

    # Rule 4: "Let's ..." tasks
    if cleaned.startswith("let's ") or cleaned.startswith("lets "):
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
