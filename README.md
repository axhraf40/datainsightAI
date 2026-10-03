# DataInsight AI

**Chat with your data.** Upload a CSV or Excel file, ask questions in plain language, and get answers, charts and PDF reports — powered by Llama 3 (via Groq) and a lightweight RAG layer tuned for e-commerce datasets.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=black)
![Groq](https://img.shields.io/badge/LLM-Llama%203%20on%20Groq-F55036)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Natural-language data analysis** — questions are turned into pandas code by the LLM, executed in a sandboxed step, and explained back in plain language.
- **Adaptive RAG for e-commerce** — on upload, columns are semantically mapped (category, region, gender, shipping, date, amount…) against a knowledge base, and the model gets that context injected into its prompt. Suggested questions are generated for each dataset.
- **Automatic charts** — matplotlib / seaborn visualizations when a question calls for one.
- **PDF reports** — one-click summary report with key insights (ReportLab).
- **Automatic data cleaning** — type inference, missing values, duplicates.
- **Model fallback chain** — automatically switches Groq models on rate limits (429) or deprecated models.
- **User accounts** — sign up, log in, password reset, bcrypt-hashed passwords, browser-bound sessions.
- **Per-user workspace** — each user's datasets, conversations and generated charts are stored in SQLite.
- **Two front-ends** — a Streamlit app, and an optional React + FastAPI version.

## Architecture

```
            ┌──────────────────┐        ┌───────────────────────┐
  Browser ─►│  Streamlit app   │        │  React frontend (opt.)│
            │     app.py       │        │  frontend/  (Vite)    │
            └────────┬─────────┘        └──────────┬────────────┘
                     │                             │ /api
                     │                   ┌─────────▼────────┐
                     │                   │  FastAPI  api.py │
                     │                   └─────────┬────────┘
                     ▼                             ▼
     ┌──────────────────────────────────────────────────────────┐
     │  data_analyst.py   LLM → pandas code → execute → explain │
     │  rag/              column mapping + suggested questions  │
     │  data_cleaner.py   automatic cleaning                    │
     │  pdf_report.py     PDF export                            │
     │  auth.py / database.py   users, files, chats (SQLite)    │
     └──────────────────────────┬───────────────────────────────┘
                                ▼
                       Groq API (Llama 3)
```

## Tech stack

| Layer | Tools |
|---|---|
| LLM | Groq API — `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` (with fallback) |
| Data | pandas, scikit-learn, openpyxl |
| Visualization | matplotlib, seaborn |
| Web UI | Streamlit · React + TypeScript + TanStack + Tailwind + shadcn/ui |
| Backend API | FastAPI, Uvicorn |
| Storage & auth | SQLite, bcrypt |
| Reports | ReportLab |

## Getting started

### 1. Clone and install

```bash
git clone https://github.com/axhraf40/datainsightAI.git
cd datainsightAI
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your API key

Get a free key at [console.groq.com](https://console.groq.com/keys), then:

```bash
cp .env.example .env
# edit .env and set GROQ_API_KEY
```

### 3. Run the Streamlit app

```bash
streamlit run app.py
```

Open http://localhost:8501, create an account, upload a dataset and start asking questions.

### Optional: React frontend + FastAPI

```bash
# terminal 1 — API on :8000
uvicorn api:app --reload --port 8000

# terminal 2 — frontend (proxies /api to :8000)
cd frontend
bun install        # or: npm install
bun run dev        # or: npm run dev
```

## Example questions

- *"What are the top 5 product categories by revenue?"*
- *"Show monthly sales as a line chart."*
- *"Compare average order value between men and women."*
- *"Which states have the slowest shipping?"*
- *"Generate a PDF report of this dataset."*

## Project structure

```
├── app.py               # Streamlit UI
├── api.py               # FastAPI REST backend (for the React UI)
├── data_analyst.py      # LLM engine: code generation, execution, explanations
├── data_cleaner.py      # Automatic dataset cleaning
├── dataset_loader.py    # CSV / Excel loading
├── pdf_report.py        # PDF report generation
├── auth.py              # Sign up / login / logout / password reset
├── browser_auth.py      # Browser-bound session handling
├── database.py          # SQLite schema and queries
├── ui_styles.py         # Streamlit custom styling
├── rag/
│   ├── knowledge_base.json  # E-commerce semantic knowledge base
│   └── rag_engine.py        # Column mapping + suggested questions
├── frontend/            # Optional React + TypeScript UI
└── .streamlit/          # Streamlit theme config
```

The SQLite database is created automatically in `data/app.db` on first run (git-ignored).

## Security notes

- API keys are read from environment variables only — never commit your `.env`.
- Passwords are hashed with bcrypt.
- In development mode, the password-reset code is displayed on screen instead of being emailed.

## License

[MIT](LICENSE)
