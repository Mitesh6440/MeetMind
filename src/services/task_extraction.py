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

# Vague references that need context from previous sentences
VAGUE_REFERENCES = [
    "this", "that", "these", "those", "it", "they",
    "this task", "that task", "this issue", "that issue",
    "this bug", "that bug", "this feature", "that feature",
]

# Words that indicate the sentence is incomplete without context
CONTEXT_NEEDED_INDICATORS = [
    "this", "that", "these", "those", "it", "they",
    "the above", "the mentioned", "the same", "the previous",
]

# Conversational words/phrases to remove from task descriptions
CONVERSATIONAL_PREFIXES = [
    "we need to", "we should", "we must", "we will", "we'll", "we have to",
    "i need to", "i should", "i must", "i will", "i'll", "i have to",
    "you need to", "you should", "you must", "you will", "you'll", "you have to",
    "let's", "lets", "can you", "will you", "could you", "would you",
    "please", "kindly", "make sure to", "ensure that", "make sure",
    "need to", "have to", "going to", "gonna", "plan to",
    "will need", "would need", "might need",
]

# Pronouns and filler words to remove
FILLER_WORDS = [
    "we", "i", "you", "they", "this", "that", "these", "those", "it",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
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
    - Rejects sentences that are too vague (just "this should be done")
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

    # Rule 0.5: Reject sentences that start with vague reference and have no clear action
    first_word = words[0] if words else ""
    if first_word in VAGUE_REFERENCES:
        # Check if there's an action verb in the sentence
        has_action_verb = any(verb in cleaned for verb in ACTION_VERBS)
        # Check if sentence is just a vague reference + deadline/time
        vague_time_only = re.match(
            r"^(this|that|it|these|those)\s+(should|must|will|need|has to|is|are)\s+(be\s+)?(done|completed|finished|ready)",
            cleaned
        )
        if not has_action_verb or vague_time_only:
            # Too vague - reject unless we can find context later
            return False

    # Rule 1: starts with an action verb ("fix the bug", "update the UI")
    first_two = " ".join(words[:2]) if len(words) >= 2 else ""
    
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
            
            # Skip if text after phrase starts with vague reference
            if text_after_phrase.split()[0] in VAGUE_REFERENCES:
                continue
            
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
                # But reject if it's just vague reference
                if text_after_phrase.split()[0] not in VAGUE_REFERENCES:
                    return True

    # Rule 3: Question-style assignments ("Can you ...", "Will you ...")
    question_patterns = [
        r"^(can|will|could|would)\s+you\s+",
        r"^(please|kindly)\s+",
    ]
    for pattern in question_patterns:
        if re.match(pattern, cleaned):
            # Check that it's not just "can you do this"
            if not re.match(r"^(can|will|could|would)\s+you\s+(do|handle|work on)\s+(this|that|it)", cleaned):
                return True

    # Rule 4: "Let's ..." or "We should ..." style
    if cleaned.startswith(("let's ", "lets ", "we should ", "we need ", "we must ")):
        # Check that it's not just "we should do this"
        if not re.match(r"^(let's|lets|we should|we need|we must)\s+(do|handle|work on)\s+(this|that|it)", cleaned):
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


def find_context_for_vague_reference(
    sentence: PreprocessedSentence,
    sentences: List[PreprocessedSentence],
    max_lookback: int = 5
) -> str:
    """
    When a sentence contains vague references (this, that, it), 
    look back at previous sentences to find what it refers to.
    
    Returns:
        Enhanced description with context, or original if no context found.
    """
    cleaned = normalize_text(sentence.cleaned_text)
    words = cleaned.split()
    
    # Check if sentence starts with vague reference
    first_word = words[0] if words else ""
    if first_word not in VAGUE_REFERENCES:
        return sentence.cleaned_text.strip()
    
    # Look back at previous sentences
    sentence_idx = next((i for i, s in enumerate(sentences) if s.id == sentence.id), -1)
    if sentence_idx < 0:
        return sentence.cleaned_text.strip()
    
    # Look back up to max_lookback sentences
    start_idx = max(0, sentence_idx - max_lookback)
    
    # Search for action verbs or task-related content in previous sentences
    best_match = None
    best_score = 0
    
    for i in range(sentence_idx - 1, start_idx - 1, -1):
        if i < 0:
            break
        prev_sentence = sentences[i]
        prev_cleaned = normalize_text(prev_sentence.cleaned_text)
        prev_words = prev_cleaned.split()
        
        # Skip if previous sentence is too short
        if len(prev_words) < 3:
            continue
        
        # Check if previous sentence contains action verbs
        has_action = False
        action_verb = None
        for verb in ACTION_VERBS:
            if verb in prev_cleaned:
                has_action = True
                action_verb = verb
                break
        
        # Score this potential match
        score = 0
        if has_action:
            score += 10
        if any(phrase in prev_cleaned for phrase in ACTION_PHRASES):
            score += 5
        # Prefer sentences that are task-like
        if is_task_sentence(prev_sentence):
            score += 15
        
        if score > best_score:
            best_score = score
            best_match = (prev_sentence, prev_cleaned, action_verb)
    
    if best_match and best_score >= 10:
        prev_sentence, prev_cleaned, action_verb = best_match
        
        # Extract the main action from previous sentence
        if action_verb:
            verb_idx = prev_cleaned.find(action_verb)
            # Get text from verb onwards (up to 20 words)
            after_verb = prev_cleaned[verb_idx:].split()[:20]
            action_part = " ".join(after_verb)
            
            # Remove vague references from action_part if present
            action_words = action_part.split()
            # Remove leading vague references
            while action_words and action_words[0] in VAGUE_REFERENCES:
                action_words = action_words[1:]
            action_part = " ".join(action_words)
            
            if action_part:
                # Replace vague reference with the action from previous sentence
                remaining_words = words[1:]  # Skip first word (vague reference)
                # Also skip common connecting words
                while remaining_words and remaining_words[0] in ["should", "must", "will", "need", "has", "to", "be"]:
                    remaining_words = remaining_words[1:]
                remaining_text = " ".join(remaining_words)
                
                # Combine: action from previous + remaining from current
                if remaining_text:
                    enhanced = f"{action_part} {remaining_text}".strip()
                else:
                    enhanced = action_part.strip()
                
                # Clean up any duplicate words at the boundary
                enhanced_words = enhanced.split()
                cleaned_enhanced = []
                prev_word = ""
                for word in enhanced_words:
                    if word != prev_word or word not in VAGUE_REFERENCES:
                        cleaned_enhanced.append(word)
                    prev_word = word
                
                return " ".join(cleaned_enhanced).strip()
    
    # If no context found, return original
    return sentence.cleaned_text.strip()


def extract_core_task(description: str) -> str:
    """
    Extract only the core actionable task from a sentence description.
    Removes conversational elements, pronouns, and filler words.
    
    Examples:
    - "We need to fix the login bug by tomorrow" -> "fix the login bug by tomorrow"
    - "Can you update the API documentation?" -> "update the API documentation"
    - "This should be done by Friday" -> "done by Friday" (if no context found)
    """
    desc_norm = normalize_text(description)
    words = desc_norm.split()
    
    if not words:
        return description.strip()
    
    # Find the first action verb
    action_verb_idx = -1
    for i, word in enumerate(words):
        # Check for single-word action verbs
        if word in ACTION_VERBS:
            action_verb_idx = i
            break
        # Check for multi-word action verbs
        if i < len(words) - 1:
            two_word_verb = f"{word} {words[i+1]}"
            if two_word_verb in ACTION_VERBS:
                action_verb_idx = i
                break
    
    # If action verb found, start from there
    if action_verb_idx >= 0:
        # Get everything from the action verb onwards
        core_words = words[action_verb_idx:]
    else:
        # No action verb found, try removing conversational prefixes
        core_words = words
        for prefix in CONVERSATIONAL_PREFIXES:
            prefix_words = prefix.split()
            if len(core_words) >= len(prefix_words):
                if " ".join(core_words[:len(prefix_words)]) == prefix:
                    core_words = core_words[len(prefix_words):]
                    break
    
    # Remove leading filler words
    while core_words and core_words[0] in FILLER_WORDS:
        core_words = core_words[1:]
    
    # Remove conversational prefixes that might still be there
    result = " ".join(core_words)
    for prefix in CONVERSATIONAL_PREFIXES:
        if result.startswith(prefix + " "):
            result = result[len(prefix):].strip()
            break
    
    # Clean up: remove leading "to" if it's just "to <verb>"
    if result.startswith("to "):
        result = result[3:].strip()
    
    # Remove leading "that" or "which"
    if result.startswith(("that ", "which ")):
        result = result.split(" ", 1)[1] if " " in result else result
    
    # Capitalize first letter for readability
    if result:
        result = result[0].upper() + result[1:] if len(result) > 1 else result.upper()
    
    return result.strip() if result.strip() else description.strip()


def is_too_vague(description: str) -> bool:
    """
    Check if a task description is too vague to be useful.
    Rejects descriptions that are mostly vague references without action.
    """
    desc_norm = normalize_text(description)
    words = desc_norm.split()
    
    if len(words) < 3:
        return True
    
    # Check if description starts with vague reference and has no clear action
    first_word = words[0] if words else ""
    if first_word in VAGUE_REFERENCES:
        # Check if there's an action verb in the description
        has_action = any(verb in desc_norm for verb in ACTION_VERBS)
        if not has_action:
            return True
        
        # Check if description is too short after removing vague reference
        remaining = " ".join(words[1:])
        if len(remaining.split()) < 3:
            return True
    
    # Check if description is just a vague reference with time/deadline
    vague_time_patterns = [
        r"^(this|that|it|these|those)\s+(should|must|will|need|has to)",
        r"^(this|that|it|these|those)\s+(is|are|was|were)",
    ]
    for pattern in vague_time_patterns:
        if re.match(pattern, desc_norm):
            # Check if there's substantial content beyond the vague reference
            if len(words) < 5:
                return True
    
    return False


def extract_tasks_from_sentences(
    sentences: List[PreprocessedSentence],
    starting_id: int = 1,
) -> List[Task]:
    """
    Iterate over preprocessed sentences and extract Task objects
    for those that look like action items.
    
    Enhanced to handle vague references by looking back at context.

    Returns:
        List of Task objects with:
        - id
        - description (enhanced with context if needed)
        - source_sentence_id
    """
    tasks: List[Task] = []
    current_id = starting_id

    for s in sentences:
        if not is_task_sentence(s):
            continue

        # Get base description
        description = s.cleaned_text.strip()
        if not description:
            continue
        
        # Check if description contains vague references
        desc_norm = normalize_text(description)
        has_vague_ref = any(ref in desc_norm.split()[:3] for ref in VAGUE_REFERENCES)
        
        if has_vague_ref:
            # Try to find context from previous sentences
            enhanced_description = find_context_for_vague_reference(s, sentences)
            description = enhanced_description
        
        # Reject if still too vague
        if is_too_vague(description):
            continue
        
        # Extract only the core task (remove conversational elements)
        core_task = extract_core_task(description)
        
        # Final check: ensure we have a meaningful task
        if len(core_task.split()) < 2:
            continue

        task = Task(
            id=current_id,
            description=core_task,  # Core task for UI display
            source_sentence_id=s.id,
            source_sentence_text=description,  # Full sentence for processing (before core extraction)
        )
        tasks.append(task)
        current_id += 1

    return tasks
