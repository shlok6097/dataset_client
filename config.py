"""
Pipeline Configuration Module
Loads configuration from .env and defines curriculum targets and dataset categories.
"""

import os
from typing import Dict, List, Any
from dotenv import dotenv_values, load_dotenv

load_dotenv()
env_vals = dotenv_values(".env")

CONFIG: Dict[str, Any] = {
    "api_base_url": os.getenv("GEMINI_WEB2API_BASE_URL", env_vals.get("GEMINI_WEB2API_BASE_URL", "http://127.0.0.1:8081/v1")),
    "model": os.getenv("GEMINI_MODEL", env_vals.get("GEMINI_MODEL", "gemini-3.7-flash")),
    "api_key": os.getenv("GEMINI_WEB2API_KEY", env_vals.get("GEMINI_WEB2API_KEY", "")),
    "mode": os.getenv("EXECUTION_MODE", "resume"),
    "output_dir": os.getenv("OUTPUT_DIR", env_vals.get("OUTPUT_DIR", "output_datasets_11_12")),
    "checkpoint_name": os.getenv("CHECKPOINT_NAME", "checkpoint.json"),
    "manifest_name": os.getenv("MANIFEST_NAME", "manifest.json"),
    "sqlite_db_name": os.getenv("SQLITE_DB_NAME", "tasks.db"),
    "batches_per_category": int(os.getenv("BATCHES_PER_CATEGORY", env_vals.get("BATCHES_PER_CATEGORY", "2"))),
    "records_per_batch": int(os.getenv("RECORDS_PER_BATCH", env_vals.get("RECORDS_PER_BATCH", "5"))),
    "temperature": float(os.getenv("TEMPERATURE", env_vals.get("TEMPERATURE", "0.2"))),
    "max_api_retries": int(os.getenv("MAX_API_RETRIES", env_vals.get("MAX_API_RETRIES", "5"))),
    "max_json_attempts": int(os.getenv("MAX_JSON_ATTEMPTS", env_vals.get("MAX_JSON_ATTEMPTS", "3"))),
    "request_delay_sec": float(os.getenv("REQUEST_DELAY_SEC", env_vals.get("REQUEST_DELAY_SEC", "0.8"))),
    "timeout_sec": int(os.getenv("TIMEOUT_SEC", env_vals.get("TIMEOUT_SEC", "120"))),
    "save_after_every_chapter": str(os.getenv("SAVE_AFTER_EVERY_CHAPTER", env_vals.get("SAVE_AFTER_EVERY_CHAPTER", "True"))).lower() == "true",
    "test_mode": str(os.getenv("TEST_MODE", env_vals.get("TEST_MODE", "False"))).lower() == "true",
    "allow_synthetic": str(os.getenv("ALLOW_SYNTHETIC", env_vals.get("ALLOW_SYNTHETIC", "False"))).lower() == "true",
    "workers": int(os.getenv("WORKERS", env_vals.get("WORKERS", "3"))),
    "curriculum_json_path": os.getenv("CURRICULUM_JSON_PATH", env_vals.get("CURRICULUM_JSON_PATH", "class_11_12_karnataka_cbse_isc_curriculum_v2026.2.json")),
    "questions_per_type": int(os.getenv("QUESTIONS_PER_TYPE", env_vals.get("QUESTIONS_PER_TYPE", "10"))),
    "summary_topics_count": int(os.getenv("SUMMARY_TOPICS_COUNT", env_vals.get("SUMMARY_TOPICS_COUNT", "10"))),
    "flashcards_topics_count": int(os.getenv("FLASHCARDS_TOPICS_COUNT", env_vals.get("FLASHCARDS_TOPICS_COUNT", "10"))),
    "google_drive_folder": os.getenv("GOOGLE_DRIVE_FOLDER_NAME", env_vals.get("GOOGLE_DRIVE_FOLDER_NAME", "ExamApp_Datasets")),
    "google_credentials_file": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", env_vals.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")),
    "google_token_file": os.getenv("GOOGLE_TOKEN_FILE", env_vals.get("GOOGLE_TOKEN_FILE", "token.json")),
}

DATASET_NAMES: List[str] = [
    "questions",
    "syllabus",
    "concepts",
    "flashcards",
    "rubrics"
]

QUESTION_TYPES: List[str] = [
    "MCQ",
    "Fill_In_The_Blanks",
    "Match_The_Following",
    "Assertion_Reason",
    "Short_Answer",
    "Long_Answer",
    "Numerical",
    "Case_Based"
]

DATASET_FILENAMES: Dict[str, str] = {
    name: f"{name}.jsonl" for name in DATASET_NAMES
}

