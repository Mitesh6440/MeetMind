from __future__ import annotations

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import re

from models.task import Task
from models.team import Team, TeamMember
from models.nlp import PreprocessedSentence
from ..utils.text_utils import normalize_text as _norm
from .skill_matching import (
    enrich_task_with_skills,
    match_team_members_for_task,
    MemberSkillMatch,
    infer_required_skills_from_description
)
from .team_loader import load_team


class AssignmentError(Exception):
    """Custom exception for assignment errors."""
    pass


# --- 1. Assignment Result Data Structures -------------------------------------

@dataclass
class AssignmentResult:
    """Result of assigning a task to a team member."""
    task_id: int
    assigned_to: Optional[str]  # Team member name
    confidence: float  # 0.0 to 1.0
    assignment_method: str  # "explicit", "skill_match", "role_match", "fallback"
    reasoning: str  # Human-readable explanation
    alternative_assignments: List[Tuple[str, float]]  # [(name, confidence), ...]


@dataclass
class WorkloadInfo:
    """Tracks workload for a team member."""
    member_name: str
    task_count: int
    critical_tasks: int
    high_priority_tasks: int


# --- 2. Explicit Assignment Detection (Priority 1) ----------------------------

def detect_explicit_assignment(
    task: Task,
    sentence: PreprocessedSentence,
    team: Team
) -> Optional[Tuple[str, float]]:
    """
    Detect if a task is explicitly assigned to someone by name.
    
    Looks for patterns like:
    - "Sakshi will fix the bug"
    - "Assign this to Moe"
    - "Let Sakshi handle this"
    - "Moe, please fix..."
    
    Returns:
        Tuple of (member_name, confidence) if found, None otherwise.
        Confidence is 1.0 for explicit assignments.
    """
    text = sentence.raw_text
    text_norm = _norm(text)
    
    # Assignment patterns
    assignment_patterns = [
        r"(\w+)\s+(?:will|should|must|can|shall)\s+",
        r"(?:assign|give|hand)\s+(?:this|it|task)\s+(?:to|for)\s+(\w+)",
        r"let\s+(\w+)\s+(?:handle|do|fix|work|take)",
        r"(\w+)[,\s]+(?:please|can you|will you)",
        r"(?:for|to)\s+(\w+)\s+(?:to|will)",
    ]
    
    # Check each team member's name
    for member in team.members:
        name_norm = _norm(member.name)
        
        # Check if name appears in assignment context
        for pattern in assignment_patterns:
            matches = re.finditer(pattern, text_norm)
            for match in matches:
                mentioned_name = _norm(match.group(1))
                if mentioned_name == name_norm or name_norm in mentioned_name:
                    # Verify it's in assignment context (not just mentioned)
                    # Check proximity to task-related words
                    context_words = ["fix", "do", "handle", "work", "task", "assign", "update", "create"]
                    text_around = text_norm[max(0, match.start()-20):match.end()+20]
                    if any(word in text_around for word in context_words):
                        return (member.name, 1.0)
        
        # Direct name mention near task description
        if name_norm in text_norm:
            # Check if name is mentioned in the same sentence as task
            task_keywords = ["fix", "update", "create", "implement", "do", "handle", "work"]
            if any(kw in text_norm for kw in task_keywords):
                # Check proximity
                name_idx = text_norm.find(name_norm)
                task_words_in_range = [
                    kw for kw in task_keywords
                    if kw in text_norm[max(0, name_idx-30):name_idx+30]
                ]
                if task_words_in_range:
                    return (member.name, 0.9)  # High confidence but not 1.0
    
    return None


# --- 3. Skill-Based Matching (Priority 2) -------------------------------------

def calculate_skill_match_score(
    task: Task,
    member: TeamMember,
    skill_matches: List[MemberSkillMatch]
) -> Tuple[float, List[str]]:
    """
    Calculate skill-based match score for a member.
    
    Returns:
        Tuple of (score, matched_skills_list)
    """
    # Find this member's match in the skill matches
    for match in skill_matches:
        if match.member.name == member.name:
            return (match.score, match.matched_skills)
    
    return (0.0, [])


