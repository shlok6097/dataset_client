import json
import sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def inspect_last_10():
    print("=" * 70)
    print("INSPECTING LAST 10 GENERATED DATAPOINTS (questions.jsonl)")
    print("=" * 70)
    
    with open("output_datasets/questions.jsonl", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    total = len(lines)
    last_10 = lines[-10:] if total >= 10 else lines
    
    for i, line in enumerate(last_10):
        rec_num = total - len(last_10) + i + 1
        data = json.loads(line)
        print(f"\n--- Datapoint #{rec_num} ---")
        print(f"Board:         {data.get('board')}")
        print(f"Class:         {data.get('class')}")
        print(f"Subject:       {data.get('subject')}")
        print(f"Chapter:       {data.get('chapter')}")
        print(f"Question Type: {data.get('question_type')}")
        print(f"Marks:         {data.get('marks_weightage')}")
        print(f"Difficulty:    {data.get('difficulty')}")
        print(f"Question:      {data.get('seed_question')}")
        if data.get('options'):
            print(f"Options:       {data.get('options')}")
        ans = data.get('answer_key') or data.get('expected_answer')
        print(f"Answer:        {ans}")
        rubric = data.get('rubric_keywords') or data.get('marking_scheme')
        print(f"Rubric/Kws:    {rubric}")

if __name__ == "__main__":
    inspect_last_10()
