# 🎣 Fishing Copilot

**Should I go fishing right now — and what should I do to maximize success?**

Fishing Copilot answers that in one glance: a **GO / OPTIONAL / DON'T GO**
decision, a success probability, the best time windows for the day, an
AI-generated plan, and a plain-language *why*. It learns from your logged
catches and gets more accurate over time — that data flywheel is the moat.

This is a real, runnable full-stack system, kept deliberately simple: a single
backend service, a shared domain core, an ML pipeline, and an Expo mobile app.

---

## Architecture

```
                ┌──────────────────────────┐
                │  Mobile app (Expo / RN)   │   Home · Plan · Log
                └─────────────┬────────────┘
                              │ REST
                ┌─────────────▼────────────┐
                │  Backend (FastAPI)        │   /decision /plan /log /history
                │                           │   /session/start /train /model/info
                │  weather → features →     │
                │  ML inference → decision  │
                │  → LLM explanation/plan   │
                └───┬───────────┬───────────┘
                    │           │
        ┌───────────▼──┐   ┌────▼─────────┐
        │  core/       │   │  ml/         │
        │  features    │   │  dataset     │
        │  rules       │   │  train       │
        │  moon        │   │  inference   │
        │  decision    │   └────┬─────────┘
        └──────────────┘        │  reads/writes
                    ┌───────────▼───────────┐
                    │  Data layer (SQLite/PG)│  users, sessions,
                    │                        │  weather_snapshots, catches
                    └────────────────────────┘
```

| Directory  | What it is |
|------------|------------|
| `core/`    | Shared, dependency-light domain logic: feature engineering, rule engine, moon phase, decision engine. **Used identically by the backend and the ML trainer** — that's what keeps training and inference consistent. |
| `ml/`      | ML pipeline: build a dataset from sessions, train + evaluate, persist an artifact, and serve predictions with a graceful no-model fallback. |
| `backend/` | FastAPI monolith: serves predictions, stores data, fetches weather + moon, runs inference, calls the LLM, triggers training. |
| `mobile/`  | Expo (React Native) app: Home, Plan, and Log screens. |
| `scripts/` | The nightly training job (the flywheel). |

---

## How a decision is made

1. **Weather** is fetched from [Open-Meteo](https://open-meteo.com) (free, no key)
   for the location, including a short recent window so we can measure a
   **pressure trend**. Results are cached per location/hour. **Moon phase** is
   computed locally (no API).
2. **Features** are engineered from that context: hour of day, pressure trend,
   wind speed, temperature delta, rain flag, moon illumination, solunar
   strength, season, day of week, location hash.
3. **ML inference** produces a success probability — *if* a model is trained.
4. **Rule engine** independently scores conditions (pressure + wind + time of
   day + temperature + moon − rain), 0–100.
5. **Decision engine** blends them:
   `final_score = 0.7·(ML_prob·100) + 0.3·rule_score`, then maps to
   **GO (70–100) / OPTIONAL (41–69) / DON'T GO (0–40)**. With no model yet, it
   falls back entirely to the rule score, so the product works on day one.
6. **LLM layer** (Claude) writes a one-line explanation and, on request, a full
   fishing plan. Without an API key it uses solid deterministic templates.

---

## Quick start

### 1. Backend + ML (Python 3.11+)

```bash
# from the repository root
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# (optional) train a cold-start model on synthetic data so predictions are
# "personalised" immediately — otherwise the rule engine is used until you've
# logged enough real sessions.
python -m ml.train --synthetic 600

# run the API (must be from the repo root so `core` and `ml` import)
uvicorn backend.app.main:app --reload
```

The API is now at **http://localhost:8000** — interactive docs at
**http://localhost:8000/docs**.

Try it:

```bash
curl "http://localhost:8000/decision?location=Lake%20Tahoe"
curl "http://localhost:8000/decision?location=39.09,-120.03"   # lat,lon works too
```

> **AI plans/explanations:** set `ANTHROPIC_API_KEY` (copy `backend/.env.example`
> to `backend/.env`) to use Claude (`claude-opus-4-8`). Without it, the app
> returns well-structured template plans — everything still works.

#### Run with Docker instead

```bash
docker build -f backend/Dockerfile -t fishing-copilot .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... fishing-copilot
```

### 2. Mobile app (Expo)

```bash
cd mobile
npm install
npm start          # then press i / a, or scan the QR code with Expo Go
```

Point the app at your backend by editing `extra.apiBaseUrl` in
`mobile/app.json` (use your machine's LAN IP for a physical device, e.g.
`http://192.168.1.50:8000`).

---

## API reference

| Method | Path              | Purpose |
|--------|-------------------|---------|
| `GET`  | `/decision`       | GO/OPTIONAL/DON'T GO + probability + explanation + time windows. Query: `location`. |
| `POST` | `/plan`           | AI fishing plan. Body: `location`, `fishing_type`, `skill_level`. |
| `POST` | `/log`            | Record a catch result. Body: `session_id`, `result` (`caught`/`no_bite`), `bait?`, `notes?`. |
| `GET`  | `/history`        | A user's past sessions + catches. Query: `user_id`. |
| `POST` | `/session/start`  | Open a session (the app calls this on launch). Body: `location`, `user_id?`. |
| `POST` | `/train`          | Kick off retraining from logged sessions (background). |
| `GET`  | `/model/info`     | Whether a model is loaded + its metrics. |
| `GET`  | `/health`         | Liveness check. |

---

## Data model (ML-ready)

`users` · `sessions` · `weather_snapshots` · `catches` — flat and append-only so
the trainer can replay history cleanly. SQLite by default; point
`DATABASE_URL` at Postgres for production (e.g.
`postgresql+psycopg://user:pass@host/db`).

---

## The data flywheel

1. User sees a prediction → 2. goes fishing → 3. logs the result via `/log` →
4. the outcome is stored → 5. the model is retrained (nightly or via `/train`).

```bash
# schedule nightly (the artifact hot-reloads into the running API)
0 3 * * *  /path/to/repo/scripts/nightly_train.sh
```

The trainer uses scikit-learn's `GradientBoostingClassifier` (with a
`LogisticRegression` fallback for small datasets). Pass `--model xgboost` after
`pip install xgboost` to use XGBoost instead.

---

## Tech notes & deliberate simplifications

- **One service, modular code.** No microservices; `core` is shared by the API
  and the trainer so features are computed identically in both.
- **Graceful degradation everywhere.** No model → rule engine. No LLM key →
  template plans. No recent weather → neutral defaults. The app is always usable.
- **Voice notes** in the Log screen are captured as text notes in this version;
  audio recording (via `expo-av`) is a natural next step and the schema already
  has a free-form `notes` field for it.
- **Auth** is intentionally minimal — an anonymous `user_id` is created on first
  launch and stored on-device. Add real auth before going to production.