def skill_based_assignment(
    task: Task,
    team: Team,
    skill_matches: List[MemberSkillMatch],
    workload: Dict[str, WorkloadInfo] = None
) -> List[Tuple[str, float, List[str]]]:
    """
    Get skill-based assignment candidates sorted by match score.
    Includes workload balancing in sorting to break ties.
    
    Returns:
        List of (member_name, confidence, matched_skills) tuples
    """
    candidates = []
    
    # Calculate average workload for tie-breaking
    avg_workload = 0.0
    if workload and team:
        total_tasks = sum(w.task_count for w in workload.values())
        avg_workload = total_tasks / len(team.members) if team.members else 0
    
    for match in skill_matches:
        if match.score > 0:
            # Convert skill match score to confidence
            # Perfect match (1.0) = 0.9 confidence
            # Partial match (0.5) = 0.7 confidence
            # Low match (0.25) = 0.5 confidence
            confidence = min(0.9, 0.5 + (match.score * 0.4))
            
            # Adjust for workload (prefer less loaded members when scores are similar)
            if workload and match.member.name in workload:
                member_workload = workload[match.member.name].task_count
                if member_workload < avg_workload:
                    # Boost confidence slightly for less loaded members
                    confidence = min(0.95, confidence + 0.05)
                elif member_workload > avg_workload + 2:
                    # Reduce confidence for overloaded members
                    confidence = max(0.1, confidence - 0.1)
            
            candidates.append((match.member.name, confidence, match.matched_skills))
        elif match.score == 0 and not task.required_skills:
            # If no skills required, include everyone with low confidence
            # But adjust based on workload
            confidence = 0.3
            if workload and match.member.name in workload:
                member_workload = workload[match.member.name].task_count
                if member_workload < avg_workload:
                    confidence = 0.4  # Prefer less loaded
                elif member_workload > avg_workload + 1:
                    confidence = 0.2  # Penalize overloaded
            candidates.append((match.member.name, confidence, match.matched_skills))
    
    # Sort by confidence (highest first), then by workload (least loaded first) for ties
    if workload:
        candidates.sort(key=lambda x: (
            -x[1],  # Negative for descending confidence
            workload.get(x[0], WorkloadInfo(x[0], 0, 0, 0)).task_count  # Ascending workload
        ))
    else:
        candidates.sort(key=lambda x: x[1], reverse=True)
    
    return candidates


# --- 4. Role-Based Matching (Priority 3) -------------------------------------

# Role to skill mapping for fallback matching
ROLE_SKILL_MAPPING = {
    "frontend": ["React", "JavaScript", "UI bugs", "Frontend", "UI/UX"],
    "backend": ["Backend", "Node.js", "Databases", "API design"],
    "designer": ["UI/UX", "Figma", "Frontend"],
    "qa": ["Testing", "Automation", "Bug tracking"],
    "engineer": ["React", "JavaScript", "Node.js", "Backend", "Frontend"],
    "developer": ["React", "JavaScript", "Node.js", "Backend", "Frontend"],
}


def role_based_assignment(
    task: Task,
    team: Team
) -> List[Tuple[str, float]]:
    """
    Get role-based assignment candidates as fallback.
    
    Returns:
        List of (member_name, confidence) tuples
    """
    if not task.required_skills:
        # No skills to match, return all members with low confidence
        return [(m.name, 0.3) for m in team.members]
    
    candidates = []
    
    for member in team.members:
        member_role_norm = _norm(member.role)
        confidence = 0.0
        
        # Check if member's role matches task requirements
        for skill in task.required_skills:
            skill_norm = _norm(skill)
            
            # Check role-skill mapping
            for role_key, skills in ROLE_SKILL_MAPPING.items():
                if role_key in member_role_norm and skill in skills:
                    confidence = max(confidence, 0.6)  # Moderate confidence
            
            # Direct role match (e.g., "Frontend" task -> "Frontend Developer")
            if skill_norm in member_role_norm or member_role_norm in skill_norm:
                confidence = max(confidence, 0.7)
        
        if confidence > 0:
            candidates.append((member.name, confidence))
    
    # If no role matches, return all with very low confidence
    if not candidates:
        candidates = [(m.name, 0.2) for m in team.members]
    
    # Sort by confidence
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates


# --- 5. Workload Balancing (Advanced) ----------------------------------------

