#!/usr/bin/env python3
"""AI Practice Problem Generator.

Generates personalized math and coding practice worksheets for tutoring
students with Claude, and adapts difficulty to each student's past scores.

Usage:
    python practice_gen.py generate --student Alex --subject math \
        --topic "linear equations" --difficulty auto --count 5
    python practice_gen.py record --student Alex --topic "linear equations" --score 4/5
    python practice_gen.py progress --student Alex
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.environ.get("PRACTICE_GEN_MODEL", "claude-haiku-5-5")
DIFFICULTIES = ["easy", "medium", "hard"]
STUDENTS_FILE = Path("students.json")
OUTPUT_DIR = Path("worksheets")


# ---------- student profiles ----------

def load_students(path=STUDENTS_FILE):
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def save_students(students, path=STUDENTS_FILE):
    with path.open("w") as f:
        json.dump(students, f, indent=2)


def parse_score(score):
    """Turn '4/5' into 0.8. Raises ValueError on bad input."""
    match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", score)
    if not match:
        raise ValueError(f"Score must look like 4/5, got {score!r}")
    correct, total = int(match.group(1)), int(match.group(2))
    if total == 0 or correct > total:
        raise ValueError(f"Invalid score {score!r}")
    return correct / total


def record_score(students, student, topic, score, difficulty="medium"):
    profile = students.setdefault(student, {"history": []})
    profile["history"].append({
        "topic": topic,
        "score": round(parse_score(score), 2),
        "difficulty": difficulty,
        "date": date.today().isoformat(),
    })
    return students


def pick_difficulty(students, student, topic):
    """Adaptive difficulty: move up after >= 80%, down after < 50%."""
    history = [h for h in students.get(student, {}).get("history", [])
               if h["topic"].lower() == topic.lower()]
    if not history:
        return "medium"
    last = history[-1]
    level = DIFFICULTIES.index(last.get("difficulty", "medium"))
    if last["score"] >= 0.8:
        level = min(level + 1, len(DIFFICULTIES) - 1)
    elif last["score"] < 0.5:
        level = max(level - 1, 0)
    return DIFFICULTIES[level]


def weak_topics(students, student, threshold=0.6):
    """Topics whose latest score is below the threshold."""
    latest = {}
    for h in students.get(student, {}).get("history", []):
        latest[h["topic"]] = h["score"]
    return sorted(t for t, s in latest.items() if s < threshold)


# ---------- prompt + API ----------

def build_prompt(subject, topic, difficulty, count, weak=None):
    focus = ""
    if weak:
        focus = (" The student has struggled with: " + ", ".join(weak)
                 + ". Where it fits naturally, reinforce those skills.")
    return (
        f"Create {count} {difficulty} {subject} practice problems on '{topic}' "
        f"for a tutoring student.{focus} Each problem should build on the last. "
        "Return ONLY a JSON array where each item has the keys "
        '"question", "answer" and "explanation" (a short step-by-step solution). '
        "For coding problems, put any code inside the strings."
    )


def call_claude(prompt, model=DEFAULT_MODEL, api_key=None):
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Set ANTHROPIC_API_KEY first (or use --dry-run).")
    body = json.dumps({
        "model": model,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}: {e.read().decode()[:300]}")
    return "".join(b.get("text", "") for b in data.get("content", []))


def parse_problems(text):
    """Pull the JSON array out of the model's reply, even if wrapped in prose."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in the response")
    problems = json.loads(match.group(0))
    for p in problems:
        missing = {"question", "answer", "explanation"} - p.keys()
        if missing:
            raise ValueError(f"Problem missing keys: {sorted(missing)}")
    return problems


# ---------- output ----------

def render_worksheet(student, topic, difficulty, problems):
    lines = [f"# {topic.title()} practice for {student}",
             f"Difficulty: {difficulty} | {date.today().isoformat()}", ""]
    for i, p in enumerate(problems, 1):
        lines += [f"**{i}.** {p['question']}", ""]
    return "\n".join(lines)


def render_answer_key(student, topic, problems):
    lines = [f"# Answer key: {topic.title()} ({student})", ""]
    for i, p in enumerate(problems, 1):
        lines += [f"**{i}. Answer:** {p['answer']}", "",
                  f"{p['explanation']}", ""]
    return "\n".join(lines)


def save_worksheet(student, topic, worksheet, key, out_dir=OUTPUT_DIR):
    out_dir.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", f"{student}-{topic}".lower()).strip("-")
    stamp = date.today().isoformat()
    ws_path = out_dir / f"{slug}-{stamp}.md"
    key_path = out_dir / f"{slug}-{stamp}-answers.md"
    ws_path.write_text(worksheet)
    key_path.write_text(key)
    return ws_path, key_path


# ---------- CLI ----------

def cmd_generate(args):
    students = load_students()
    difficulty = (pick_difficulty(students, args.student, args.topic)
                  if args.difficulty == "auto" else args.difficulty)
    weak = [t for t in weak_topics(students, args.student) if t != args.topic]
    prompt = build_prompt(args.subject, args.topic, difficulty, args.count, weak)
    if args.dry_run:
        print(f"[dry run] difficulty={difficulty}\n{prompt}")
        return
    problems = parse_problems(call_claude(prompt))
    ws, key = save_worksheet(
        args.student, args.topic,
        render_worksheet(args.student, args.topic, difficulty, problems),
        render_answer_key(args.student, args.topic, problems))
    print(f"Saved {len(problems)} {difficulty} problems:\n  {ws}\n  {key}")


def cmd_record(args):
    students = record_score(load_students(), args.student, args.topic,
                            args.score, args.difficulty)
    save_students(students)
    print(f"Recorded {args.score} on {args.topic} for {args.student}. "
          f"Next difficulty: {pick_difficulty(students, args.student, args.topic)}")


def cmd_progress(args):
    history = load_students().get(args.student, {}).get("history", [])
    if not history:
        print(f"No history for {args.student} yet.")
        return
    for h in history:
        print(f"{h['date']}  {h['topic']:<25} {h['difficulty']:<7} {h['score']:.0%}")
    weak = weak_topics(load_students(), args.student)
    print("Needs work: " + (", ".join(weak) if weak else "nothing flagged"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="Create a worksheet and answer key")
    g.add_argument("--student", required=True)
    g.add_argument("--subject", choices=["math", "coding"], required=True)
    g.add_argument("--topic", required=True)
    g.add_argument("--difficulty", choices=DIFFICULTIES + ["auto"], default="auto")
    g.add_argument("--count", type=int, default=5)
    g.add_argument("--dry-run", action="store_true",
                   help="Show the prompt without calling the API")
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("record", help="Log a student's score")
    r.add_argument("--student", required=True)
    r.add_argument("--topic", required=True)
    r.add_argument("--score", required=True, help="e.g. 4/5")
    r.add_argument("--difficulty", choices=DIFFICULTIES, default="medium")
    r.set_defaults(func=cmd_record)

    p = sub.add_parser("progress", help="Show a student's history")
    p.add_argument("--student", required=True)
    p.set_defaults(func=cmd_progress)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
