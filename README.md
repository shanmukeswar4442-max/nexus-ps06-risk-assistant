TRACK_ID=PS06

# Transaction Risk Investigation Assistant (NexusTiq24 PS06)

An intelligent, deterministic-first investigation assistant for banking fraud desks.

## Overview
This assistant processes multi-month customer transaction histories, evaluates activity against deterministic risk rules (unusually large transfers, unfamiliar payee bursts, odd-hours activity, established pattern breaks), and generates grounded narrative reports using Gemini LLM.

## Quick Start
```bash
pip install -r requirements.txt
python app.py
```
App will start serving on `http://localhost:8000`.

## Architecture
- `src/rules/`: Pure Python deterministic risk engine (no LLM calls)
- `src/llm/`: Gemini LLM narrative report generator with template fallback
- `src/api/`: FastAPI endpoints
- `data/`: Synthetic transaction datasets (clean, anomalous, borderline)

## Environment Variables
- `GEMINI_API_KEY`: API key for Gemini LLM. If missing or invalid, the app gracefully falls back to deterministic report templates.