def calculate_workload(
    tasks: List[Task],
    team: Team
) -> Dict[str, WorkloadInfo]:
    """
    Calculate current workload for each team member.
    """
    workload: Dict[str, WorkloadInfo] = {}
    
    # Initialize workload for all members
    for member in team.members:
        workload[member.name] = WorkloadInfo(
            member_name=member.name,
            task_count=0,
            critical_tasks=0,
            high_priority_tasks=0
        )
    
    # Count assigned tasks
    for task in tasks:
        if task.assigned_to:
            if task.assigned_to in workload:
                workload[task.assigned_to].task_count += 1
                if task.priority == "critical":
                    workload[task.assigned_to].critical_tasks += 1
                elif task.priority == "high":
                    workload[task.assigned_to].high_priority_tasks += 1
    
    return workload


def adjust_confidence_for_workload(
    member_name: str,
    base_confidence: float,
    workload: Dict[str, WorkloadInfo],
    task_priority: Optional[str],
    team: Team = None
) -> float:
    """
    Adjust assignment confidence based on workload balancing.
    
    Reduces confidence if member is overloaded, especially for low-priority tasks.
    Also considers relative workload compared to team average.
    """
    if member_name not in workload:
        return base_confidence
    
    info = workload[member_name]
    
    # Calculate workload score
    workload_score = info.task_count
    
    # Penalize if member has many critical/high priority tasks
    if task_priority in ["medium", "low"]:
        workload_score += info.critical_tasks * 2
        workload_score += info.high_priority_tasks * 1.5
    
    # Calculate average workload for comparison
    if team and len(team.members) > 1:
        total_tasks = sum(w.task_count for w in workload.values())
        avg_workload = total_tasks / len(team.members)
        
        # If this member has significantly more tasks than average, reduce confidence
        if info.task_count > avg_workload + 1:
            # Calculate how much more loaded they are
            overload_ratio = (info.task_count - avg_workload) / max(avg_workload, 1)
            # Reduce confidence proportionally (more reduction for higher overload)
            reduction = min(0.4, overload_ratio * 0.15)  # Up to 40% reduction
            base_confidence = max(0.1, base_confidence - reduction)
    
    # Additional reduction if overloaded (absolute threshold)
    if workload_score > 3:
        reduction = min(0.3, (workload_score - 3) * 0.1)  # Stronger reduction
        return max(0.1, base_confidence - reduction)
    
    return base_confidence


# --- 6. Reasoning Generator ----------------------------------------------------

def generate_assignment_reasoning(
    task: Task,
    assigned_to: Optional[str],
    assignment_method: str,
    matched_skills: List[str] = None,
    team: Team = None
) -> str:
    """
    Generate human-readable reasoning for task assignment.
    """
    if not assigned_to:
        return "No suitable assignment found. Task requires manual review."
    
    member = next((m for m in team.members if m.name == assigned_to), None) if team else None
    
    reasons = []
    
    # Method-based reasoning
    if assignment_method == "explicit":
        reasons.append(f"Explicitly assigned to {assigned_to}")
    elif assignment_method == "skill_match":
        if matched_skills:
            skills_str = ", ".join(matched_skills)
            reasons.append(f"Skill match: {assigned_to} has {skills_str}")
        else:
            reasons.append(f"Best skill match: {assigned_to}")
    elif assignment_method == "role_match":
        if member:
            reasons.append(f"Role match: {assigned_to} is {member.role}")
        else:
            reasons.append(f"Role-based assignment: {assigned_to}")
    elif assignment_method == "fallback":
        reasons.append(f"Fallback assignment: {assigned_to}")
    
    # Priority-based reasoning
    if task.priority == "critical":
        reasons.append("Critical priority task")
    elif task.priority == "high":
        reasons.append("High priority task")
    
    # Context-based reasoning
    # Use full sentence text for better context checking
    task_text = task.source_sentence_text if task.source_sentence_text else task.description
    if "blocking" in task_text.lower() or "blocking" in str(task.technical_terms).lower():
        reasons.append("Blocking issue")
    
    if task.deadline:
        from datetime import datetime
        days_until = (task.deadline - datetime.now()).days
        if days_until <= 1:
            reasons.append("Urgent deadline")
        elif days_until <= 3:
            reasons.append("Near deadline")
    
    # Technical context
    if task.technical_terms:
        tech_str = ", ".join(task.technical_terms[:2])
        reasons.append(f"Technical context: {tech_str}")
    
    return ". ".join(reasons) + "."


# --- 7. Main Assignment Engine ------------------------------------------------

