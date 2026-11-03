"""
Status Checker for ExamApp Dataset Pipeline
Displays live progress: completed tasks, pending tasks, completion percentage,
and committed record counts across all datasets.
"""

import json
import os
from checkpoint_manager import CheckpointManager
from config import CONFIG, DATASET_FILENAMES

def show_status():
    ckpt_mgr = CheckpointManager()
    summary = ckpt_mgr.get_progress_summary()
    total = summary["total_tasks"]
    completed = summary["completed_tasks"]
    pending = summary["pending_tasks"]
    failed = summary["failed_tasks"]
    records = summary["total_records_committed"]

    pct = (completed / total * 100) if total > 0 else 0.0

    print("=" * 70)
    print("EXAMAPP DATASET GENERATION PROGRESS STATUS")
    print("=" * 70)
    print(f"Overall Progress:       {pct:.1f}%")
    print(f"Completed Tasks:        {completed} / {total}")
    print(f"Pending Tasks:          {pending}")
    print(f"Failed Tasks:           {failed}")
    print(f"Total Committed Records:{records}")
    print("-" * 70)
    target_dir = CONFIG.get("output_dir", "output_datasets_11_12")
    print(f"Dataset Files ({target_dir}/):")
    for name, fname in DATASET_FILENAMES.items():
        fpath = os.path.join(target_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                count = sum(1 for line in f if line.strip())
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  * {name:15s} : {count:5d} records ({size_kb:6.1f} KB) -> {fname}")
        else:
            print(f"  * {name:15s} :     0 records (Not created yet)")

    print("=" * 70)

if __name__ == "__main__":
    show_status()

