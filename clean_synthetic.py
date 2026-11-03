"""
Clean Synthetic Records Utility
Identifies and purges synthetic boilerplate records from JSONL datasets
and resets the corresponding tasks in tasks.db back to 'pending'.
"""

import json
import os
import sqlite3
import shutil
from datetime import datetime
from config import CONFIG

SYNTHETIC_MARKERS = [
    "(Question ",
    "With the aid of a neat labeled diagram",
    "Physical Quantities vs Standard SI Units",
    "In Heron's Formula, the standard SI unit",
    "Directions: In the following question on",
    "Standard correct relation for ",
    "Inverted fraction (Common Student Trap)",
    "Comprehensive fundamental definition, scope, and foundational principles",
    "Core statement, technical definition, and boundary conditions",
    "Neat diagram with ray directions, axes, and points labeled",
    "Part A (Diagram): Neat diagram with ray directions",
    "Explain the primary mechanism of ",
    "Read the following experimental case study regarding ",
    "An object is placed at a distance of u =",
]

SYNTHETIC_KEYWORDS = {
    'column_i', 'conceptual_choice', 'labeled_diagram', 
    'cartesian_sign', 'causality', 'terminology', 'experimental_analysis'
}

def is_synthetic(record: dict) -> bool:
    s = json.dumps(record, ensure_ascii=False)
    for marker in SYNTHETIC_MARKERS:
        if marker in s:
            return True
            
    # Check rubric keywords signature
    kws = set(record.get('rubric_keywords', []))
    if kws & SYNTHETIC_KEYWORDS:
        return True
    if 'definition' in kws and 'conditions' in kws:
        return True
        
    # Check concepts/flashcards synthetic signatures
    if "Confusing scalar and vector properties or omitting Cartesian sign rules in " in s:
        return True
    if "Core statement, technical definition, and boundary conditions for " in s:
        return True
        
    return False

def clean_datasets(dry_run: bool = True, dataset_dir: str = None):
    if dataset_dir is None:
        dataset_dir = CONFIG.get("output_dir", "output_datasets_11_12")
    db_path = os.path.join(dataset_dir, "tasks.db")
    
    files = ["questions.jsonl", "concepts.jsonl", "flashcards.jsonl", "syllabus.jsonl", "rubrics.jsonl"]
    
    print("=" * 70)
    print(f"PURGING SYNTHETIC FALLBACK RECORDS (Dry Run: {dry_run})")
    print("=" * 70)
    
    tasks_to_reset = set()
    stats = {}
    
    for fname in files:
        fpath = os.path.join(dataset_dir, fname)
        if not os.path.exists(fpath):
            continue
            
        with open(fpath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            
        clean_lines = []
        synth_count = 0
        
        for l in lines:
            try:
                rec = json.loads(l)
                if is_synthetic(rec):
                    synth_count += 1
                    # Identify chapter/task
                    b = rec.get("board", "")
                    c = rec.get("class", "")
                    s = rec.get("subject", "")
                    ch = rec.get("chapter", "")
                    qt = rec.get("question_type", "")
                    ds = fname.replace(".jsonl", "")
                    tasks_to_reset.add((b, c, s, ch, ds, qt))
                else:
                    clean_lines.append(l)
            except Exception:
                clean_lines.append(l)
                
        stats[fname] = {
            "total_before": len(lines),
            "synthetic_removed": synth_count,
            "real_retained": len(clean_lines)
        }
        
        if not dry_run and synth_count > 0:
            # Backup original
            bak_path = fpath + ".bak"
            shutil.copy2(fpath, bak_path)
            # Write cleaned
            with open(fpath, "w", encoding="utf-8") as f:
                for cl in clean_lines:
                    f.write(cl + "\n")
                    
    print("\nFile Statistics:")
    for fname, st in stats.items():
        print(f"  * {fname:18}: {st['total_before']} total -> removed {st['synthetic_removed']} synthetic -> {st['real_retained']} real retained")
        
    print(f"\nIdentified {len(tasks_to_reset)} distinct task categories to reset in tasks.db.")
    
    if os.path.exists(db_path) and not dry_run:
        from checkpoint_manager import make_chapter_key
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        reset_count = 0
        for b, c, s, ch, ds, qt in tasks_to_reset:
            target = {"board": b, "class": c, "subject": s, "chapter": ch}
            ch_key = make_chapter_key(target)
            if qt:
                prefix = f"{ch_key}_{ds}_{qt}_"
            else:
                prefix = f"{ch_key}_{ds}_"
            cur.execute(
                "UPDATE tasks SET status='pending', record_count=0 WHERE task_id LIKE ? AND status='completed'",
                (f"{prefix}%",)
            )
            reset_count += cur.rowcount
        conn.commit()
        conn.close()
        print(f"Successfully reset {reset_count} completed tasks in tasks.db back to 'pending'.")

if __name__ == "__main__":
    import sys
    dry = "--apply" not in sys.argv
    clean_datasets(dry_run=dry)
    if dry:
        print("\nTo apply this cleanup and reset tasks.db, run:")
        print("  python clean_synthetic.py --apply")