def assign_task(
    task: Task,
    sentences: List[PreprocessedSentence],
    team: Team,
    existing_tasks: List[Task] = None,
    skill_matches: List[MemberSkillMatch] = None
) -> AssignmentResult:
    """
    Main assignment engine that tries multiple strategies in priority order.
    
    Priority 1: Explicit assignment (name mentioned)
    Priority 2: Skill-based matching
    Priority 3: Role-based matching
    Priority 4: Fallback (first available)
    """
    if existing_tasks is None:
        existing_tasks = []
    
    # Get source sentence
    sentence = None
    if task.source_sentence_id:
        sentence = next(
            (s for s in sentences if s.id == task.source_sentence_id),
            None
        )
    
    # Ensure task has skills extracted
    if not task.required_skills:
        enrich_task_with_skills(task)
    
    # Get skill matches if not provided
    if skill_matches is None:
        skill_matches = match_team_members_for_task(task, team.members)
    
    # Calculate workload
    workload = calculate_workload(existing_tasks, team)
    
    # Priority 1: Explicit assignment
    if sentence:
        explicit = detect_explicit_assignment(task, sentence, team)
        if explicit:
            member_name, confidence = explicit
            # Adjust for workload (but explicit assignments have high priority)
            # Only reduce if severely overloaded
            if workload and member_name in workload:
                info = workload[member_name]
                if info.task_count > 8:  # Only reduce if very overloaded
                    confidence = max(0.7, confidence - 0.2)
            reasoning = generate_assignment_reasoning(
                task, member_name, "explicit", team=team
            )
            # Get alternatives
            alternatives = skill_based_assignment(task, team, skill_matches, workload)
            alt_list = [(name, conf) for name, conf, _ in alternatives[:3] if name != member_name]
            return AssignmentResult(
                task_id=task.id,
                assigned_to=member_name,
                confidence=confidence,
                assignment_method="explicit",
                reasoning=reasoning,
                alternative_assignments=alt_list
            )
    
    # Priority 2: Skill-based matching
    skill_candidates = skill_based_assignment(task, team, skill_matches, workload)
    if skill_candidates:
        # Find best candidate considering workload
        best_candidate = None
        best_score = -1
        
        for candidate in skill_candidates:
            member_name, base_confidence, matched_skills = candidate
            # Calculate final score with workload adjustment
            final_confidence = adjust_confidence_for_workload(
                member_name, base_confidence, workload, task.priority, team
            )
            # Use a composite score: confidence + workload bonus
            if workload and member_name in workload:
                member_workload = workload[member_name].task_count
                # Calculate average workload
                if team and len(team.members) > 1:
                    avg_workload = sum(w.task_count for w in workload.values()) / len(team.members)
                    # Bonus for being less loaded than average
                    if member_workload < avg_workload:
                        workload_bonus = (avg_workload - member_workload) * 0.05
                        final_confidence = min(0.95, final_confidence + workload_bonus)
            
            if final_confidence > best_score:
                best_score = final_confidence
                best_candidate = (member_name, final_confidence, matched_skills)
        
        if best_candidate:
            member_name, confidence, matched_skills = best_candidate
            reasoning = generate_assignment_reasoning(
                task, member_name, "skill_match", matched_skills, team
            )
            # Get alternatives (excluding the chosen one)
            alt_list = [(name, conf) for name, conf, _ in skill_candidates if name != member_name][:3]
            return AssignmentResult(
                task_id=task.id,
                assigned_to=member_name,
                confidence=confidence,
                assignment_method="skill_match",
                reasoning=reasoning,
                alternative_assignments=alt_list
            )
    
    # Priority 3: Role-based matching
    role_candidates = role_based_assignment(task, team)
    if role_candidates:
        # Find best candidate considering workload (not just first one)
        best_candidate = None
        best_score = -1
        
        for member_name, base_confidence in role_candidates:
            # Adjust for workload
            confidence = adjust_confidence_for_workload(
                member_name, base_confidence, workload, task.priority, team
            )
            # Add workload bonus/penalty
            if workload and member_name in workload:
                member_workload = workload[member_name].task_count
                if team and len(team.members) > 1:
                    avg_workload = sum(w.task_count for w in workload.values()) / len(team.members)
                    if member_workload < avg_workload:
                        confidence = min(0.95, confidence + 0.05)
            
            if confidence > best_score:
                best_score = confidence
                best_candidate = (member_name, confidence)
        
        if best_candidate:
            member_name, confidence = best_candidate
            reasoning = generate_assignment_reasoning(
                task, member_name, "role_match", team=team
            )
            # Get alternatives (excluding the chosen one)
            alt_list = [(name, conf) for name, conf in role_candidates if name != member_name][:3]
            return AssignmentResult(
                task_id=task.id,
                assigned_to=member_name,
                confidence=confidence,
                assignment_method="role_match",
                reasoning=reasoning,
                alternative_assignments=alt_list
            )
    
    # Priority 4: Fallback (least loaded member)
    if team.members:
        # Find least loaded member
        least_loaded = min(
            team.members,
            key=lambda m: workload.get(m.name, WorkloadInfo(m.name, 0, 0, 0)).task_count
        )
        reasoning = generate_assignment_reasoning(
            task, least_loaded.name, "fallback", team=team
        )
        return AssignmentResult(
            task_id=task.id,
            assigned_to=least_loaded.name,
            confidence=0.1,
            assignment_method="fallback",
            reasoning=reasoning,
            alternative_assignments=[]
        )
    
    # No assignment possible
    return AssignmentResult(
        task_id=task.id,
        assigned_to=None,
        confidence=0.0,
        assignment_method="none",
        reasoning="No team members available for assignment",
        alternative_assignments=[]
    )


