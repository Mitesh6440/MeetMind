from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List
import re
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

from models.task import Task
from models.nlp import PreprocessedSentence
from ..utils.text_utils import normalize_text as _norm


class DeadlineExtractionError(Exception):
    """Custom exception for deadline extraction errors."""
    pass


# --- 1. Enhanced temporal expression patterns ---------------------------------

# Relative time expressions that indicate deadlines
DEADLINE_KEYWORDS = [
    "by", "before", "until", "due", "deadline", "on", "at"
]

# Relative time phrases
RELATIVE_DEADLINE_PATTERNS = [
    r"by\s+(today|tonight)",
    r"by\s+(tomorrow|tomorrow\s+night)",
    r"by\s+(day\s+after\s+tomorrow)",
    r"by\s+(this\s+(morning|afternoon|evening|week|month|quarter))",
    r"by\s+(next\s+(week|month|quarter|monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
    r"by\s+(end\s+of\s+(day|week|month|quarter))",
    r"by\s+eod",  # End of day
    r"by\s+eow",  # End of week
    r"by\s+eom",  # End of month
    r"before\s+(today|tomorrow|next\s+week)",
    r"due\s+(today|tomorrow|next\s+week)",
    r"deadline\s+(is\s+)?(today|tomorrow|next\s+week)",
]

# Absolute date patterns
ABSOLUTE_DATE_PATTERNS = [
    r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b",  # MM/DD/YYYY or DD/MM/YYYY
    r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{2,4})\b",
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{2,4})\b",
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{2,4})\b",
]

# Weekday names
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12
}


# --- 2. Parse relative dates to absolute dates -------------------------------


