"""
Training Dataset Exporter Module
Converts raw curriculum and dataset records into fine-tuning (SFT) datasets
optimized for training an AI model on 4 core capabilities:
  1. Generate Question Papers (any topic, any question type, complete marking scheme)
  2. Explain Any Topic (pedagogical explanation, formulas, misconceptions, analogies)
  3. Evaluate Student Answers (step-by-step grading, rubric scoring, partial credit, feedback)
  4. Generate Active-Recall Flashcards (spaced repetition Q&A, retrieval cues)

Supports export formats:
  - chatml / openai: {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}
  - alpaca: {"instruction": "...", "input": "...", "output": "..."}
  - sharegpt: {"conversations": [{"from": "human", ...}, {"from": "gpt", ...}]}
"""

import json
import os
import random
from typing import Any, Dict, List, Optional
from config import CONFIG, DATASET_FILENAMES
from curriculum_discovery import resolve_all_chapters
from logger import logger

SYSTEM_PROMPT = (
    "You are an expert AI Master Educator and Board Exam Specialist for Indian secondary curricula "
    "(CBSE, Karnataka State Board SSLC, and CISCE ICSE). You excel at creating rigorous question papers, "
    "providing deep pedagogical explanations, evaluating student answers with partial marking rubrics, "
    "and constructing high-yield active-recall revision materials."
)

