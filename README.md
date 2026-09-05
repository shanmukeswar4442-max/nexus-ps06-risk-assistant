TRACK_ID=PS06

# Production-Grade Transaction Risk Investigation Assistant (NexusTiq24 PS06)

An intelligent, deterministic-first investigation assistant for a bank's fraud desk.

## Overview
This assistant processes multi-month customer transaction histories, evaluates activity against deterministic risk rules (unusually large transfers, unfamiliar payee bursts, odd-hours activity, established pattern breaks), and generates grounded narrative reports using Gemini LLM.

## Quick Start
```bash
pip install -r requirements.txt
python app.py
```
App starts serving on `http://localhost:8000`.

## Features
- **Deterministic Risk Engine (`src/rules/`)**: Pure Python engine (zero LLM calls) calculating structured findings and historical baselines.
- **Grounded LLM Narrator (`src/llm/`)**: Gemini LLM layer synthesizing reports strictly grounded in rule findings.
- **Runtime API Key Overrides**: Paste session API keys in the Settings UI without saving to disk or logs.
- **Interactive SPA Dashboard (`static/`)**: Real-time customer status chips, citation highlighting, report export, CSV/JSON upload, and real-time transaction entry.

## Environment Variables
- `GEMINI_API_KEY`: Default API key for Gemini LLM. Can be overridden at runtime via the Settings UI.