# --- 8. Batch Assignment with Conflict Resolution ----------------------------

def assign_all_tasks(
    tasks: List[Task],
    sentences: List[PreprocessedSentence],
    team: Team = None
) -> List[AssignmentResult]:
    """
    Assign all tasks, handling conflicts and dependencies.
    
    Processes tasks in priority order (critical first) and respects dependencies.
    """
    if team is None:
        team = load_team()
    
    # Sort tasks by priority and dependencies
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_tasks = sorted(
        tasks,
        key=lambda t: (
            priority_order.get(t.priority or "medium", 2),
            len(t.dependencies)  # Tasks with dependencies come later
        )
    )
    
    results = []
    assigned_tasks = []
    
    # Pre-compute skill matches for all tasks
    task_skill_matches = {}
    for task in sorted_tasks:
        if not task.required_skills:
            enrich_task_with_skills(task)
        task_skill_matches[task.id] = match_team_members_for_task(task, team.members)
    
    # Assign tasks one by one
    for task in sorted_tasks:
        result = assign_task(
            task,
            sentences,
            team,
            existing_tasks=assigned_tasks,
            skill_matches=task_skill_matches[task.id]
        )
        
        # Apply assignment if confidence is acceptable
        if result.assigned_to and result.confidence >= 0.3:
            task.assigned_to = result.assigned_to
            assigned_tasks.append(task)
        
        results.append(result)
    
    return results


# --- 9. Validation and Conflict Resolution -----------------------------------

def validate_assignments(
    results: List[AssignmentResult],
    tasks: List[Task]
) -> Dict[str, List[str]]:
    """
    Validate assignments and identify issues.
    
    Returns:
        Dictionary with validation issues:
        {
            "unassigned": [task_ids],
            "low_confidence": [task_ids],
            "conflicts": [task_ids]
        }
    """
    issues = {
        "unassigned": [],
        "low_confidence": [],
        "conflicts": []
    }
    
    # Check for unassigned tasks
    for result in results:
        if not result.assigned_to:
            issues["unassigned"].append(result.task_id)
        elif result.confidence < 0.5:
            issues["low_confidence"].append(result.task_id)
    
    # Check for conflicts (same person assigned too many critical tasks)
    member_critical_count: Dict[str, int] = {}
    for task in tasks:
        if task.assigned_to and task.priority == "critical":
            member_critical_count[task.assigned_to] = member_critical_count.get(task.assigned_to, 0) + 1
            if member_critical_count[task.assigned_to] > 3:
                issues["conflicts"].append(task.id)
    
    return issues


def suggest_alternatives(
    result: AssignmentResult,
    team: Team
) -> List[str]:
    """
    Suggest alternative assignments for a task.
    """
    suggestions = []
    
    if result.alternative_assignments:
        for alt_name, alt_confidence in result.alternative_assignments:
            member = next((m for m in team.members if m.name == alt_name), None)
            if member:
                suggestions.append(
                    f"{alt_name} ({member.role}) - {alt_confidence:.0%} confidence"
                )
    
    return suggestions