def parse_relative_date(expression: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
    """
    Convert relative date expressions to absolute datetime.
    
    Examples:
    - "tomorrow" -> datetime for tomorrow
    - "next week" -> datetime for next week
    - "end of week" -> datetime for end of current week (Friday 23:59:59)
    - "by Friday" -> datetime for next Friday
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    expr_norm = _norm(expression)
    
    # Today / Tonight
    if expr_norm in ["today", "tonight"]:
        return reference_date.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Tomorrow
    if expr_norm == "tomorrow":
        tomorrow = reference_date + timedelta(days=1)
        return tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)
    
    if expr_norm == "tomorrow night":
        tomorrow = reference_date + timedelta(days=1)
        return tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Day after tomorrow
    if expr_norm == "day after tomorrow":
        day_after = reference_date + timedelta(days=2)
        return day_after.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # This morning/afternoon/evening
    if expr_norm == "this morning":
        return reference_date.replace(hour=12, minute=0, second=0, microsecond=0)
    if expr_norm == "this afternoon":
        return reference_date.replace(hour=17, minute=0, second=0, microsecond=0)
    if expr_norm == "this evening":
        return reference_date.replace(hour=20, minute=0, second=0, microsecond=0)
    
    # End of day (EOD)
    if expr_norm in ["eod", "end of day"]:
        return reference_date.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # This week (end of current week - Friday)
    if expr_norm == "this week":
        days_until_friday = (4 - reference_date.weekday()) % 7
        if days_until_friday == 0:
            # If it's Friday, use end of today
            return reference_date.replace(hour=23, minute=59, second=59, microsecond=0)
        friday = reference_date + timedelta(days=days_until_friday)
        return friday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # End of week (EOW)
    if expr_norm in ["eow", "end of week", "end of the week"]:
        days_until_friday = (4 - reference_date.weekday()) % 7
        if days_until_friday == 0:
            # If it's Friday, use end of today
            return reference_date.replace(hour=23, minute=59, second=59, microsecond=0)
        friday = reference_date + timedelta(days=days_until_friday)
        return friday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Next week
    if expr_norm == "next week":
        days_until_next_monday = (7 - reference_date.weekday()) % 7
        if days_until_next_monday == 0:
            days_until_next_monday = 7
        next_monday = reference_date + timedelta(days=days_until_next_monday)
        return next_monday.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # This month (end of current month)
    if expr_norm == "this month":
        next_month = reference_date.replace(day=1) + relativedelta(months=1)
        end_of_month = next_month - timedelta(days=1)
        return end_of_month.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # End of month (EOM)
    if expr_norm in ["eom", "end of month"]:
        next_month = reference_date.replace(day=1) + relativedelta(months=1)
        end_of_month = next_month - timedelta(days=1)
        return end_of_month.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Next month
    if expr_norm == "next month":
        next_month = reference_date.replace(day=1) + relativedelta(months=1)
        end_of_next_month = (next_month + relativedelta(months=1)) - timedelta(days=1)
        return end_of_next_month.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Next quarter
    if expr_norm == "next quarter":
        current_quarter = (reference_date.month - 1) // 3
        next_quarter_month = (current_quarter + 1) * 3 + 1
        if next_quarter_month > 12:
            next_quarter_month = 1
            year = reference_date.year + 1
        else:
            year = reference_date.year
        quarter_start = datetime(year, next_quarter_month, 1)
        quarter_end = (quarter_start + relativedelta(months=3)) - timedelta(days=1)
        return quarter_end.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Weekday matching (e.g., "next Friday", "by Monday")
    for weekday_name, weekday_num in WEEKDAYS.items():
        if weekday_name in expr_norm:
            days_ahead = (weekday_num - reference_date.weekday()) % 7
            if days_ahead == 0:
                # If it's the same day, check if "next" is mentioned
                if "next" in expr_norm:
                    days_ahead = 7
                else:
                    # Same day, use end of day
                    return reference_date.replace(hour=23, minute=59, second=59, microsecond=0)
            elif "next" in expr_norm and days_ahead < 7:
                days_ahead += 7
            
            target_date = reference_date + timedelta(days=days_ahead)
            return target_date.replace(hour=23, minute=59, second=59, microsecond=0)
    
    return None


# --- 3. Parse absolute dates --------------------------------------------------


def parse_absolute_date(date_str: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
    """
    Parse absolute date strings in various formats.
    
    Supports:
    - MM/DD/YYYY or DD/MM/YYYY
    - "January 15, 2024"
    - "15 January 2024"
    - "15th January 2024"
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    date_str_clean = date_str.strip()
    
    # Try dateutil parser first (handles many formats)
    try:
        parsed = date_parser.parse(date_str_clean, default=reference_date)
        # Set to end of day if no time specified
        if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
            parsed = parsed.replace(hour=23, minute=59, second=59)
        return parsed
    except (ValueError, TypeError):
        pass
    
    # Try MM/DD/YYYY or DD/MM/YYYY
    match = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", date_str_clean)
    if match:
        part1, part2, part3 = match.groups()
        year = int(part3)
        if year < 100:
            year += 2000 if year < 50 else 1900
        
        # Try MM/DD/YYYY first (US format)
        try:
            month, day = int(part1), int(part2)
            if 1 <= month <= 12 and 1 <= day <= 31:
                return datetime(year, month, day, 23, 59, 59)
        except (ValueError, TypeError):
            pass
        
        # Try DD/MM/YYYY (European format)
        try:
            day, month = int(part1), int(part2)
            if 1 <= month <= 12 and 1 <= day <= 31:
                return datetime(year, month, day, 23, 59, 59)
        except (ValueError, TypeError):
            pass
    
    # Try "Month Day, Year" or "Day Month Year"
    month_match = None
    for month_name, month_num in MONTHS.items():
        if month_name in date_str_clean.lower():
            month_match = (month_name, month_num)
            break
    
    if month_match:
        # Extract day and year
        day_match = re.search(r"(\d{1,2})(?:st|nd|rd|th)?", date_str_clean)
        year_match = re.search(r"(\d{4})", date_str_clean)
        
        if day_match and year_match:
            day = int(day_match.group(1))
            year = int(year_match.group(1))
            month_num = month_match[1]
            
            try:
                return datetime(year, month_num, day, 23, 59, 59)
            except (ValueError, TypeError):
                pass
    
    return None


# --- 4. Extract deadline from sentence ----------------------------------------


def extract_deadline_from_sentence(
    sentence: PreprocessedSentence,
    reference_date: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Extract deadline from a sentence by looking for temporal expressions.
    
    Returns the earliest deadline found, or None if no deadline is detected.
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    text = sentence.cleaned_text
    text_norm = _norm(text)
    
    deadlines: List[datetime] = []
    
    # 1. Look for absolute dates
    for pattern in ABSOLUTE_DATE_PATTERNS:
        matches = re.finditer(pattern, text_norm)
        for match in matches:
            date_str = match.group(0)
            parsed_date = parse_absolute_date(date_str, reference_date)
            if parsed_date:
                deadlines.append(parsed_date)
    
    # 2. Look for relative deadline patterns
    for pattern in RELATIVE_DEADLINE_PATTERNS:
        matches = re.finditer(pattern, text_norm)
        for match in matches:
            # Extract the time expression part
            full_match = match.group(0)
            # Remove "by", "before", etc. to get the actual time expression
            time_expr = re.sub(r"^(by|before|due|deadline\s+is?\s*)", "", full_match).strip()
            parsed_date = parse_relative_date(time_expr, reference_date)
            if parsed_date:
                deadlines.append(parsed_date)
    
    # 3. Look for standalone relative expressions
    for keyword in ["tomorrow", "today", "next week", "end of week", "end of month"]:
        if keyword in text_norm:
            # Check if it's part of a deadline phrase
            if any(kw in text_norm for kw in DEADLINE_KEYWORDS):
                parsed_date = parse_relative_date(keyword, reference_date)
                if parsed_date:
                    deadlines.append(parsed_date)
    
    # 4. Look for weekday mentions with deadline keywords
    for weekday in WEEKDAYS.keys():
        if weekday in text_norm:
            # Check if preceded by deadline keyword
            pattern = rf"\b(by|before|on|due)\s+{weekday}\b"
            if re.search(pattern, text_norm):
                parsed_date = parse_relative_date(weekday, reference_date)
                if parsed_date:
                    deadlines.append(parsed_date)
    
    # Return the earliest deadline (most urgent)
    if deadlines:
        return min(deadlines)
    
    return None


# --- 5. Enrich tasks with deadlines -------------------------------------------


def enrich_tasks_with_deadlines(
    tasks: List[Task],
    sentences: List[PreprocessedSentence],
    reference_date: Optional[datetime] = None
) -> List[Task]:
    """
    Extract deadlines from task sentences and assign them to tasks.
    
    For each task, looks at its source sentence and extracts any deadline.
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    # Create lookup from sentence id -> sentence
    sentence_map = {s.id: s for s in sentences}
    
    for task in tasks:
        if task.source_sentence_id is None:
            continue
        
        sent = sentence_map.get(task.source_sentence_id)
        if not sent:
            continue
        
        deadline = extract_deadline_from_sentence(sent, reference_date)
        if deadline:
            task.deadline = deadline
    
    return tasks

