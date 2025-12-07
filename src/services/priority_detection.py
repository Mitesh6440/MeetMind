from __future__ import annotations

from typing import List, Optional
from enum import Enum
import re

from models.task import Task
from models.nlp import PreprocessedSentence
from ..utils.text_utils import normalize_text as _norm


class PriorityLevel(str, Enum):
    """Priority levels for tasks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# --- 1. Priority Keywords -----------------------------------------------------

# Critical priority keywords (highest urgency)
CRITICAL_KEYWORDS = [
    "critical",
    "urgent",
    "emergency",
    "asap",
    "as soon as possible",
    "immediately",
    "right away",
    "blocking",
    "blocker",
    "p0",
    "priority 0",
    "severity 0",
    "sev 0",
    "production down",
    "site down",
    "service down",
    "outage",
    "breakage",
    "broken",
    "not working",
    "down",
]

# High priority keywords
HIGH_KEYWORDS = [
    "high priority",
    "important",
    "soon",
    "quickly",
    "fast",
    "p1",
    "priority 1",
    "severity 1",
    "sev 1",
    "before release",
    "for release",
    "release blocker",
    "must have",
    "required",
    "necessary",
    "essential",
]

# Medium priority keywords (default if no indicators)
MEDIUM_KEYWORDS = [
    "medium priority",
    "normal",
    "standard",
    "p2",
    "priority 2",
    "should have",
    "nice to have",
]

# Low priority keywords
LOW_KEYWORDS = [
    "low priority",
    "whenever",
    "eventually",
    "later",
    "p3",
    "priority 3",
    "p4",
    "priority 4",
    "backlog",
    "future",
    "optional",
    "if time permits",
]

# Context phrases that indicate high/critical priority
CRITICAL_CONTEXT_PHRASES = [
    "blocking users",
    "users cannot",
    "users can't",
    "users are unable",
    "preventing access",
    "preventing login",
    "preventing signup",
    "preventing checkout",
    "preventing payment",
    "data loss",
    "security issue",
    "security vulnerability",
    "security breach",
    "privacy issue",
    "compliance issue",
    "legal issue",
    "regulatory",
    "production issue",
    "live issue",
    "customer facing",
    "revenue impact",
    "financial impact",
    "money loss",
    "revenue loss",
]

HIGH_CONTEXT_PHRASES = [
    "before release",
    "for release",
    "release blocker",
    "release critical",
    "launch blocker",
    "launch critical",
    "deadline approaching",
    "upcoming deadline",
    "time sensitive",
    "customer request",
    "client request",
    "stakeholder request",
    "executive request",
    "management request",
    "feature request",
    "user request",
    "performance issue",
    "performance problem",
    "scalability issue",
    "user experience",
    "ux issue",
]

LOW_CONTEXT_PHRASES = [
    "nice to have",
    "if time permits",
    "when we have time",
    "future enhancement",
    "future improvement",
    "optimization",
    "refactoring",
    "cleanup",
    "documentation",
    "code cleanup",
    "technical debt",
]


# --- 2. Priority Detection Functions ------------------------------------------


def detect_priority_from_keywords(text: str) -> Optional[PriorityLevel]:
    """
    Detect priority level from explicit priority keywords in text.
    Returns the highest priority found (Critical > High > Medium > Low).
    """
    text_norm = _norm(text)
    
    # Check for critical keywords
    for keyword in CRITICAL_KEYWORDS:
        if keyword in text_norm:
            return PriorityLevel.CRITICAL
    
    # Check for high keywords
    for keyword in HIGH_KEYWORDS:
        if keyword in text_norm:
            return PriorityLevel.HIGH
    
    # Check for low keywords
    for keyword in LOW_KEYWORDS:
        if keyword in text_norm:
            return PriorityLevel.LOW
    
    # Check for medium keywords
    for keyword in MEDIUM_KEYWORDS:
        if keyword in text_norm:
            return PriorityLevel.MEDIUM
    
    return None


def detect_priority_from_context(text: str) -> Optional[PriorityLevel]:
    """
    Detect priority level from context phrases that indicate urgency.
    """
    text_norm = _norm(text)
    
    # Check for critical context
    for phrase in CRITICAL_CONTEXT_PHRASES:
        if phrase in text_norm:
            return PriorityLevel.CRITICAL
    
    # Check for high context
    for phrase in HIGH_CONTEXT_PHRASES:
        if phrase in text_norm:
            return PriorityLevel.HIGH
    
    # Check for low context
    for phrase in LOW_CONTEXT_PHRASES:
        if phrase in text_norm:
            return PriorityLevel.LOW
    
    return None


def detect_priority_from_deadline(task: Task) -> Optional[PriorityLevel]:
    """
    Infer priority from deadline proximity.
    Tasks with very near deadlines get higher priority.
    """
    if task.deadline is None:
        return None
    
    from datetime import datetime, timedelta
    
    now = datetime.now()
    time_until_deadline = task.deadline - now
    
    # Critical if deadline is within 24 hours
    if time_until_deadline <= timedelta(hours=24):
        return PriorityLevel.CRITICAL
    
    # High if deadline is within 3 days
    if time_until_deadline <= timedelta(days=3):
        return PriorityLevel.HIGH
    
    # Medium if deadline is within 2 weeks
    if time_until_deadline <= timedelta(days=14):
        return PriorityLevel.MEDIUM
    
    # Low if deadline is far away
    return PriorityLevel.LOW


def detect_priority_from_sentence(
    sentence: PreprocessedSentence,
    task: Optional[Task] = None
) -> PriorityLevel:
    """
    Detect priority level from a sentence using multiple strategies:
    1. Explicit priority keywords
    2. Context phrases
    3. Deadline proximity (if task provided)
    
    Returns the highest priority detected, defaulting to MEDIUM.
    """
    text = sentence.cleaned_text
    
    # Strategy 1: Check explicit keywords (highest confidence)
    keyword_priority = detect_priority_from_keywords(text)
    if keyword_priority:
        return keyword_priority
    
    # Strategy 2: Check context phrases
    context_priority = detect_priority_from_context(text)
    if context_priority:
        return context_priority
    
    # Strategy 3: Check deadline proximity (if task has deadline)
    if task and task.deadline:
        deadline_priority = detect_priority_from_deadline(task)
        if deadline_priority:
            return deadline_priority
    
    # Default to medium priority
    return PriorityLevel.MEDIUM


# --- 3. Enrich Tasks with Priority --------------------------------------------


def enrich_tasks_with_priority(
    tasks: List[Task],
    sentences: List[PreprocessedSentence]
) -> List[Task]:
    """
    Assign priority levels to tasks based on their descriptions and context.
    
    For each task:
    1. Look at the source sentence for priority indicators
    2. Check deadline proximity
    3. Assign the highest priority detected
    """
    # Create lookup from sentence id -> sentence
    sentence_map = {s.id: s for s in sentences}
    
    for task in tasks:
        if task.source_sentence_id is None:
            # No source sentence, default to medium
            task.priority = PriorityLevel.MEDIUM.value
            continue
        
        sent = sentence_map.get(task.source_sentence_id)
        if not sent:
            task.priority = PriorityLevel.MEDIUM.value
            continue
        
        # Detect priority from sentence and task context
        priority = detect_priority_from_sentence(sent, task)
        task.priority = priority.value  # Convert enum to string value
    
    return tasks

