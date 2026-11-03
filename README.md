# ExamApp Dataset Generator (Class 9 & 10)

Production dataset generation pipeline utilizing `class_9_10_karnataka_cbse_icse_curriculum_v2026.2.json` across **Board**, **Class**, **Subject**, and **Chapter**.

---

## 1. Curriculum Coverage

- **Boards (3)**:
  - `CBSE` (Central Board of Secondary Education)
  - `KARNATAKA_STATE_BOARD_SSLC` (Karnataka KSEAB / SSLC)
  - `CISCE_ICSE` (Council for the Indian School Certificate Examinations)
- **Classes (2)**: `Class_9`, `Class_10`
- **Total Chapters**: `555` resolved chapters
- **Academic Year**: `2026-27` (with latest NCERT 2026-27 revisions & state frameworks)

---

## 2. Dataset Categories

The pipeline generates 5 specialized dataset categories, outputted as atomic JSONL files:
1. `questions.jsonl`: Assessment questions supporting **8 distinct question formats**:
   - `MCQ` (Multiple Choice Questions)
   - `Short_Answer` (2-3 marks direct conceptual)
   - `Long_Answer` (4-5 marks proofs, essays, detailed derivations)
   - `Numerical` (Quantitative with parameter ranges)
   - `Assertion_Reason` (Causal logic evaluation)
   - `Case_Based` (Passage/experiment context with sub-questions)
   - `Fill_In_The_Blanks` (Statement with `___` markers, answer key, and optional word bank)
   - `Match_The_Following` (Column I & Column II pairing with explanations)
2. `syllabus.jsonl`: Subtopic breakdowns, learning outcomes, competencies, and estimated teaching hours.
3. `concepts.jsonl`: Detailed pedagogical explanations, key formulas, and common misconceptions.
4. `flashcards.jsonl`: Active-recall front prompts and concise back answers.
5. `rubrics.jsonl`: Assessment criteria and stepwise scoring rubrics.

---

## 3. Quick Start

### Using the CLI (`generate_dataset.py`)

#### View Curriculum Inventory
```bash
python generate_dataset.py --list-curriculum
```

#### List Chapters with Filters
```bash
# List all Class 10 Math chapters in CBSE
python generate_dataset.py --board CBSE --class Class_10 --subject Mathematics --list-chapters

# List Karnataka SSLC Science chapters
python generate_dataset.py --board KARNATAKA_STATE_BOARD_SSLC --class Class_10 --subject Science --list-chapters
```

#### Generate Dataset for a Specific Chapter
```bash
# Generate 5 questions for CBSE Class 10 Mathematics - Real Numbers
python generate_dataset.py --board CBSE --class Class_10 --subject Mathematics --chapter "Real Numbers" --dataset questions --batches 1 --records-per-batch 5

# Generate Fill in the Blanks questions
python generate_dataset.py --board CBSE --class Class_10 --subject Science --chapter "Light - Reflection and Refraction" --dataset questions --question-type Fill_In_The_Blanks --records-per-batch 5

# Generate Match the Following questions
python generate_dataset.py --board KARNATAKA_STATE_BOARD_SSLC --class Class_10 --subject Science --chapter "Chemical Reactions and Equations" --dataset questions --question-type Match_The_Following --records-per-batch 5

# Generate all 5 dataset categories for a specific chapter
python generate_dataset.py --board KARNATAKA_STATE_BOARD_SSLC --class Class_10 --subject Science --chapter "Chemical Reactions and Equations"
```

#### Dry-Run (Estimate tasks and preview prompts without generating)
```bash
python generate_dataset.py --board CBSE --class Class_10 --dry-run
```

---

## 4. Using the Jupyter Notebook

Open and run [`Untitled1.ipynb`](file:///c:/Users/shlok/dataset_02/Untitled1.ipynb) in VS Code or JupyterLab.
All cells (1 through 17) run sequentially with zero configuration:
- Cells 1-15: System verification, prompt previews, validation, and dry-run inventory.
- Cell 16: Interactive chapter filtering and targeted generation by `board`, `class`, `subject`, and `chapter`.
- Cell 17: Visual inspection of generated records across all 5 JSONL files.

---

## 5. Model Fine-Tuning (SFT) Dataset Preparation

The pipeline converts generated curriculum data into fine-tuning datasets via [`train_dataset_exporter.py`](file:///c:/Users/shlok/dataset_02/train_dataset_exporter.py) to train an LLM on **4 core capabilities**:

1. **Question Paper Generation**: Generates full blueprint-aligned papers or targeted questions across 8 formats with step-by-step solutions (`train_task1_paper_gen_chatml.jsonl`).
2. **Topic Explanation**: Produces master-teacher pedagogical explanations with formal theorems, formulas, and warnings against common student misconceptions (`train_task2_topic_explain_chatml.jsonl`).
3. **Student Answer Evaluation**: Acts as a board examiner to score student submissions, award partial marks by step, check required keywords, and provide actionable remediation (`train_task3_answer_eval_chatml.jsonl`).
4. **Active Flashcard Generation**: Builds high-retention spaced repetition decks with front prompts and back answers (`train_task4_flashcards_chatml.jsonl`).

### Export Training Data:
```bash
# Export all 4 tasks in ChatML / OpenAI messages format (for Unsloth, Axolotl, LLaMA-Factory, TRL)
python train_dataset_exporter.py
```

---

## 6. Architecture, Crash Resilience & Resume

The pipeline is built with **zero unnecessary regeneration** and **crash resilience**:

1. **Deterministic Task IDs**: Every batch has a unique slug (e.g. `CBSE_Class_10_Mathematics_Real_Numbers_questions_b1`).
2. **SQLite Task State Machine** (`output_datasets/tasks.db`):
   - Tasks transition: `pending` &rarr; `running` &rarr; `completed` (or `failed`).
   - If an error, power outage, or `Ctrl+C` interrupt occurs, already completed tasks stay marked `completed`.
   - On the next execution, the pipeline runs `recover_stale_tasks()`, resetting any interrupted task back to `pending` and **skipping all completed tasks in 0.001s**.
3. **Pre-Flight Auto-Repair**:
   - If a crash happens mid-write, `verify_and_repair_jsonl()` automatically detects and drops any partial trailing line at EOF before appending new records.
4. **Immediate Flush & Fsync**:
   - Every single batch is written with `os.fsync` immediately to disk before updating the manifest and checkpoint.
   - There are no large in-memory buffers that can be lost on crash.
5. **Resume Anytime**:
   ```bash
   # Automatically resumes from the exact batch where it stopped
   python generate_dataset.py

   # Retry any failed tasks without touching completed ones
   python generate_dataset.py --retry-failed
   ```

