"""
Curriculum Discovery Module
Loads and resolves curriculum across Karnataka State Board (KSEAB/PUC/SSLC),
CBSE, and CISCE (ISC/ICSE) from official curriculum JSON.
Accurately handles shared NCERT core, board overrides, book-to-class mappings,
and board-specific subjects for Class 9, 10, 11, and 12.
"""

import json
import os
from typing import Dict, List, Any, Optional
from logger import logger

DEFAULT_CURRICULUM_PATH = "class_11_12_karnataka_cbse_isc_curriculum_v2026.2.json"

def load_curriculum(json_path: Optional[str] = None) -> Dict[str, Any]:
    path = json_path or os.getenv("CURRICULUM_JSON_PATH", DEFAULT_CURRICULUM_PATH)
    if not os.path.isabs(path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cand = os.path.join(base_dir, path)
        if os.path.exists(cand):
            path = cand
    if not os.path.exists(path):
        raise FileNotFoundError(f"Curriculum file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_all_chapters(curriculum_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Flattens the entire curriculum tree into discrete target records:
    [Board, Class, Subject, Chapter No, Chapter Title, Academic Year, etc.]
    Accurately applies inheritance rules for shared NCERT core subjects,
    board-specific overrides, and book assignments.
    """
    if curriculum_data is None:
        curriculum_data = load_curriculum()

    # Supports both Class 11-12 ('shared_ncert_core') and Class 9-10 ('shared_ncert_math_science_core')
    shared_core = curriculum_data.get("shared_ncert_core") or curriculum_data.get("shared_ncert_math_science_core") or {}
    boards = curriculum_data.get("boards", {})
    resolved: List[Dict[str, Any]] = []

    for board_id, board_info in boards.items():
        board_name = board_info.get("board_name", board_id)
        inherits_shared = board_info.get("inherits_shared_ncert_core") or board_info.get("inherits_shared_ncert_math_science")
        inherits_classes = board_info.get("inherits_shared_core_classes")
        exceptions = board_info.get("shared_core_exceptions", [])
        overrides = board_info.get("shared_core_overrides", {})

        # CISCE/ISC in 11-12 defines all its active subjects inside board_specific_subjects
        is_cisce = "CISCE" in board_id or "ISC" in board_id or "ICSE" in board_id

        # 1. Inherited Shared NCERT Core
        if inherits_shared and not (is_cisce and "shared_core_notes" in board_info):
            for subj in shared_core.get("subjects", []):
                subj_name = subj.get("subject_name", "")
                subj_id = subj.get("subject_id", "")

                # Skip explicitly exempted core subjects
                if subj_id in exceptions:
                    continue

                # Handle subjects with dynamic class-to-book assignments (e.g., NCERT_ECON)
                if "class_assignment" in subj and "books" in subj:
                    assignment = subj.get("class_assignment", {}).get(board_id, {})
                    books = subj.get("books", {})
                    for cls_key, book_names in assignment.items():
                        if not isinstance(book_names, list):
                            continue
                        if inherits_classes and cls_key not in inherits_classes:
                            continue
                        cls_name = f"Class_{cls_key}"
                        cls_disp = "1st PUC" if (board_id == "KARNATAKA_PUC" and cls_key == "11") else (
                            "2nd PUC" if (board_id == "KARNATAKA_PUC" and cls_key == "12") else cls_name
                        )
                        for bname in book_names:
                            for ch in books.get(bname, []):
                                if not isinstance(ch, dict):
                                    continue
                                ch_title = ch.get("title") or ch.get("chapter_name") or ""
                                if not ch_title:
                                    continue
                                book_display = bname.replace("_", " ").title()
                                resolved.append({
                                    "board": board_id,
                                    "board_display": board_name,
                                    "academic_year": "2026-27",
                                    "class": cls_name,
                                    "class_display": cls_disp,
                                    "subject": subj_name,
                                    "subject_id": subj_id,
                                    "chapter_no": ch.get("chapter_no"),
                                    "chapter": ch_title,
                                    "book": book_display,
                                    "discipline": ch.get("discipline", ""),
                                    "division": ch.get("division") or ch.get("section") or book_display,
                                    "source": "shared_ncert_core",
                                    "chapter_metadata": ch
                                })
                    continue

                # Standard subjects with 'classes' map
                subj_classes = subj.get("classes", {})
                target_classes = inherits_classes if inherits_classes is not None else list(subj_classes.keys())
                for cls_key in target_classes:
                    cls_name = f"Class_{cls_key}"
                    cls_disp = "1st PUC" if (board_id == "KARNATAKA_PUC" and cls_key == "11") else (
                        "2nd PUC" if (board_id == "KARNATAKA_PUC" and cls_key == "12") else cls_name
                    )

                    # Check for board-specific overrides for this subject and class
                    if subj_id in overrides and cls_key in overrides[subj_id]:
                        ch_list = overrides[subj_id][cls_key]
                        source = "shared_core_override"
                    else:
                        ch_list = subj_classes.get(cls_key, [])
                        source = "shared_ncert_core"

                    if not isinstance(ch_list, list):
                        continue

                    for ch in ch_list:
                        if not isinstance(ch, dict):
                            continue
                        ch_title = ch.get("title") or ch.get("chapter_name") or ""
                        if not ch_title:
                            continue
                        resolved.append({
                            "board": board_id,
                            "board_display": board_name,
                            "academic_year": "2026-27",
                            "class": cls_name,
                            "class_display": cls_disp,
                            "subject": subj_name,
                            "subject_id": subj_id,
                            "chapter_no": ch.get("chapter_no"),
                            "chapter": ch_title,
                            "discipline": ch.get("discipline", ""),
                            "division": ch.get("division") or ch.get("section") or "",
                            "book": ch.get("book", "NCERT"),
                            "source": source,
                            "chapter_metadata": ch
                        })

        # 2. Board-Specific Subjects
        for subj in board_info.get("board_specific_subjects", []):
            subj_name = subj.get("subject_name", "")
            subj_id = subj.get("subject_id", "")
            for cls_key, ch_list in subj.get("classes", {}).items():
                cls_name = f"Class_{cls_key}"
                cls_disp = "1st PUC" if (board_id == "KARNATAKA_PUC" and cls_key == "11") else (
                    "2nd PUC" if (board_id == "KARNATAKA_PUC" and cls_key == "12") else cls_name
                )
                if isinstance(ch_list, list):
                    for ch in ch_list:
                        if not isinstance(ch, dict):
                            continue
                        ch_title = ch.get("title") or ch.get("chapter_name") or ""
                        if not ch_title:
                            continue
                        division = ch.get("division") or ch.get("section") or ch.get("discipline") or ""
                        resolved.append({
                            "board": board_id,
                            "board_display": board_name,
                            "academic_year": "2026-27",
                            "class": cls_name,
                            "class_display": cls_disp,
                            "subject": subj_name,
                            "subject_id": subj_id,
                            "chapter_no": ch.get("chapter_no"),
                            "chapter": ch_title,
                            "discipline": ch.get("discipline", ""),
                            "division": division,
                            "book": ch.get("book", ""),
                            "source": "board_specific",
                            "chapter_metadata": ch
                        })

    return resolved

def build_inventory_report(curriculum_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Builds a structured statistical report of the curriculum coverage.
    """
    if curriculum_data is None:
        curriculum_data = load_curriculum()

    targets = resolve_all_chapters(curriculum_data)

    boards = sorted(list(set(t["board"] for t in targets)))
    classes = sorted(list(set(t["class"] for t in targets)))
    subjects = sorted(list(set(t["subject"] for t in targets)))

    board_class_breakdown: Dict[str, Dict[str, int]] = {}
    board_subject_breakdown: Dict[str, Dict[str, int]] = {}

    for t in targets:
        b = t["board"]
        c = t["class"]
        s = t["subject"]

        if b not in board_class_breakdown:
            board_class_breakdown[b] = {}
        board_class_breakdown[b][c] = board_class_breakdown[b].get(c, 0) + 1

        if b not in board_subject_breakdown:
            board_subject_breakdown[b] = {}
        board_subject_breakdown[b][s] = board_subject_breakdown[b].get(s, 0) + 1

    return {
        "version": curriculum_data.get("version", "2026.2"),
        "total_chapters": len(targets),
        "total_boards": len(boards),
        "boards": boards,
        "classes": classes,
        "subjects": subjects,
        "board_class_breakdown": board_class_breakdown,
        "board_subject_breakdown": board_subject_breakdown,
        "targets": targets
    }

def print_inventory_report(inventory: Dict[str, Any]) -> None:
    """
    Pretty-prints the curriculum discovery inventory report,
    and includes live dataset generation progress.
    """
    print("=" * 70)
    print(f"OFFICIAL CURRICULUM SYLLABUS CATALOG (Syllabus v{inventory.get('version')})")
    print(f"NOTE: This catalog represents {inventory['total_chapters']} chapters across textbooks.")
    print("=" * 70)
    print(f"Total Boards:   {inventory['total_boards']} {inventory['boards']}")
    print(f"Classes:        {inventory['classes']}")
    print(f"Total Chapters: {inventory['total_chapters']} chapters in curriculum")
    print("-" * 70)
    print("Chapter Counts by Board and Class (Syllabus Scope):")
    for board, classes in sorted(inventory["board_class_breakdown"].items()):
        total_board = sum(classes.values())
        print(f"  * {board} (Total: {total_board} chapters):")
        for cls_name, cnt in sorted(classes.items()):
            print(f"      - {cls_name}: {cnt} chapters")

    print("-" * 70)
    print("Subjects Summary:")
    for board, subjects in sorted(inventory["board_subject_breakdown"].items()):
        print(f"  * {board}: {len(subjects)} subjects covered")
    print("=" * 70)

    # Automatically show live generation progress from current target output dir
    try:
        from checkpoint_manager import CheckpointManager
        ckpt_mgr = CheckpointManager()
        summary = ckpt_mgr.get_progress_summary()
        tot = summary["total_tasks"]
        done = summary["completed_tasks"]
        pct = (done / tot * 100) if tot > 0 else 0.0
        print(f"LIVE DATASET GENERATION PROGRESS ({ckpt_mgr.output_dir}/):")
        print(f"  * Completed Tasks:        {done} / {tot} ({pct:.1f}%)")
        print(f"  * Pending Tasks:          {summary['pending_tasks']}")
        print(f"  * Failed Tasks:           {summary['failed_tasks']}")
        print(f"  * Total Committed Records:{summary['total_records_committed']}")
        print("  (Tip: Run 'python check_status.py' or 'python generate_dataset.py --status' for file details)")
        print("=" * 70)
    except Exception:
        pass

def filter_targets(
    targets: List[Dict[str, Any]],
    board: Optional[str] = None,
    class_name: Optional[str] = None,
    subject: Optional[str] = None,
    chapter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filters resolved chapter targets by board, class, subject substring, or chapter substring.
    Supports user aliases like '11', '12', '1st_PUC', '2nd_PUC', 'SSLC', 'ISC', etc.
    """
    results = targets
    if board:
        b_lower = board.lower().replace(" ", "_")
        results = [
            t for t in results
            if b_lower in t["board"].lower() or b_lower in t.get("board_display", "").lower()
        ]
    if class_name:
        c_clean = class_name.lower().replace(" ", "_").replace("-", "_")
        if c_clean in ["11", "class11", "class_11", "1st_puc", "1stpuc", "puc1", "puc_1"]:
            norm = ["class_11", "1st_puc", "11"]
        elif c_clean in ["12", "class12", "class_12", "2nd_puc", "2ndpuc", "puc2", "puc_2"]:
            norm = ["class_12", "2nd_puc", "12"]
        elif c_clean in ["9", "class9", "class_9"]:
            norm = ["class_9", "9"]
        elif c_clean in ["10", "class10", "class_10", "sslc"]:
            norm = ["class_10", "10", "sslc"]
        else:
            norm = [c_clean]

        results = [
            t for t in results
            if any(n in t["class"].lower() or n in t.get("class_display", "").lower() for n in norm)
        ]
    if subject:
        s_lower = subject.lower()
        results = [
            t for t in results
            if s_lower in t["subject"].lower() or s_lower in t.get("subject_id", "").lower()
        ]
    if chapter:
        ch_lower = chapter.lower()
        results = [t for t in results if ch_lower in t["chapter"].lower()]
    return results

if __name__ == "__main__":
    inv = build_inventory_report()
    print_inventory_report(inv)