def load_jsonl_records(filename: str, output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    target_dir = output_dir or CONFIG.get("output_dir", "output_datasets")
    path = os.path.join(target_dir, filename)
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records

# ==============================================================================
# TASK 1: Question Paper & Assessment Generation
# ==============================================================================
def build_task1_paper_generation_samples(
    questions: List[Dict[str, Any]],
    syllabus: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Builds training pairs where the model generates complete, structured question papers
    or targeted questions for any chapter and question type.
    """
    samples = []

    # 1. Single Question Generation by Type & Chapter
    for q in questions:
        board = q.get("board", "CBSE")
        cls_name = q.get("class", "Class_10")
        subject = q.get("subject", "Science")
        chapter = q.get("chapter", "Light")
        q_type = q.get("question_type", "MCQ")
        marks = q.get("marks_weightage", 1)
        diff = q.get("difficulty", "Medium")

        user_prompt = (
            f"Generate a {diff}-difficulty {q_type} question ({marks} marks) for {board} {cls_name} "
            f"{subject}, Chapter: '{chapter}'. Provide the complete question text, options (if applicable), "
            f"detailed answer key with step-by-step rationale, and rubric evaluation keywords."
        )

        assistant_resp = (
            f"### {board} {cls_name} | {subject}\n"
            f"**Chapter**: {chapter}\n"
            f"**Type**: {q_type} | **Marks**: {marks} | **Difficulty**: {diff}\n\n"
            f"**Question**:\n{q.get('seed_question')}\n\n"
        )
        if q.get("options") and q_type in ["MCQ", "Match_The_Following", "Fill_In_The_Blanks"]:
            assistant_resp += "**Options / Choices**:\n"
            for opt in q["options"]:
                assistant_resp += f"- {opt}\n"
            assistant_resp += "\n"

        assistant_resp += (
            f"**Answer Key & Step-by-Step Solution**:\n{q.get('answer_key')}\n\n"
            f"**Rubric Evaluation Keywords**: {', '.join(q.get('rubric_keywords', []))}"
        )

        samples.append({
            "task": "question_paper_generation",
            "instruction": user_prompt,
            "input": "",
            "output": assistant_resp,
            "metadata": {"board": board, "class": cls_name, "subject": subject, "chapter": chapter, "type": q_type}
        })

    # 2. Comprehensive Multi-Section Question Paper
    # Group questions by (board, class, subject, chapter)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for q in questions:
        key = f"{q.get('board')}_{q.get('class')}_{q.get('subject')}_{q.get('chapter')}"
        grouped.setdefault(key, []).append(q)

    for key, q_list in grouped.items():
        if len(q_list) >= 3:
            first_q = q_list[0]
            board = first_q.get("board", "CBSE")
            cls = first_q.get("class", "Class_10")
            subj = first_q.get("subject", "Science")
            ch = first_q.get("chapter", "Light")

            total_marks = sum(item.get("marks_weightage", 1) for item in q_list)
            user_prompt = (
                f"Design a complete unit test paper ({total_marks} Marks) for {board} {cls} {subj} "
                f"on the chapter '{ch}'. Include a balanced distribution of question formats (Objective, Short Answer, "
                f"Long Answer / Numerical) along with complete scoring guidelines and solutions."
            )

            paper_text = (
                f"# {board} Examination Preparation Paper\n"
                f"**Class**: {cls} | **Subject**: {subj}\n"
                f"**Chapter**: {ch} | **Time Allowed**: 45 Minutes | **Maximum Marks**: {total_marks}\n\n"
                f"---\n## SECTION A: OBJECTIVE & RECALL QUESTIONS\n"
            )

            solutions_text = "\n\n---\n## SOLUTIONS & STEPWISE MARKING SCHEME\n"
            for idx, item in enumerate(q_list, start=1):
                paper_text += f"\n**Q{idx}** ({item.get('marks_weightage', 1)} Mark - {item.get('question_type')}):\n{item.get('seed_question')}\n"
                if item.get("options"):
                    for opt in item["options"]:
                        paper_text += f"   - {opt}\n"

                solutions_text += (
                    f"\n**Answer Q{idx}**:\n{item.get('answer_key')}\n"
                    f"*Key Evaluation Terms*: {', '.join(item.get('rubric_keywords', []))}\n"
                )

            samples.append({
                "task": "question_paper_generation",
                "instruction": user_prompt,
                "input": "",
                "output": paper_text + solutions_text,
                "metadata": {"board": board, "class": cls, "subject": subj, "chapter": ch, "type": "Full_Paper"}
            })

    return samples

# ==============================================================================
# TASK 2: Topic Explanation & Conceptual Breakdown
# ==============================================================================
def build_task2_topic_explanation_samples(
    concepts: List[Dict[str, Any]],
    syllabus: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Builds training pairs where the model provides pedagogical master-class explanations
    with core principles, formulas, step-by-step insights, and common pitfalls.
    """
    samples = []
    for c in concepts:
        board = c.get("board", "CBSE")
        cls_name = c.get("class", "Class_10")
        subject = c.get("subject", "Mathematics")
        chapter = c.get("chapter", "Real Numbers")
        title = c.get("concept_title", chapter)
        explanation = c.get("explanation", "")
        formulas = c.get("key_formulas", [])
        misconceptions = c.get("common_misconceptions", [])

        user_prompt = (
            f"Explain the topic '{title}' from Chapter '{chapter}' for a {board} {cls_name} {subject} student. "
            f"Provide an intuitive overview, formal mathematical/scientific principles, key formulas, "
            f"and warn about frequent student misconceptions."
        )

        response = (
            f"## Conceptual Breakdown: {title}\n"
            f"**Curriculum**: {board} | **Class**: {cls_name} | **Subject**: {subject} | **Chapter**: {chapter}\n\n"
            f"### 1. Overview & Core Concept\n{explanation}\n\n"
        )
        if formulas:
            response += "### 2. Governing Laws & Key Formulas\n"
            for f in formulas:
                response += f"- $${f}$$\n"
            response += "\n"

        if misconceptions:
            response += "### 3. Common Misconceptions & Exam Pitfalls\n"
            for m in misconceptions:
                response += f"- **Caution**: {m}\n"
            response += "\n"

        response += (
            "### 4. Board Exam Strategy & High-Yield Tip\n"
            f"When answering questions on {title} in {board} board exams, always state the standard Cartesian conventions, "
            f"write explicit definitions before algebraic substitutions, and specify SI units in final answers."
        )

        samples.append({
            "task": "topic_explanation",
            "instruction": user_prompt,
            "input": "",
            "output": response,
            "metadata": {"board": board, "class": cls_name, "subject": subject, "chapter": chapter, "title": title}
        })

    return samples

# ==============================================================================
# TASK 3: Student Answer Evaluation & Rubric Scoring
# ==============================================================================
def build_task3_answer_evaluation_samples(
    questions: List[Dict[str, Any]],
    rubrics: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Builds training pairs where the model acts as a board examiner:
    evaluates a student's answer, awards partial marks according to rubrics,
    identifies missing keywords, and gives actionable remediation.
    """
    samples = []

    for q in questions:
        board = q.get("board", "CBSE")
        cls = q.get("class", "Class_10")
        subj = q.get("subject", "Science")
        ch = q.get("chapter", "Light")
        q_text = q.get("seed_question", "")
        q_type = q.get("question_type", "Short_Answer")
        max_marks = q.get("marks_weightage", 3)
        ideal_ans = q.get("answer_key", "")
        keywords = q.get("rubric_keywords", [])

        # Scenario A: Good Answer (Full or near full marks)
        student_ans_good = (
            f"Answer: In {ch}, the fundamental rule is that {q_text[:40]}... "
            f"Following {ideal_ans[:120]}. Therefore, concluding with proper units and statements."
        )
        user_prompt_good = (
            f"Evaluate the following student's response for a {board} {cls} {subj} exam.\n\n"
            f"**Question** ({max_marks} Marks):\n{q_text}\n\n"
            f"**Student Answer**:\n{student_ans_good}\n\n"
            f"**Evaluation Request**: Provide awarded marks, step-by-step scoring breakdown, "
            f"rubric keywords identified, and feedback."
        )
        feedback_good = (
            f"### Board Evaluation Report\n"
            f"- **Marks Awarded**: {max_marks} / {max_marks} (Full Marks)\n"
            f"- **Performance Level**: Excellent\n\n"
            f"**Step-by-Step Scoring Breakdown**:\n"
            f"- Concept Identification: {max_marks * 0.4:.1f}/{max_marks * 0.4:.1f} Marks (Clear statement of principles)\n"
            f"- Derivation / Solution: {max_marks * 0.4:.1f}/{max_marks * 0.4:.1f} Marks (Accurate step sequence)\n"
            f"- Final Form & Units: {max_marks * 0.2:.1f}/{max_marks * 0.2:.1f} Marks (Accurate conclusion)\n\n"
            f"**Rubric Keywords Verified**: {', '.join(keywords)}\n"
            f"**Examiner Remarks**: The student demonstrated strong conceptual clarity and adhered strictly to board presentation norms."
        )
        samples.append({
            "task": "answer_evaluation",
            "instruction": user_prompt_good,
            "input": "",
            "output": feedback_good,
            "metadata": {"board": board, "class": cls, "subject": subj, "chapter": ch, "score": "full"}
        })

        # Scenario B: Partial Answer with Common Flaw (Partial Credit)
        partial_marks = max(0.5, round(max_marks * 0.5, 1))
        student_ans_partial = f"The value is directly obtained. We know the formula applies to {ch}, so answer is approximate."
        user_prompt_partial = (
            f"Evaluate the following student's response for a {board} {cls} {subj} exam.\n\n"
            f"**Question** ({max_marks} Marks):\n{q_text}\n\n"
            f"**Student Answer**:\n{student_ans_partial}\n\n"
            f"**Evaluation Request**: Provide awarded marks, step-by-step scoring breakdown, "
            f"missing keywords, and constructive correction."
        )
        missing_kw = keywords[1:] if len(keywords) > 1 else keywords
        feedback_partial = (
            f"### Board Evaluation Report\n"
            f"- **Marks Awarded**: {partial_marks} / {max_marks} (Partial Credit)\n"
            f"- **Performance Level**: Needs Improvement\n\n"
            f"**Step-by-Step Scoring Breakdown**:\n"
            f"- Concept Identification: {partial_marks}/{max_marks * 0.4:.1f} Marks (Partial mention of topic context)\n"
            f"- Derivation / Solution: 0.0/{max_marks * 0.4:.1f} Marks (Missing step-by-step calculation or proof)\n"
            f"- Units & Conventions: 0.0/{max_marks * 0.2:.1f} Marks (Lacks SI units and Cartesian signs)\n\n"
            f"**Missing Essential Rubric Keywords**: {', '.join(missing_kw)}\n\n"
            f"**Model Answer & Remediation**:\n"
            f"To secure full marks, the student must include:\n{ideal_ans}"
        )
        samples.append({
            "task": "answer_evaluation",
            "instruction": user_prompt_partial,
            "input": "",
            "output": feedback_partial,
            "metadata": {"board": board, "class": cls, "subject": subj, "chapter": ch, "score": "partial"}
        })

    return samples

# ==============================================================================
# TASK 4: Active-Recall Flashcard Generation
# ==============================================================================
def build_task4_flashcard_samples(
    flashcards: List[Dict[str, Any]],
    concepts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Builds training pairs where the model generates high-impact active recall flashcard decks
    for rapid revision.
    """
    samples = []
    # Group flashcards by chapter
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for fc in flashcards:
        key = f"{fc.get('board')}_{fc.get('class')}_{fc.get('subject')}_{fc.get('chapter')}"
        grouped.setdefault(key, []).append(fc)

    for key, fc_list in grouped.items():
        first = fc_list[0]
        board = first.get("board", "CBSE")
        cls = first.get("class", "Class_10")
        subj = first.get("subject", "Science")
        ch = first.get("chapter", "Light")

        user_prompt = (
            f"Create a deck of active-recall revision flashcards for {board} {cls} {subj}, "
            f"Chapter: '{ch}'. Format each card with a Front Trigger (active retrieval question) "
            f"and Back Answer (concise high-retention explanation with key formulas/facts)."
        )

        deck_text = f"### Active-Recall Revision Deck: {ch}\n**Board**: {board} | **Class**: {cls} | **Subject**: {subj}\n\n"
        for idx, item in enumerate(fc_list, start=1):
            deck_text += (
                f"**Card {idx}**\n"
                f"- **Front (Prompt)**: {item.get('front_prompt')}\n"
                f"- **Back (Answer)**: {item.get('back_answer')}\n"
                f"- **Tags**: {', '.join(item.get('tags', []))}\n\n"
            )

        samples.append({
            "task": "flashcard_generation",
            "instruction": user_prompt,
            "input": "",
            "output": deck_text.strip(),
            "metadata": {"board": board, "class": cls, "subject": subj, "chapter": ch, "card_count": len(fc_list)}
        })

    return samples

# ==============================================================================
# Master Exporter
# ==============================================================================
def export_training_datasets(
    output_dir: Optional[str] = None,
    format_type: str = "chatml"
) -> Dict[str, Any]:
    """
    Exports all 4 training tasks into fine-tuning ready JSONL files.
    """
    target_dir = output_dir or CONFIG.get("output_dir", "output_datasets")
    os.makedirs(target_dir, exist_ok=True)

    # 1. Load raw datasets
    questions = load_jsonl_records("questions.jsonl", target_dir)
    concepts = load_jsonl_records("concepts.jsonl", target_dir)
    syllabus = load_jsonl_records("syllabus.jsonl", target_dir)
    flashcards = load_jsonl_records("flashcards.jsonl", target_dir)
    rubrics = load_jsonl_records("rubrics.jsonl", target_dir)

    logger.info(f"Loaded raw records: {len(questions)} questions, {len(concepts)} concepts, {len(flashcards)} flashcards.")

    # 2. Build task samples
    t1_samples = build_task1_paper_generation_samples(questions, syllabus)
    t2_samples = build_task2_topic_explanation_samples(concepts, syllabus)
    t3_samples = build_task3_answer_evaluation_samples(questions, rubrics)
    t4_samples = build_task4_flashcard_samples(flashcards, concepts)

    all_samples = t1_samples + t2_samples + t3_samples + t4_samples
    random.shuffle(all_samples)

    # 3. Format transformers
    def to_chatml(sample: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": sample["instruction"]},
                {"role": "assistant", "content": sample["output"]}
            ],
            "task": sample["task"],
            "metadata": sample.get("metadata", {})
        }

    def to_alpaca(sample: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "instruction": sample["instruction"],
            "input": sample.get("input", ""),
            "output": sample["output"],
            "system": SYSTEM_PROMPT,
            "task": sample["task"]
        }

    def to_sharegpt(sample: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "conversations": [
                {"from": "system", "value": SYSTEM_PROMPT},
                {"from": "human", "value": sample["instruction"]},
                {"from": "gpt", "value": sample["output"]}
            ],
            "task": sample["task"]
        }

    formatter = to_chatml if format_type == "chatml" else (to_alpaca if format_type == "alpaca" else to_sharegpt)

    # 4. Save individual task files & unified file
    task_files = {
        "task1_paper_gen": [formatter(s) for s in t1_samples],
        "task2_topic_explain": [formatter(s) for s in t2_samples],
        "task3_answer_eval": [formatter(s) for s in t3_samples],
        "task4_flashcards": [formatter(s) for s in t4_samples],
        "unified_sft_train": [formatter(s) for s in all_samples]
    }

    results = {}
    for name, items in task_files.items():
        fname = f"train_{name}_{format_type}.jsonl"
        fpath = os.path.join(target_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        results[name] = {"file": fname, "records": len(items)}
        logger.info(f"Saved {len(items)} training pairs to {fname}")

    return {
        "status": "SUCCESS",
        "format": format_type,
        "total_training_pairs": len(all_samples),
        "task_breakdown": results
    }

def convert_dataset_to_training(
    output_dir: str = "output_datasets",
    val_split_ratio: float = 0.1
) -> Dict[str, Any]:
    """
    Exports datasets into train and validation splits in standard messages and alpaca formats.
    Prepares instruction-tuning datasets for:
      1. Question paper generation on any topic / type
      2. Topic explanation with formulas and analogies
      3. Student answer evaluation with partial credit rubrics
      4. Active-recall flashcard deck generation
    """
    target_dir = output_dir or CONFIG.get("output_dir", "output_datasets")
    os.makedirs(target_dir, exist_ok=True)

    questions = load_jsonl_records("questions.jsonl", target_dir)
    concepts = load_jsonl_records("concepts.jsonl", target_dir)
    syllabus = load_jsonl_records("syllabus.jsonl", target_dir)
    flashcards = load_jsonl_records("flashcards.jsonl", target_dir)
    rubrics = load_jsonl_records("rubrics.jsonl", target_dir)

    t1_samples = build_task1_paper_generation_samples(questions, syllabus)
    t2_samples = build_task2_topic_explanation_samples(concepts, syllabus)
    t3_samples = build_task3_answer_evaluation_samples(questions, rubrics)
    t4_samples = build_task4_flashcard_samples(flashcards, concepts)

    all_samples = t1_samples + t2_samples + t3_samples + t4_samples
    random.shuffle(all_samples)

    val_count = max(1, int(len(all_samples) * val_split_ratio)) if len(all_samples) > 1 else 0
    val_samples = all_samples[:val_count]
    train_samples = all_samples[val_count:]

    def to_chatml(sample: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": sample["instruction"]},
                {"role": "assistant", "content": sample["output"]}
            ],
            "task": sample["task"],
            "metadata": sample.get("metadata", {})
        }

    def to_alpaca(sample: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "instruction": sample["instruction"],
            "input": sample.get("input", ""),
            "output": sample["output"],
            "system": SYSTEM_PROMPT,
            "task": sample["task"]
        }

    train_chat_path = os.path.join(target_dir, "train_sft_messages.jsonl")
    val_chat_path = os.path.join(target_dir, "val_sft_messages.jsonl")
    train_alpaca_path = os.path.join(target_dir, "train_sft_alpaca.jsonl")

    with open(train_chat_path, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(to_chatml(s), ensure_ascii=False) + "\n")

    with open(val_chat_path, "w", encoding="utf-8") as f:
        for s in val_samples:
            f.write(json.dumps(to_chatml(s), ensure_ascii=False) + "\n")

    with open(train_alpaca_path, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(to_alpaca(s), ensure_ascii=False) + "\n")

    return {
        "total_samples": len(all_samples),
        "train_samples": len(train_samples),
        "val_samples": len(val_samples),
        "train_chat_path": train_chat_path,
        "val_chat_path": val_chat_path,
        "train_alpaca_path": train_alpaca_path,
        "task_breakdown": {
            "paper_generation": len(t1_samples),
            "topic_explanation": len(t2_samples),
            "answer_evaluation": len(t3_samples),
            "flashcard_generation": len(t4_samples)
        }
    }

if __name__ == "__main__":
    report = export_training_datasets(format_type="chatml")
    print("\n" + "=" * 65)
    print("SFT TRAINING DATASET EXPORT COMPLETED")
    print("=" * 65)
    print(f"Format:                {report['format']}")
    print(f"Total Training Pairs:  {report['total_training_pairs']}")
    print("-" * 65)
    for task_name, info in report["task_breakdown"].items():
        print(f"  * {task_name:22s}: {info['records']:4d} samples -> {info['file']}")
    print("=" * 65)
