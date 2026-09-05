TRACK_ID=PS06

# Production-Grade Transaction Risk Investigation Assistant (NexusTiq24 PS06)

An intelligent, deterministic-first investigation assistant for a bank's fraud desk. Built for Track **PS06 — Transaction Risk Investigation Assistant (Banking)**.

---

## 🌟 Key Architectural Features

1. **Clear Separation of Concerns**:
   - **Pure-Python Rule Engine (`src/rules/`)**: 100% deterministic risk rules (no LLM calls) evaluating unusually large transfers, unfamiliar payee bursts, odd-hours activity, and established pattern breaks. Fully unit-tested.
   - **Grounded Narrative Layer (`src/llm/`)**: Gemini LLM layer that takes ONLY deterministic findings + minimal raw transaction context. It narrating/explaining what the rule engine found. It **NEVER** decides suspicion, **NEVER** declares that fraud occurred, and **NEVER** hallucinates transaction IDs.

2. **Headline First Finding**:
   - The VERY FIRST line of every investigation report plainly states:
     - `ATTENTION NEEDED: YES` (for flagged accounts with cited transactions)
     - `ATTENTION NEEDED: NO` (for routine accounts, stopping cleanly without manufacturing suspicion)

3. **100% Offline & Resilience Guarantee**:
   - Every Gemini LLM call is wrapped in a `try/except` handler with an automatic, high-quality **deterministic template fallback**. If `GEMINI_API_KEY` is omitted, offline, or times out, the system seamlessly outputs a structured investigation report directly from the rule findings.

4. **Runtime API Key Override (Settings UI)**:
   - Users can paste a Gemini API key at runtime in the Settings modal.
   - **Security**: Key is stored **in memory only for the session** — never written to disk, never logged, and never committed.
   - The UI shows real-time status indicators: `🟢 Key Active (Session Override)`, `🟢 Key Active (Environment Variable)`, or `⚪ No Key (Rule Fallback)`.

5. **Single-Command Startup**:
   - Both FastAPI REST endpoints and the interactive SPA Web Dashboard serve directly from `app.py` on port `8000`.

---

## 🚀 Quick Start Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variable (Optional)
Set your Gemini API key:
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key-here"

# Linux / macOS
export GEMINI_API_KEY="your-gemini-api-key-here"
```
*(Note: If `GEMINI_API_KEY` is not set, you can paste a key in the Settings UI at runtime, or let the app use its built-in deterministic report generator without failing.)*

### 3. Run Application
```bash
python app.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the Fraud Desk Assistant portal.

---

## 📊 Generated Synthetic Customer Datasets (`data/`)

The repository includes realistic multi-month transaction histories committed under `data/` in both **JSON** and **CSV** formats:

| Customer ID | Name | Risk Profile | Planted Signals / Behavior |
| :--- | :--- | :--- | :--- |
| **`CUST-1001`** | Sarah Jenkins | **Clean / Routine** | 98 routine transactions (salary, rent, groceries, coffee). **0 rules triggered** (`ATTENTION NEEDED: NO`). |
| **`CUST-1002`** | Marcus Vance | **High Risk Anomalous** | Outgoing wire transfer of ₹9,50,000.00 (6.8x historical 90th percentile `TXN-88219`), burst of rapid IMPS payments to unfamiliar payee `CryptoVault Exchange India` (`TXN-88220`, `TXN-88221`, `TXN-88222`), and odd-hours activity (03:14 AM - 04:05 AM). |
| **`CUST-1003`** | Elena Rostova | **Borderline / Ambiguous** | Slightly elevated annual insurance renewal payment (₹45,000 vs ₹6,500 regular shopping) executed at 00:45 AM. Demonstrates system restraint (`ATTENTION NEEDED: NO`). |

---

## ⚙️ Deterministic Risk Rules (`src/rules/engine.py`)

- **`RULE_LARGE_TRANSFER`**: Flags transfers > 3.0x customer's historical 90th percentile and > 2.5x baseline maximum.
- **`RULE_PAYEE_BURST`**: Flags payees first seen within 14 days receiving ≥ 2 payments in 48 hours or total sum ≥ ₹1,50,000.00.
- **`RULE_ODD_HOURS`**: Flags high-value (≥ ₹25,000.00) or high-risk channel transactions executed between 01:00 AM and 05:00 AM.
- **`RULE_PATTERN_BREAK`**: Flags velocity bursts (≥ 3 txns in 30 mins) or unprecedented high-risk channel usage (e.g. Wire Transfer / Crypto).

---

## 🧪 Running Unit & Integration Tests

Run the complete test suite (20 unit & integration tests covering rules, API endpoints, mock LLM failure fallback, file upload, and edge cases):
```bash
python -m pytest tests/
```

---

## 💻 Tech Stack
- **Backend**: Python 3.11, FastAPI, Uvicorn, Pydantic, Google Gemini API (`google-genai` SDK), Pytest, HTTPX.
- **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism Dark Mode), JavaScript (ES6+ SPA architecture).
