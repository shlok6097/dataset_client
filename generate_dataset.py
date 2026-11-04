"""
ExamApp Dataset Generator CLI
Command-line tool to inspect curriculum and trigger dataset generation
by board, class, subject, and chapter.
"""

import argparse
import json
import sys
from typing import Optional
from curriculum_discovery import build_inventory_report, print_inventory_report, resolve_all_chapters, filter_targets
from dataset_generator import run_pipeline, build_batch_prompt
from checkpoint_manager import CheckpointManager
from config import CONFIG, DATASET_NAMES

def main():
    parser = argparse.ArgumentParser(description="ExamApp Dataset Generator CLI for Class 9 & 10")
    parser.add_argument("--board", type=str, help="Filter by board (e.g. CBSE, KARNATAKA_STATE_BOARD_SSLC, CISCE_ICSE)")
    parser.add_argument("--class", dest="class_name", type=str, help="Filter by class (e.g. Class_9, Class_10)")
    parser.add_argument("--subject", type=str, help="Filter by subject name substring (e.g. Mathematics, Science)")
    parser.add_argument("--chapter", type=str, help="Filter by chapter title substring")
    parser.add_argument("--dataset", type=str, choices=DATASET_NAMES, help="Generate only for this dataset category")
    parser.add_argument("--question-type", type=str, choices=[
        "MCQ", "Short_Answer", "Long_Answer", "Numerical", "Assertion_Reason",
        "Case_Based", "Fill_In_The_Blanks", "Match_The_Following"
    ], help="Generate questions of a specific type (e.g. Fill_In_The_Blanks, Match_The_Following)")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry-run without generating records")
    parser.add_argument("--status", action="store_true", help="Check how many tasks and records are processed till now")
    parser.add_argument("--retry-failed", action="store_true", help="Reset and re-run all previously failed tasks")
    parser.add_argument("--mode", type=str, choices=["resume", "new", "retry_failed"], default="resume", help="Execution mode (default: resume)")
    parser.add_argument("--allow-synthetic", action="store_true", help="Allow fallback to synthetic offline templates if LLM fails (default: False, fails task instead)")
    parser.add_argument("--list-curriculum", action="store_true", help="Print the inventory report of the curriculum")
    parser.add_argument("--list-chapters", action="store_true", help="List all chapters matching the filters")
    parser.add_argument("--records-per-batch", type=int, default=CONFIG.get("records_per_batch", 5), help="Number of records per batch")
    parser.add_argument("--batches", type=int, default=CONFIG.get("batches_per_category", 2), help="Number of batches per chapter")
    parser.add_argument("--workers", type=int, default=CONFIG.get("workers", 3), help="Number of concurrent workers (default: 3, set 1 for sequential)")
    parser.add_argument("--max-failed-retries", type=int, default=CONFIG.get("max_failed_retries", 5), help="Number of automatic retry rounds for failed tasks after main run (default: 5)")

    args = parser.parse_args()

    if args.allow_synthetic:
        CONFIG["allow_synthetic"] = True

    if args.status:
        from check_status import show_status
        show_status()
        return

    if args.list_curriculum:
        inv = build_inventory_report()
        print_inventory_report(inv)
        return

    all_targets = resolve_all_chapters()
    filtered = filter_targets(
        all_targets,
        board=args.board,
        class_name=args.class_name,
        subject=args.subject,
        chapter=args.chapter
    )

    if args.list_chapters:
        print(f"\nFound {len(filtered)} matching chapters:")
        for idx, t in enumerate(filtered, start=1):
            ch_num = f"Ch.{t.get('chapter_no')}" if t.get('chapter_no') is not None else "Unit"
            print(f"  {idx:3d}. [{t['board']}] {t['class']} | {t['subject']} | {ch_num}: {t['chapter']}")
        return

    print("=" * 70)
    print("EXAMAPP DATASET GENERATION")
    print("=" * 70)
    print(f"Board Filter:     {args.board or 'ALL'}")
    print(f"Class Filter:     {args.class_name or 'ALL'}")
    print(f"Subject Filter:   {args.subject or 'ALL'}")
    print(f"Chapter Filter:   {args.chapter or 'ALL'}")
    if args.question_type:
        print(f"Question Type:    {args.question_type}")
    print(f"Datasets:         {[args.dataset] if args.dataset else DATASET_NAMES}")
    print(f"Target Chapters:  {len(filtered)}")
    print("=" * 70)

    if not filtered:
        print("No curriculum chapters matched the specified filters. Use --list-chapters to view available targets.")
        return

    if args.question_type:
        for t in filtered:
            t["question_type"] = args.question_type

    # Update config runtime overrides
    CONFIG["records_per_batch"] = args.records_per_batch
    CONFIG["batches_per_category"] = args.batches

    active_ds = [args.dataset] if args.dataset else DATASET_NAMES

    if args.dry_run:
        result = run_pipeline(
            dry_run=True,
            targets=filtered,
            dataset_names=active_ds
        )
        print(f"\n[DRY RUN SUMMARY]")
        print(f"  Eligible Tasks:          {result.get('generation_task_count')}")
        print(f"  Target Chapters:         {result.get('total_chapters')}")
        print(f"  Question Types per Ch.:  {result.get('question_types_count', 8)} (10 questions each = 80 questions/chapter)")
        print(f"  Total Expected Records:  {result.get('total_expected_records', 'N/A')}")
        return

    exec_mode = "retry_failed" if args.retry_failed else args.mode
    print(f"\nStarting generation (Mode: {exec_mode}, Workers: {args.workers}, Auto-Retries: {args.max_failed_retries})...")
    result = run_pipeline(
        mode=exec_mode,
        dry_run=False,
        targets=filtered,
        dataset_names=active_ds,
        workers=args.workers,
        failed_retries=args.max_failed_retries
    )

    out_dir = CONFIG.get("output_dir", "output_datasets_11_12")
    print(f"\n[GENERATION COMPLETED]")
    print(f"  Processed Tasks:      {result['processed_tasks']}")
    print(f"  Committed Records:    {result['committed_records']}")
    summary = result.get("summary", {})
    print(f"  Total Records in DB:  {summary.get('total_records_committed')}")
    print(f"  Failed Tasks Left:    {summary.get('failed_tasks', 0)}")
    print(f"  Output Files:         {out_dir}/*.jsonl")

if __name__ == "__main__":
    main()

