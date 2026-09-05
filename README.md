TRACK_ID=PS06

# Transaction Risk Investigation Assistant (NexusTiq24 PS06)

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

4. **Single-Command Startup**:
   - Both FastAPI REST endpoints and the interactive glassmorphism Web Dashboard serve directly from `app.py` on port `8000`.

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
*(Note: If `GEMINI_API_KEY` is not set, the app gracefully uses its built-in deterministic report generator without failing.)*

### 3. Run Application
```bash
python app.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the Fraud Desk Assistant portal.

---

## 📊 Generated Synthetic Customer Datasets (`data/`)

The repository includes three realistic multi-month transaction histories generated under `data/`:

| Customer ID | Name | Risk Profile | Planted Signals / Behavior |
| :--- | :--- | :--- | :--- |
| **`CUST-1001`** | Sarah Jenkins | **Clean / Routine** | 98 routine transactions (salary, rent, groceries, coffee). **0 rules triggered** (`ATTENTION NEEDED: NO`). |
| **`CUST-1002`** | Marcus Vance | **High Risk Anomalous** | Outgoing wire transfer of \$9,500.00 (6.8x historical 90th percentile `TXN-88219`), burst of rapid P2P payments to unfamiliar payee `CryptoVault Exchange` (`TXN-88220`, `TXN-88221`, `TXN-88222`), and odd-hours activity (03:14 AM - 04:05 AM). |
| **`CUST-1003`** | Elena Rostova | **Borderline / Ambiguous** | Slightly elevated annual insurance renewal payment (\$1,450 vs \$180 regular shopping) executed at 00:45 AM. Demonstrates system restraint (Low Risk Score / `ATTENTION NEEDED: NO`). |

---

## ⚙️ Deterministic Risk Rules (`src/rules/engine.py`)

- **`RULE_LARGE_TRANSFER`**: Flags transfers > 3.0x customer's historical 90th percentile and > 2.5x baseline maximum.
- **`RULE_PAYEE_BURST`**: Flags payees first seen within 14 days receiving ≥ 2 payments in 48 hours or total sum ≥ \$2,000.
- **`RULE_ODD_HOURS`**: Flags high-value (≥ \$500) or high-risk channel transactions executed between 01:00 AM and 05:00 AM.
- **`RULE_PATTERN_BREAK`**: Flags velocity bursts (≥ 3 txns in 30 mins) or unprecedented high-risk channel usage (e.g. Wire Transfer).

---

## 🧪 Running Unit Tests

Run the complete test suite (13 unit tests covering rule logic, clean customer, anomalous customer, narrative fallback, and edge cases):
```bash
python -m pytest src/
```

---

## 📹 Demo Video Link

- **Demo Video**: [Link to 2-minute Walkthrough Video](https://youtube.com) *(Placeholder for hackathon submission)*
