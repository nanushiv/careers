# CareerOS — Run Locally in 15 Minutes

## You need 3 accounts (all free tiers work):
1. **Supabase** — https://supabase.com (free) — database
2. **Clerk** — https://clerk.com (free) — auth
3. **Google AI Studio** — https://aistudio.google.com (free) — AI

---

## Step 1 — Supabase Setup (5 min)

1. Create a new project at supabase.com
2. Go to **SQL Editor** → paste the entire contents of `backend/migrations/001_initial_schema.sql` → **Run**
3. Go to **Project Settings → API** → copy:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY`
   - `anon` key → `SUPABASE_ANON_KEY`
4. `DATABASE_URL`: from **Settings → Database → Connection String → URI** (switch to asyncpg):
   - Replace `postgresql://` with `postgresql+asyncpg://`

---

## Step 2 — Clerk Setup (3 min)

1. Create app at clerk.com — choose Email + Google sign-in
2. From **Dashboard → API Keys** copy:
   - `Publishable key` → `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   - `Secret key` → `CLERK_SECRET_KEY`
3. For webhooks (optional for local): skip for now

---

## Step 3 — Google AI Key (1 min)

1. Go to https://aistudio.google.com/app/apikey
2. Create key → copy → `GEMINI_API_KEY`

---

## Step 4 — Configure & Run

```bash
# Backend
cd backend
cp .env.local.example .env
# Fill in: DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
#          SUPABASE_ANON_KEY, CLERK_SECRET_KEY, GEMINI_API_KEY

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend running at http://localhost:8000 — check http://localhost:8000/docs

```bash
# Frontend (new terminal)
cd frontend
cp .env.example .env.local
# Fill in: NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY

npm install
npm run dev
```

Frontend running at http://localhost:3000

---

## Step 5 — Or use Docker (easiest)

```bash
# From repo root
cp backend/.env.local.example backend/.env
cp frontend/.env.example frontend/.env.local
# Fill in env vars in both files

cd infra
docker compose up
```

All services start: API on :8000, Frontend on :3000, Redis on :6379

---

## What works out of the box

✅ Sign up / Sign in (Clerk)
✅ Upload PDF/DOCX resume (parses to text immediately)
✅ ATS Analysis (rule engine — no AI key needed for basics)
✅ ATS + Recruiter Perception with AI (needs GEMINI_API_KEY)
✅ Log applications (kanban board)
✅ Dashboard with career health score
✅ Stage pipeline tracker
✅ Follow-up reminders (auto-created on every application)

## What needs extra setup

- Email notifications: add `RESEND_API_KEY`
- File storage: add `R2_*` vars (otherwise files are memory-only)
- Background workers: `celery -A app.workers.runner worker`
- Payments: add `STRIPE_*` vars

---

## Testing the API directly

With backend running:
```bash
# Health check
curl http://localhost:8000/health

# Full API docs
open http://localhost:8000/docs
```

All endpoints are documented with request/response schemas at `/docs`.
