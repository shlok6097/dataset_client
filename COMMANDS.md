# ExamApp Dataset Pipeline - Command Cheat Sheet (Class 11 & 12 / 1st & 2nd PUC)

Essential terminal commands for dataset generation, multi-worker concurrency, crash-resumption, targeted exports, and LLM fine-tuning across Karnataka PUC, CBSE, and CISCE ISC.

---

## 1. Check Progress (How Many Processed Till Now)

Check processed vs pending tasks, completion percentage, and record counts across all 5 datasets in `output_datasets_11_12/`:
```pwsh
python check_status.py
```
Or via the main generator CLI:
```pwsh
python generate_dataset.py --status
```
Or in PowerShell:
```pwsh
.\run_pipeline.ps1 -Status
```

### Check Archived Class 9 & 10 Progress Anytime
The completed Class 9 & 10 dataset (66,653 records) is permanently preserved in `output_datasets_class_9_10/`:
```pwsh
$env:OUTPUT_DIR="output_datasets_class_9_10"; python check_status.py; Remove-Item Env:\OUTPUT_DIR
```

### Watch Live Generation Logs in Real Time
Every single generation step auto-flushes and syncs directly to disk. You can stream the live logs in PowerShell:
```pwsh
Get-Content dataset_generator.log -Wait -Tail 20
```
*(Press `Ctrl+C` to exit the live stream anytime)*

---

## 2. Speed Optimization & 3-Account High-Throughput

### Run with 3 Concurrent Workers
With 3 round-robin accounts configured on `gemini-web2api`, run with `--workers 3`:
```pwsh
# 3 parallel workers (3x speed, auto-balanced across 3 accounts)
python generate_dataset.py --workers 3

# Or via PowerShell runner:
.\run_pipeline.ps1 -Workers 3
```

### Built-in Anti-Bot & Anti-Blocking Protections
1. **Initial Staggering**: Concurrent workers start with a 1.2s offset to avoid hitting the server on the exact same millisecond.
2. **Cadence Jitter**: An automatic randomized delay (`REQUEST_DELAY_SEC` + 0.2s–0.8s) is inserted between tasks to break mechanical rhythm.
3. **Adaptive 429 / 503 Exponential Backoff**: When `gemini-web2api` is throttled by Google, the generator automatically pauses (4s -> 10s -> 20s -> 35s -> 60s) with jitter and retries without dropping tasks.

---

## 3. Resume, Crash Recovery & Automatic 5x Retry

### Automatic 5-Round Failed Task Retry (Built-in)
After completing the main run across all pending chapters, the pipeline **automatically inspects for any failed tasks** and retries them across up to **5 consecutive rounds** (with cool-down delays) until 0 failed tasks remain:
```pwsh
# Runs main generation + automatically retries any failed tasks up to 5 times
python generate_dataset.py --workers 3

# Customize retry rounds if desired (e.g. 5 rounds is default):
python generate_dataset.py --workers 3 --max-failed-retries 5
```

### Manual Resumption & Retry
If generation was stopped midway due to `Ctrl+C` or a system restart:
```pwsh
# Automatically resumes from the exact batch where it stopped (Zero duplicate work)
python generate_dataset.py --workers 3
```

Check pending vs. completed tasks before generating:
```pwsh
python generate_dataset.py --dry-run
```

Re-run only the tasks that failed:
```pwsh
python generate_dataset.py --retry-failed --workers 3
```

---

## 4. Export Dataset for Model Training (SFT / Fine-Tuning)

Convert all generated data into fine-tuning datasets for the 4 core tasks:
1. Question Paper Generation
2. Topic Explanation
3. Student Answer Evaluation & Rubrics
4. Active Flashcard Generation

```pwsh
# Exports into OpenAI / ChatML format (train_sft_messages.jsonl)
python train_dataset_exporter.py

# Export into Alpaca format (instruction, input, output)
python -c "from train_dataset_exporter import export_training_datasets; export_training_datasets(format_type='alpaca')"
```

---

## 5. Targeted Generation by Board, Class, Subject & Chapter

### List Chapters in the Curriculum
```pwsh
# List all Karnataka 1st PUC (Class 11) chapters
python generate_dataset.py --board KARNATAKA_PUC --class 1st_PUC --list-chapters

# List CBSE Class 12 Physics chapters
python generate_dataset.py --board CBSE --class Class_12 --subject Physics --list-chapters

# List ISC Class 11 Computer Science chapters
python generate_dataset.py --board CISCE_ISC --class Class_11 --subject "Computer Science" --list-chapters
```

### Generate for a Specific Chapter
```pwsh
# Generate for CBSE Class 11 Physics - Units and Measurements
python generate_dataset.py --board CBSE --class Class_11 --subject Physics --chapter "Units and Measurements"

# Generate for Karnataka 2nd PUC Accountancy
python generate_dataset.py --board KARNATAKA_PUC --class 2nd_PUC --subject Accountancy --chapter "Accounting for Partnership Fundamentals"
```

---




### Fill in the Blanks (`Fill_In_The_Blanks`)
```pwsh
python generate_dataset.py --board CBSE --class Class_11 --subject Physics --chapter "Units and Measurements" --dataset questions --question-type Fill_In_The_Blanks
```

### Match the Following (`Match_The_Following`)
```pwsh
python generate_dataset.py --board KARNATAKA_PUC --class 1st_PUC --subject Chemistry --chapter "Structure of Atom" --dataset questions --question-type Match_The_Following
```

### Other Question Types
Available choices for `--question-type`:
- `MCQ`
- `Short_Answer`
- `Long_Answer`
- `Numerical`
- `Assertion_Reason`
- `Case_Based`
- `Fill_In_The_Blanks`
- `Match_The_Following`

---

## 7. View Curriculum Inventory Summary
```pwsh
python generate_dataset.py --list-curriculum
```

