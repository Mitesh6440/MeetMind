from __future__ import annotations

from typing import List, Optional, Dict, Set
import re
from dataclasses import dataclass

from models.task import Task
from models.nlp import PreprocessedSentence


class DependencyError(Exception):
    """Custom exception for dependency extraction errors."""
    pass


def _norm(text: str) -> str:
    """Normalize text for matching."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


# --- 1. Dependency Keywords and Patterns --------------------------------------

# Keywords that indicate dependencies
DEPENDENCY_KEYWORDS = [
    "depends on",
    "dependent on",
    "requires",
    "needs",
    "after",
    "before",
    "first",
    "then",
    "once",
    "when",
    "following",
    "subsequent",
    "prerequisite",
    "blocked by",
    "blocking",
    "waiting for",
    "waiting on",
]

# Patterns for dependency expressions
DEPENDENCY_PATTERNS = [
    r"depends?\s+on\s+([^,\.]+)",
    r"dependent\s+on\s+([^,\.]+)",
    r"requires?\s+([^,\.]+)",
    r"needs?\s+([^,\.]+)",
    r"after\s+([^,\.]+)",
    r"before\s+([^,\.]+)",
    r"first\s+([^,\.]+)",
    r"then\s+([^,\.]+)",
    r"once\s+([^,\.]+)",
    r"when\s+([^,\.]+)",
    r"following\s+([^,\.]+)",
    r"blocked\s+by\s+([^,\.]+)",
    r"waiting\s+(?:for|on)\s+([^,\.]+)",
]

# Task reference patterns (e.g., "task 1", "the login fix", "API update")
TASK_REFERENCE_PATTERNS = [
    r"task\s+(\d+)",
    r"issue\s+(\d+)",
    r"ticket\s+(\d+)",
    r"bug\s+(\d+)",
    r"the\s+([a-z\s]+?)(?:\s+task|\s+fix|\s+update|\s+feature|\s+bug)",
    r"([a-z\s]+?)\s+task",
    r"([a-z\s]+?)\s+fix",
    r"([a-z\s]+?)\s+update",
]


# --- 2. Dependency Graph Structure --------------------------------------------

@dataclass
class DependencyEdge:
    """Represents a dependency relationship between tasks."""
    from_task_id: int
    to_task_id: int
    dependency_type: str  # "depends_on", "blocks", "prerequisite", etc.
    description: Optional[str] = None


class DependencyGraph:
    """
    Represents the dependency graph of tasks.
    """
    
    def __init__(self):
        self.edges: List[DependencyEdge] = []
        self.task_dependencies: Dict[int, List[int]] = {}  # task_id -> [dependent_task_ids]
        self.task_dependents: Dict[int, List[int]] = {}    # task_id -> [prerequisite_task_ids]
    
    def add_edge(self, edge: DependencyEdge):
        """Add a dependency edge to the graph."""
        self.edges.append(edge)
        
        # Update dependency maps
        if edge.from_task_id not in self.task_dependencies:
            self.task_dependencies[edge.from_task_id] = []
        if edge.to_task_id not in self.task_dependencies[edge.from_task_id]:
            self.task_dependencies[edge.from_task_id].append(edge.to_task_id)
        
        if edge.to_task_id not in self.task_dependents:
            self.task_dependents[edge.to_task_id] = []
        if edge.to_task_id not in self.task_dependents[edge.to_task_id]:
            self.task_dependents[edge.to_task_id].append(edge.from_task_id)
    
    def get_dependencies(self, task_id: int) -> List[int]:
        """Get all tasks that this task depends on."""
        return self.task_dependencies.get(task_id, [])
    
    def get_dependents(self, task_id: int) -> List[int]:
        """Get all tasks that depend on this task."""
        return self.task_dependents.get(task_id, [])
    
    def has_cycles(self) -> bool:
        """Check if the dependency graph has cycles."""
        visited: Set[int] = set()
        rec_stack: Set[int] = set()
        
        def has_cycle(node: int) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.task_dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in self.task_dependencies.keys():
            if task_id not in visited:
                if has_cycle(task_id):
                    return True
        
        return False
    
    def topological_sort(self) -> List[int]:
        """
        Perform topological sort to get execution order.
        Returns list of task IDs in order of execution.
        """
        in_degree: Dict[int, int] = {}
        
        # Initialize in-degree for all tasks
        for task_id in set(self.task_dependencies.keys()) | set(self.task_dependents.keys()):
            in_degree[task_id] = 0
        
        # Calculate in-degrees
        for edge in self.edges:
            in_degree[edge.to_task_id] = in_degree.get(edge.to_task_id, 0) + 1
        
        # Find tasks with no dependencies
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            task_id = queue.pop(0)
            result.append(task_id)
            
            # Reduce in-degree for dependent tasks
            for dependent_id in self.task_dependencies.get(task_id, []):
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        return result


# --- 3. Extract Task References from Text -------------------------------------


def extract_task_references(text: str, tasks: List[Task]) -> List[int]:
    """
    Extract task IDs that are referenced in the text.
    Uses fuzzy matching to find tasks by description keywords.
    """
    text_norm = _norm(text)
    referenced_task_ids: List[int] = []
    
    # 1. Look for explicit task numbers (e.g., "task 1", "issue 2")
    for pattern in TASK_REFERENCE_PATTERNS:
        matches = re.finditer(pattern, text_norm)
        for match in matches:
            # Try to match by number
            if match.group(1).isdigit():
                task_num = int(match.group(1))
                # Find task with matching ID
                for task in tasks:
                    if task.id == task_num:
                        if task.id not in referenced_task_ids:
                            referenced_task_ids.append(task.id)
            else:
                # Try to match by description keywords
                keywords = match.group(1).strip().split()
                for task in tasks:
                    task_desc_norm = _norm(task.description)
                    # Check if keywords appear in task description
                    if all(kw in task_desc_norm for kw in keywords if len(kw) > 2):
                        if task.id not in referenced_task_ids:
                            referenced_task_ids.append(task.id)
    
    # 2. Fuzzy matching: look for task descriptions in text
    for task in tasks:
        task_desc_norm = _norm(task.description)
        # Extract key words from task description (skip common words)
        task_keywords = [w for w in task_desc_norm.split() if len(w) > 3]
        if len(task_keywords) >= 2:
            # Check if at least 2 keywords appear in the text
            matches = sum(1 for kw in task_keywords[:3] if kw in text_norm)
            if matches >= 2:
                if task.id not in referenced_task_ids:
                    referenced_task_ids.append(task.id)
    
    return referenced_task_ids


# --- 4. Extract Dependencies from Sentence ------------------------------------


def extract_dependencies_from_sentence(
    sentence: PreprocessedSentence,
    all_tasks: List[Task],
    current_task: Task
) -> List[int]:
    """
    Extract task IDs that the current task depends on from the sentence.
    """
    text = sentence.cleaned_text
    text_norm = _norm(text)
    
    # Check if sentence contains dependency keywords
    has_dependency_keyword = any(kw in text_norm for kw in DEPENDENCY_KEYWORDS)
    if not has_dependency_keyword:
        return []
    
    # Extract task references from the sentence
    referenced_tasks = extract_task_references(text, all_tasks)
    
    # Filter out self-reference
    referenced_tasks = [tid for tid in referenced_tasks if tid != current_task.id]
    
    return referenced_tasks


# --- 5. Build Dependency Graph ------------------------------------------------


def build_dependency_graph(
    tasks: List[Task],
    sentences: List[PreprocessedSentence]
) -> DependencyGraph:
    """
    Build a dependency graph from tasks and their source sentences.
    """
    graph = DependencyGraph()
    sentence_map = {s.id: s for s in sentences}
    
    for task in tasks:
        if task.source_sentence_id is None:
            continue
        
        sent = sentence_map.get(task.source_sentence_id)
        if not sent:
            continue
        
        # Extract dependencies from the sentence
        dependencies = extract_dependencies_from_sentence(sent, tasks, task)
        
        # Add edges to graph
        for dep_task_id in dependencies:
            edge = DependencyEdge(
                from_task_id=task.id,
                to_task_id=dep_task_id,
                dependency_type="depends_on",
                description=f"Task {task.id} depends on task {dep_task_id}"
            )
            graph.add_edge(edge)
    
    return graph


# --- 6. Enrich Tasks with Dependencies ----------------------------------------


def enrich_tasks_with_dependencies(
    tasks: List[Task],
    sentences: List[PreprocessedSentence]
) -> tuple[List[Task], DependencyGraph]:
    """
    Extract dependencies from task sentences and build a dependency graph.
    
    Returns:
        - Updated tasks with dependencies field populated
        - Dependency graph for analysis
    """
    # Build dependency graph
    graph = build_dependency_graph(tasks, sentences)
    
    # Update tasks with their dependencies
    for task in tasks:
        dependencies = graph.get_dependencies(task.id)
        task.dependencies = dependencies
    
    return tasks, graph

