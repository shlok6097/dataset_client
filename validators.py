"""
Validators Module
Handles JSON response extraction, parsing, schema validation, and sanity checks
for educational datasets (questions, syllabus, concepts, flashcards, rubrics).
"""

import json
import re
from typing import Any, Dict, List, Union

def clean_json_response(raw_text: str) -> str:
    """
    Strips markdown code fences (```json ... ```) or finds the outer JSON object/array.
    """
    if not raw_text:
        return ""
    text = raw_text.strip()

    # Pattern 1: match markdown code blocks anywhere in text
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(fence_pattern, text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    else:
        # Pattern 2: locate between first { or [ and last } or ]
        first_curly = text.find("{")
        first_square = text.find("[")

        first_char_idx = -1
        if first_curly != -1 and first_square != -1:
            first_char_idx = min(first_curly, first_square)
        elif first_curly != -1:
            first_char_idx = first_curly
        elif first_square != -1:
            first_char_idx = first_square

        last_curly = text.rfind("}")
        last_square = text.rfind("]")
        last_char_idx = max(last_curly, last_square)

        if first_char_idx != -1 and last_char_idx != -1 and last_char_idx > first_char_idx:
            text = text[first_char_idx:last_char_idx + 1]

    return text.strip()

def parse_and_validate_json(raw_text: str) -> Union[Dict[str, Any], List[Any]]:
    """
    Cleans and parses raw JSON string into Python dict or list with fallback repairs:
    - Strips markdown code blocks
    - Strips illegal trailing commas before } or ]
    - Attempts bracket balance repair if truncated
    """
    cleaned = clean_json_response(raw_text)
    if not cleaned:
        raise ValueError("Empty or invalid JSON content")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Repair 1: Strip trailing commas (e.g. {"a": 1, })
    repaired = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Repair 2: Balance unclosed braces/brackets if truncated at max tokens
    open_curlies = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")
    if open_brackets > 0 or open_curlies > 0:
        patch = repaired.rstrip(", \n\t")
        if open_curlies > 0:
            patch += "}" * open_curlies
        if open_brackets > 0:
            patch += "]" * open_brackets
        try:
            return json.loads(patch)
        except json.JSONDecodeError:
            pass

    # If all repairs fail, raise informative error
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parsing error at char {e.pos}: {e.msg}") from e

def validate_questions(records: List[Dict[str, Any]]) -> List[str]:
    """
    Validates question records against the schema.
    Returns list of error messages (empty if all records are valid).
    """
    errors = []
    required_fields = [
        "board", "class", "subject", "chapter",
        "question_type", "marks_weightage", "difficulty",
        "seed_question", "answer_key"
    ]

    valid_types = {
        "MCQ", "Short_Answer", "Long_Answer", "Numerical", "Assertion_Reason", "Case_Based",
        "Fill_In_The_Blanks", "Match_The_Following"
    }
    type_aliases = {
        "fib": "Fill_In_The_Blanks",
        "fill_in_the_blank": "Fill_In_The_Blanks",
        "fill_in_the_blanks": "Fill_In_The_Blanks",
        "fill_in_blanks": "Fill_In_The_Blanks",
        "fill_in_blank": "Fill_In_The_Blanks",
        "matching": "Match_The_Following",
        "match": "Match_The_Following",
        "match_the_following": "Match_The_Following",
        "match_following": "Match_The_Following"
    }
    valid_difficulties = {"Easy", "Medium", "Hard"}

    for idx, r in enumerate(records, start=1):
        if not isinstance(r, dict):
            errors.append(f"Record {idx} is not a valid JSON dictionary")
            continue

        for field in required_fields:
            if field not in r or r[field] is None or (isinstance(r[field], str) and not r[field].strip()):
                errors.append(f"Record {idx}: Missing or empty required field '{field}'")

        q_type = r.get("question_type")
        normalized_type = None
        if q_type:
            # Check direct or alias match
            raw_key = str(q_type).strip().lower().replace("-", "_").replace(" ", "_")
            if raw_key in type_aliases:
                normalized_type = type_aliases[raw_key]
            else:
                for vt in valid_types:
                    if vt.lower() == raw_key:
                        normalized_type = vt
                        break

            if not normalized_type:
                errors.append(f"Record {idx}: Unknown question_type '{q_type}'")
            else:
                r["question_type"] = normalized_type

        # Type-specific validation
        eff_type = normalized_type or q_type
        if eff_type == "MCQ":
            options = r.get("options")
            if not isinstance(options, list) or len(options) < 2:
                errors.append(f"Record {idx}: MCQ question must have at least 2 options")
        elif eff_type == "Fill_In_The_Blanks":
            q_text = str(r.get("seed_question", ""))
            if "_" not in q_text and "[" not in q_text and "blank" not in q_text.lower():
                # Informative warning / note: recommended to have blank marker
                pass
        elif eff_type == "Match_The_Following":
            q_text = str(r.get("seed_question", ""))
            ans_text = str(r.get("answer_key", ""))
            if not ans_text:
                errors.append(f"Record {idx}: Match_The_Following must have non-empty answer_key with pairings")

        diff = r.get("difficulty")
        if diff and diff not in valid_difficulties:
            if diff.capitalize() not in valid_difficulties:
                errors.append(f"Record {idx}: Unknown difficulty level '{diff}'")

    return errors

def validate_syllabus(records: List[Dict[str, Any]]) -> List[str]:
    """
    Validates syllabus breakdown records.
    """
    errors = []
    required_fields = ["board", "class", "subject", "chapter", "subtopics", "learning_outcomes"]
    for idx, r in enumerate(records, start=1):
        if not isinstance(r, dict):
            errors.append(f"Record {idx} is not a dictionary")
            continue
        for field in required_fields:
            if field not in r:
                errors.append(f"Record {idx}: Missing field '{field}'")
    return errors

def validate_concepts(records: List[Dict[str, Any]]) -> List[str]:
    """
    Validates conceptual study notes records.
    """
    errors = []
    required_fields = ["board", "class", "subject", "chapter", "concept_title", "explanation"]
    for idx, r in enumerate(records, start=1):
        if not isinstance(r, dict):
            errors.append(f"Record {idx} is not a dictionary")
            continue
        for field in required_fields:
            if field not in r:
                errors.append(f"Record {idx}: Missing field '{field}'")
    return errors

def validate_flashcards(records: List[Dict[str, Any]]) -> List[str]:
    """
    Validates active-recall flashcard records.
    """
    errors = []
    required_fields = ["board", "class", "subject", "chapter", "front_prompt", "back_answer"]
    for idx, r in enumerate(records, start=1):
        if not isinstance(r, dict):
            errors.append(f"Record {idx} is not a dictionary")
            continue
        for field in required_fields:
            if field not in r:
                errors.append(f"Record {idx}: Missing field '{field}'")
    return errors

def validate_rubrics(records: List[Dict[str, Any]]) -> List[str]:
    """
    Validates marking rubric / scoring evaluation records.
    """
    errors = []
    required_fields = ["board", "class", "subject", "chapter", "criteria", "scoring_breakdown"]
    for idx, r in enumerate(records, start=1):
        if not isinstance(r, dict):
            errors.append(f"Record {idx} is not a dictionary")
            continue
        for field in required_fields:
            if field not in r:
                errors.append(f"Record {idx}: Missing field '{field}'")
    return errors

def validate_dataset_records(dataset_name: str, records: List[Dict[str, Any]]) -> List[str]:
    """
    Dispatches validation based on dataset name.
    """
    if dataset_name == "questions":
        return validate_questions(records)
    elif dataset_name == "syllabus":
        return validate_syllabus(records)
    elif dataset_name == "concepts":
        return validate_concepts(records)
    elif dataset_name == "flashcards":
        return validate_flashcards(records)
    elif dataset_name == "rubrics":
        return validate_rubrics(records)
    return []

