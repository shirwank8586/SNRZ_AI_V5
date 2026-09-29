# SNRZ AI V5 — Mobile-Friendly GitHub Root

This package keeps the deployable files in the repository root so it is easier to upload from an iPhone.

## Files
- `app.py` — FastAPI app
- `market.py` — Twelve Data XAU/USD adapter
- `snrz_engine.py` — SNRZ-only analysis engine
- `index.html` — dashboard
- `RULEBOOK.md` — SNRZ rulebook
- `requirements.txt` — Python dependencies
- `.env.example` — environment variable template

## Run
`uvicorn app:app --host 0.0.0.0 --port $PORT`

Set `TWELVE_DATA_API_KEY` on the server. Do not put real API keys in public GitHub files.

Mode: paper/educational analysis only; no live order execution.
