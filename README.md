# AI Practice Problem Generator

A Python command-line tool I built for my tutoring students. It uses Claude to generate personalized math and coding practice worksheets, with a separate answer key, and adjusts the difficulty based on each student's past scores.

## Why I built it

I tutor math and coding. Writing fresh practice problems for every student at the right level took more time than the sessions themselves. This tool does it in seconds and keeps track of who needs help with what.

## Try it

**Live demo:** _link coming soon_

Or run the web app locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Without an API key the web app runs in demo mode with a sample worksheet; the adaptive difficulty logic still runs for real.

## Features

- **Personalized worksheets:** problems on any math or coding topic, saved as a worksheet plus an answer key with step-by-step explanations
- **Adaptive difficulty:** moves a student up a level after scoring 80%+ and down after scoring under 50%
- **Weak-spot reinforcement:** topics where a student scored under 60% get worked into new problem sets
- **Progress tracking:** each student's score history is saved locally
- **Web app and CLI:** a Streamlit interface for anyone to try, plus a command-line tool with zero dependencies

## Setup

```bash
export ANTHROPIC_API_KEY=your-key-here
```

## Usage

```bash
# Generate 5 problems at the right level for this student
python practice_gen.py generate --student Alex --subject math --topic "linear equations"

# Log how they did
python practice_gen.py record --student Alex --topic "linear equations" --score 4/5

# See their history and weak spots
python practice_gen.py progress --student Alex

# Preview the prompt without calling the API
python practice_gen.py generate --student Alex --subject coding --topic "for loops" --dry-run
```

## Tests

```bash
python -m unittest
```
