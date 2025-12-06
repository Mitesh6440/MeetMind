from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import re

from difflib import SequenceMatcher

from models.task import Task
from models.team import TeamMember


# --- 1. Canonical skill database / mapping -----------------------------------

# Canonical skills used in the system.
# You can extend this list any time.
CANONICAL_SKILLS: List[str] = [
    "React",
    "JavaScript",
    "UI bugs",
    "Frontend",
    "Backend",
    "Node.js",
    "Databases",
    "API design",
    "Testing",
    "Automation",
    "Bug tracking",
    "UI/UX",
    "Figma",
]

# For each canonical skill, define keywords / phrases that may appear in tasks.
# This is your "skill database" in code form.
SKILL_KEYWORDS: Dict[str, List[str]] = {
    "React": [
        "react",
        "react.js",
        "reactjs",
        "frontend component",
        "react component",
    ],
    "JavaScript": [
        "javascript",
        "js code",
        "js bug",
        "script error",
    ],
    "UI bugs": [
        "ui bug",
        "alignment issue",
        "button not visible",
        "frontend bug",
        "layout issue",
    ],
    "Frontend": [
        "frontend",
        "ui",
        "user interface",
        "screen design",
    ],
    "Backend": [
        "backend",
        "server side",
        "api bug",
        "business logic",
    ],
    "Node.js": [
        "node",
        "node.js",
        "nodejs",
        "express route",
    ],
    "Databases": [
        "database",
        "db",
        "query",
        "sql",
        "mongo",
        "mongodb",
    ],
    "API design": [
        "api",
        "endpoint",
        "rest",
        "http request",
    ],
    "Testing": [
        "testing",
        "test case",
        "testcases",
        "qa",
        "quality check",
    ],
    "Automation": [
        "automation",
        "automated tests",
        "selenium",
        "cypress",
    ],
    "Bug tracking": [
        "bug tracking",
        "jira",
        "ticket",
        "issue tracking",
    ],
    "UI/UX": [
        "ui/ux",
        "ux",
        "user experience",
        "wireframe",
        "prototype",
    ],
    "Figma": [
        "figma",
        "design file",
        "figma screen",
    ],
}


# --- 2. Fuzzy matching utilities ---------------------------------------------


def _normalize(text: str) -> str:
    """Basic normalization: lowercase + remove extra spaces."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fuzzy_score(a: str, b: str) -> float:
    """
    Compute a fuzzy similarity score between two short strings.
    Uses Python's built-in SequenceMatcher
    Returns value between 0.0 and 1.0.
    """
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def fuzzy_match_skill(token: str, skills: List[str], threshold: float = 0.75) -> str | None:
    """
    Given a token (word/phrase) and a list of canonical skills,
    return the best-matching skill if similarity >= threshold.
    Otherwise return None.
    """
    best_skill = None
    best_score = 0.0

    for skill in skills:
        score = fuzzy_score(token, skill)
        if score > best_score:
            best_score = score
            best_skill = skill

    if best_skill and best_score >= threshold:
        return best_skill
    return None


# --- 3. Map task description -> required skills ------------------------------


def infer_required_skills_from_description(description: str) -> List[str]:
    """
    Parse a task description and infer required canonical skills using:

    1. Keyword matching (SKILL_KEYWORDS)
    2. Fuzzy matching fallback for unknown phrases
    """
    desc_norm = _normalize(description)
    found_skills: List[str] = []

    # 1) Keyword-based detection
    for skill, keywords in SKILL_KEYWORDS.items():
        for kw in keywords:
            if _normalize(kw) in desc_norm:
                found_skills.append(skill)
                break  # avoid duplicate for same skill

    # 2) Fuzzy matching for individual words / short phrases
    #    (useful when phrasing is slightly different)
    tokens = re.split(r"[,.!;:/\-]+|\s+", desc_norm)
    tokens = [t for t in tokens if t]  # remove empty

    for token in tokens:
        matched_skill = fuzzy_match_skill(token, CANONICAL_SKILLS, threshold=0.85)
        if matched_skill:
            found_skills.append(matched_skill)

    # Deduplicate while preserving order
    unique_skills: List[str] = []
    for s in found_skills:
        if s not in unique_skills:
            unique_skills.append(s)

    return unique_skills


def enrich_task_with_skills(task: Task) -> Task:
    """
    Take a Task object and fill its required_skills field based on description.
    Returns the same task (for convenience).
    """
    task.required_skills = infer_required_skills_from_description(task.description)
    return task


# --- 4. Score team members vs required skills (used later for assignment) ----


@dataclass
class MemberSkillMatch:
    member: TeamMember
    matched_skills: List[str]
    score: float  # simple ratio: matched / required


def match_team_members_for_task(task: Task, team_members: List[TeamMember]) -> List[MemberSkillMatch]:
    """
    Given a Task (with required_skills already set) and a list of TeamMembers,
    compute a simple skill match score for each member.

    Returns:
        Sorted list of MemberSkillMatch (best match first).
    """
    if not task.required_skills:
        # No required skills extracted -> everyone equal
        return [
            MemberSkillMatch(member=m, matched_skills=[], score=0.0)
            for m in team_members
        ]

    result: List[MemberSkillMatch] = []

    for member in team_members:
        member_skills_norm = [_normalize(s) for s in member.skills]
        matched: List[str] = []

        for req_skill in task.required_skills:
            req_norm = _normalize(req_skill)

            # Exact-ish match against member skills (lowercased)
            if any(req_norm in s or s in req_norm for s in member_skills_norm):
                matched.append(req_skill)

        score = len(matched) / len(task.required_skills)
        result.append(MemberSkillMatch(member=member, matched_skills=matched, score=score))

    # Sort: highest score first
    result.sort(key=lambda ms: ms.score, reverse=True)
    return result