# Configured high-level Board / Class targets for selective or global generation
CURRICULUM_TARGETS: List[Dict[str, Any]] = [
    {
        "board": "CBSE",
        "academic_year": "2026-27",
        "class": "Class_12",
        "subjects": [
            "Physics", "Chemistry", "Mathematics", "Biology", "Computer Science (Python)",
            "Accountancy", "Business Studies", "Economics", "Geography", "Psychology",
            "English Core", "History (NCERT)", "Political Science (NCERT)", "Sociology (NCERT)",
            "Informatics Practices", "Applied Mathematics", "Physical Education"
        ]
    },
    {
        "board": "CBSE",
        "academic_year": "2026-27",
        "class": "Class_11",
        "subjects": [
            "Physics", "Chemistry", "Mathematics", "Biology", "Computer Science (Python)",
            "Accountancy", "Business Studies", "Economics", "Geography", "Psychology",
            "English Core", "History (NCERT)", "Political Science (NCERT)", "Sociology (NCERT)",
            "Informatics Practices", "Applied Mathematics", "Physical Education"
        ]
    },
    {
        "board": "KARNATAKA_PUC",
        "academic_year": "2026-27",
        "class": "Class_12",
        "class_display": "2nd PUC",
        "subjects": [
            "Physics", "Chemistry", "Mathematics", "Biology", "Computer Science (Python)",
            "Accountancy", "Business Studies", "Economics", "Geography", "Psychology",
            "English", "Kannada (Sahitya Sanchalana)", "Electronics", "Statistics",
            "Basic Mathematics", "History (State Syllabus)", "Political Science (State Syllabus)", "Sociology (State Syllabus)"
        ]
    },
    {
        "board": "KARNATAKA_PUC",
        "academic_year": "2026-27",
        "class": "Class_11",
        "class_display": "1st PUC",
        "subjects": [
            "Physics", "Chemistry", "Mathematics", "Biology", "Computer Science (Python)",
            "Accountancy", "Business Studies", "Economics", "Geography", "Psychology",
            "English", "Kannada (Sahitya Sanchalana)", "Electronics", "Statistics",
            "Basic Mathematics", "History (State Syllabus)", "Political Science (State Syllabus)", "Sociology (State Syllabus)"
        ]
    },
    {
        "board": "CISCE_ISC",
        "academic_year": "2026-27",
        "class": "Class_12",
        "subjects": [
            "English-II Literature (Macbeth, Prism, Rhapsody)", "Computer Science (Java)",
            "Commerce", "Business Studies", "History", "Political Science", "Chemistry"
        ]
    },
    {
        "board": "CISCE_ISC",
        "academic_year": "2026-27",
        "class": "Class_11",
        "subjects": [
            "English-II Literature (Macbeth, Prism, Rhapsody)", "Computer Science (Java)",
            "Commerce", "Business Studies", "History", "Political Science", "Physics"
        ]
    },
    {
        "board": "CBSE",
        "academic_year": "2026-27",
        "class": "Class_10",
        "subjects": [
            "Mathematics",
            "Science (Physics, Chemistry, Biology)",
            "Social Science (NCERT: History, Geography, Political Science, Economics)",
            "English Language and Literature",
            "Information Technology (402) / Artificial Intelligence (417) / Computer Applications (165)"
        ]
    },
    {
        "board": "CBSE",
        "academic_year": "2026-27",
        "class": "Class_9",
        "subjects": [
            "Mathematics (Ganita Manjari) - Class 9 only",
            "Science (Exploration) - Class 9 only",
            "Social Science (NCERT: History, Geography, Political Science, Economics)",
            "English Language and Literature",
            "Information Technology (402) / Artificial Intelligence (417) / Computer Applications (165)"
        ]
    },
    {
        "board": "KARNATAKA_STATE_BOARD_SSLC",
        "academic_year": "2026-27",
        "class": "Class_10",
        "subjects": [
            "Mathematics",
            "Science (Physics, Chemistry, Biology)",
            "Social Science (KTBS State Syllabus)",
            "First Language Kannada (Siri Kannada)",
            "Second Language English",
            "First Language English",
            "Third Language Hindi (Vallari)"
        ]
    },
    {
        "board": "KARNATAKA_STATE_BOARD_SSLC",
        "academic_year": "2026-27",
        "class": "Class_9",
        "subjects": [
            "Mathematics",
            "Science (Physics, Chemistry, Biology)",
            "Social Science (KTBS State Syllabus)",
            "First Language Kannada (Siri Kannada)",
            "Second Language English",
            "First Language English",
            "Third Language Hindi (Vallari)"
        ]
    },
    {
        "board": "CISCE_ICSE",
        "academic_year": "2026-27",
        "class": "Class_10",
        "subjects": [
            "Mathematics",
            "Physics (Science Paper 1)",
            "Chemistry (Science Paper 2)",
            "Biology (Science Paper 3)",
            "History and Civics (H.C.G. Paper 1)",
            "Geography (H.C.G. Paper 2)",
            "English (Paper 1: Language & Paper 2: Literature - Julius Caesar & Treasure Chest)",
            "Computer Applications (Java)",
            "Commercial Studies (63) & Economics (64)"
        ]
    },
    {
        "board": "CISCE_ICSE",
        "academic_year": "2026-27",
        "class": "Class_9",
        "subjects": [
            "Mathematics",
            "Physics (Science Paper 1)",
            "Chemistry (Science Paper 2)",
            "Biology (Science Paper 3)",
            "History and Civics (H.C.G. Paper 1)",
            "Geography (H.C.G. Paper 2)",
            "English (Paper 1: Language & Paper 2: Literature - Julius Caesar & Treasure Chest)",
            "Computer Applications (Java)",
            "Commercial Studies (63) & Economics (64)"
        ]
    }
]

