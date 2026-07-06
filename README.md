# CareerOS 🚀
### AI-powered Career Intelligence & Job Hunt Operating System

> Tells tech professionals *exactly* why they're not getting hired — and gives them a strategic roadmap to fix it.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green)](https://supabase.com)

---

## What It Does

| Feature | Description |
|---------|-------------|
| 🎯 ATS Analyzer | Rule engine + embeddings + LLM. Scores resume vs JD, finds keyword gaps |
| 👁️ Recruiter Perception | Simulates how a real recruiter reads your resume in 30 seconds |
| 📊 PM Readiness Score | 6-dimension readiness assessment for PM/AI-PM transitions |
| 🗂️ Application Tracker | Kanban pipeline with auto follow-up reminders |
| 🧠 AI Insights | Weekly strategic insights: ghosting patterns, source performance, pivot signals |
| 📈 Analytics | Source performance, funnel conversion, resume version comparison |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TailwindCSS, TypeScript, shadcn/ui, Recharts |
| Backend | FastAPI (Python 3.11) |
| Database | Supabase (PostgreSQL + pgvector) |
| Cache | Upstash Redis |
| Auth | Clerk |
| AI | Google Gemini 1.5 Flash |
| Storage | Cloudflare R2 |
| Email | Resend |
| Payments | Razorpay |
| Hosting | Vercel (frontend) + Fly.io (backend) |

---

## Architecture

```
Resume Upload
     │
     ▼
┌─────────────────────────────────────┐
│         Analysis Pipeline           │
│                                     │
│  1. Rule Engine  (free, instant)    │
│     • Keyword extraction            │
│     • Format scoring                │
│     • ATS red flag detection        │
│                                     │
│  2. Embeddings  (cheap, ~1s)        │
│     • Semantic similarity vs JD     │
│     • pgvector cosine search        │
│                                     │
│  3. LLM Enrichment  (conditional)   │
│     • Only if rule confidence < 0.8 │
│     • Gemini 1.5 Flash              │
│     • Cost governor enforces budget │
└─────────────────────────────────────┘
     │
     ▼
Supabase Realtime → Frontend update
```

**Key design decisions:**
- Rule Engine → Embeddings → LLM order enforced everywhere (lazy AI, cost-first)
- Cache TTLs: ATS=24h, role_fit=7d, recruiter=48h, dashboard=5min
- Free tier AI budget: $0.15/month. Pro: $2.00/month
- Async jobs: trigger returns `job_id`, Supabase Realtime notifies frontend

---

## Project Structure

```
careeros/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── core/                # Config, DB, security, cache
│   │   ├── api/v1/              # Route handlers
│   │   │   ├── users.py
│   │   │   ├── resumes.py
│   │   │   ├── analyses.py
│   │   │   ├── applications.py
│   │   │   ├── insights.py
│   │   │   ├── dashboard.py
│   │   │   ├── billing.py
│   │   │   └── webhooks.py
│   │   ├── ai/                  # LLM orchestration
│   │   │   ├── llm_client.py    # Unified Gemini/OpenRouter client
│   │   │   ├── rule_engine.py   # Deterministic ATS analysis
│   │   │   ├── prompt_templates.py
│   │   │   └── cost_governor.py
│   │   ├── services/
│   │   │   ├── analysis/        # ATS, recruiter, role fit, readiness
│   │   │   ├── insights/        # Insight engine
│   │   │   ├── notifications/   # Email via Resend
│   │   │   └── analytics/       # Weekly aggregations
│   │   └── workers/             # Celery background jobs
│   └── migrations/              # SQL schema
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/           # Main dashboard
│   │   ├── resume/              # Resume vault + analysis results
│   │   ├── applications/        # Kanban pipeline
│   │   ├── intelligence/        # AI insights hub
│   │   ├── analytics/           # Charts + metrics
│   │   ├── settings/            # Profile management
│   │   ├── pricing/             # Razorpay upgrade page
│   │   └── onboarding/          # 3-step setup wizard
│   ├── components/
│   │   ├── analysis/            # ATS score, recruiter panel, gap grid
│   │   ├── applications/        # Kanban cards, add modal
│   │   └── dashboard/           # Health gauge, insight cards
│   ├── lib/api.ts               # Typed API client
│   └── stores/                  # Zustand state
│
└── infra/
    ├── docker-compose.yml
    └── fly.toml
```

---

## Quick Start (15 minutes)

### Prerequisites
- Python 3.11+, Node.js 18+
- Free accounts: [Supabase](https://supabase.com), [Clerk](https://clerk.com), [Google AI Studio](https://aistudio.google.com)

### 1. Database (Supabase)
1. Create project at supabase.com
2. SQL Editor → paste `backend/migrations/001_initial_schema.sql` → Run
3. Copy: Project URL, service_role key, anon key, DB connection string

### 2. Auth (Clerk)
1. Create app at clerk.com → Email + Google
2. Copy: Publishable key, Secret key

### 3. AI (Google AI Studio)
1. Get API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) (free)

### 4. Configure & Run

```bash
# Backend
cd backend
cp .env.local.example .env    # fill in 6 values
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
cp .env.example .env.local    # fill in Clerk keys
npm install && npm run dev
```

### 5. Open
- **App**: http://localhost:3000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

---

## API Documentation

Full interactive Swagger UI at **`http://localhost:8000/docs`**

### Key Endpoints

```
GET    /health                        Health check

# Users
GET    /v1/users/me                   Get current user
PATCH  /v1/users/me                   Update profile

# Resumes
POST   /v1/resumes/upload             Upload PDF/DOCX
GET    /v1/resumes                    List all resumes
DELETE /v1/resumes/{id}              Delete resume

# Analyses
POST   /v1/analyses                   Trigger analysis (async)
GET    /v1/analyses                   List analyses
GET    /v1/analyses/{id}             Get single analysis

# Applications
POST   /v1/applications               Log application
GET    /v1/applications               List (filterable by stage/source)
PATCH  /v1/applications/{id}         Update stage/notes
POST   /v1/applications/{id}/events  Add timeline event

# Dashboard
GET    /v1/dashboard                  Main dashboard aggregate
GET    /v1/dashboard/pipeline         Kanban + funnel data
GET    /v1/dashboard/analytics        Time-series analytics
GET    /v1/dashboard/recruiter        Recruiter intelligence

# Insights
GET    /v1/insights                   List AI insights
POST   /v1/insights/{id}/dismiss     Dismiss insight

# Billing
POST   /v1/billing/create-checkout   Razorpay checkout session
POST   /v1/billing/portal            Razorpay customer portal
```

---

## Deployment

### Backend → Fly.io
```bash
cd backend
fly launch --no-deploy
fly secrets set $(cat .env | xargs)
fly deploy
```

### Frontend → Vercel
```bash
cd frontend
vercel --prod
# Set env vars in Vercel dashboard
```

---

## Pricing

| Plan | Price | Analyses | Applications |
|------|-------|----------|-------------|
| Free | $0/mo | 3/month | 10 tracked |
| Pro  | $29/mo | Unlimited | Unlimited |

Target gross margin: ~95% at scale (AI COGS ≈ $1.53/pro user/month)

---

## License

MIT © CareerOS
