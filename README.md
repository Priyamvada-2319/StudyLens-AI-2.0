# StudyLens AI 2.0


## Features

- Preparation domain selector (JEE, SAT, ACT, IELTS, NEET, Boards, UPSC, NDA, and custom)
- Exam-labelled diagnostic quizzes, easy/intermediate/hard questions from a limited prechecked bank
- Confidence-aware four-quadrant diagnostic
- Topic accuracy, number attempted, history, and charts
- N-day rule-based study plan
- Flashcard creation and simple interval-based review
- Revision tracker
- Learning micro-reels
- Same-score statistical learning-profile demonstration
- Extract text from PDF, DOCX, TXT/MD to create **source recall** cards
- Optional **local** Ollama model for new question generation and free-form concept explanations

**Scope disclosure:** The no-key cloud version does not generate unlimited novel MCQs for arbitrary exams. Its public question bank is intentionally limited, and the exam selector does not imply official exam-pattern compliance. Resource-based MCQs and free-form coaching require a local model. PDFs need extractable text; audio/video lectures require a transcript.

## GitHub and Streamlit Community Cloud

Repository root files: `app.py`, `requirements.txt`, `README.md` and the `core/` directory.

1. Push the folder contents into a GitHub repository (preserve `core/`).
2. Open https://share.streamlit.io and choose **Create app**.
3. Select your repository, `main` branch, and `app.py` as the main path.
4. Deploy. **No secrets or key required** for the curated-bank mode.

## Run on Mac / Windows

Python 3.10+ (version compatible with requirements).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, replace Python invocation with `py` as needed, and use `.venv\Scripts\python.exe -m pip install -r requirements.txt` followed by `.venv\Scripts\python.exe -m streamlit run app.py`.

## Optional local AI without a provider key

Install Ollama on your own Mac or Windows computer from https://ollama.com and run:

```bash
ollama pull llama3.2:3b
ollama serve
```

If Ollama is already running in the background, you don't need to start `serve` again. Run Streamlit **on that same computer** and select the local AI mode. This does not power the publicly hosted Streamlit Cloud deployment.

## Privacy and limitations

The public prototype uses a local SQLite database (`studylens_demo.db`). It is **not** suitable for real student data because there is no authentication, demo identifiers are guessable, and cloud storage is ephemeral. Use fictional IDs only. No uploads are sent to an external AI provider by the cloud demo. Avoid copyrighted uploads you lack rights to process or redistribute. AI model generations are not academically verified. Study schedule and quadrant recommendations are transparent heuristics, not validated educational predictions.
# StudyLens-AI-2.0
