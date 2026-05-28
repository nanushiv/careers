# Deploying CareerOS

## Frontend → Vercel (5 minutes, free)

### Option A — Vercel Dashboard (easiest)
1. Push code to GitHub
2. Go to vercel.com → "Add New Project"
3. Import your GitHub repo → select `frontend` as root directory
4. Add environment variables:
   ```
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
   CLERK_SECRET_KEY=sk_live_...
   NEXT_PUBLIC_API_URL=https://careeros-api.fly.dev
   ```
5. Click Deploy → done ✅

Your feedback page will be live at:
`https://your-project.vercel.app/feedback`

### Option B — Vercel CLI
```bash
cd frontend
npm i -g vercel
vercel login
vercel --prod
```

---

## Backend → Fly.io (10 minutes, ~$3/mo)

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# From backend directory
cd backend
fly launch --name careeros-api --region sin --no-deploy

# Set all secrets from your .env
fly secrets set \
  DATABASE_URL="postgresql+asyncpg://..." \
  SUPABASE_URL="https://..." \
  SUPABASE_SERVICE_ROLE_KEY="eyJ..." \
  CLERK_SECRET_KEY="sk_live_..." \
  GEMINI_API_KEY="AIza..." \
  REDIS_URL="rediss://..."

# Deploy
fly deploy
```

Backend live at: `https://careeros-api.fly.dev`
Swagger docs at: `https://careeros-api.fly.dev/docs`

---

## After Deploy — Update Clerk

In Clerk dashboard → Domains:
- Add your Vercel URL as allowed domain
- Update webhook URL to: `https://careeros-api.fly.dev/v1/webhooks/clerk`

---

## Sharing on LinkedIn

Share this link in comments (not in post body):
`https://your-project.vercel.app/feedback`

Use post templates in `LINKEDIN_POSTS.md`

---

## Monitor Responses

```bash
# Check feedback summary
curl https://careeros-api.fly.dev/v1/feedback/summary
```
