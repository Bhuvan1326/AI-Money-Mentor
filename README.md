# AI Money Mentor

Personal financial planning web app for the **ET AI Hackathon**: calculators, India-focused tax education, portfolio charts, and a **rule-based on-device “AI” advisor** — built with **Python** and **Streamlit** (no external LLM or API keys).

## Features

- **Profile inputs**: age, income, expenses, savings, SIPs, EMI, goals (house / car / retirement / emergency)
- **Money health score** (0–100) with actionable tips
- **SIP calculator** (future value, gains)
- **Retirement corpus** estimate and **FIRE** number with rough years-to-FIRE
- **Emergency fund** target and gap
- **Risk profile** (low / medium / high) with equity range hints
- **India tax-saving pointers** (80C, NPS, 80D, etc.) — educational, not professional advice
- **Monthly surplus allocation** breakdown
- **Plotly charts**: wealth projection, SIP horizons, portfolio scenarios, savings analysis
- **AI advisor** (`offline_ai.py`): chat, 12-month plan, simple explanations — **fully offline**
- **Couple Mode**: Partner A + B inputs → combined household profile, joint health score, couple risk rules, income-split pie, joint goals, combined budget & retirement tabs

## Setup

```bash
cd ai-money-mentor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Open the URL shown in the terminal (usually `http://localhost:8501`).

## Project layout

| File | Role |
|------|------|
| `app.py` | Streamlit UI: sidebar, tabs, charts, chat |
| `financial_calculator.py` | SIP, retirement, FIRE, health score, risk, tax list, goals |
| `offline_ai.py` | Rule-based advisor (intent + profile logic) |
| `ai_advisor.py` | Thin facade re-exporting `offline_ai` |
| `charts.py` | Plotly figures |
| `financial_score.py` | Money health 0–100 (savings, emergency, invest, debt) |
| `risk_profile.py` | Conservative / Moderate / Aggressive + equity/debt/gold template |
| `goal_planner.py` | Goal-based SIP & FV |
| `fire_calculator.py` | FIRE corpus = expenses×25×12, timeline, bridge SIP |
| `wealth_projection.py` | Multi-horizon paths @ fixed CAGR |
| `budget_engine.py` | 50/30/20 budget table & vs-actual insights |
| `expense_analyzer.py` | Overspend / EMI / savings flags |
| `personality.py` | Saver / Spender / Investor heuristic |
| `joint_calculator.py` | Merge partners → one `UserFinancialProfile` + household meta |
| `couple_mode.py` | Couple risk heuristics + `CoupleAdviceBundle` for the offline advisor |
| `couple_planner.py` | Joint milestones (house / education / retirement corpus SIPs) |
| `utils.py` | Formatting and helpers |

## Disclaimer

This app is for **education and hackathon demonstration** only. It is **not** investment, tax, or legal advice. Consult a SEBI-registered investment adviser and a qualified chartered accountant for decisions suited to your situation.
