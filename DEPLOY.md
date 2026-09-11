# Deploying Panther Home Care (GitHub + Render)

This deploys three things on Render: a **PostgreSQL** database, the **Django backend**
(which also serves the full server-rendered app), and the **React frontend** (static
site). A `render.yaml` Blueprint sets all three up at once.

---

## Part 1 — Put the project on GitHub

From inside the `panther` folder (where `manage.py` is), in PowerShell:

```powershell
git init
git add .
git commit -m "Panther Home Care"
git branch -M main
```

Create a new **empty public** repo on github.com (no README/……), then:

```powershell
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

> `.gitignore` already excludes `.env`, `db.sqlite3`, `node_modules/`, and build output,
> so no secrets or heavy files get pushed. **Never commit your `.env`.**

---

## Part 2 — Deploy on Render (Blueprint)

1. Go to <https://dashboard.render.com> → **New +** → **Blueprint**.
2. Connect your GitHub account and pick this repo. Render reads `render.yaml`.
3. Click **Apply**. Render creates the database, the backend, and the frontend.
   The first build takes a few minutes (it installs deps, builds the React app,
   runs migrations, and seeds demo data).

When it finishes you'll have two URLs, e.g.:
- Backend / full app: `https://panther-backend.onrender.com`
- React frontend: `https://panther-frontend.onrender.com`

Log in with **rene / panther123**.

### If Render gave your services different URLs
Service names must be globally unique, so Render may append a suffix. If your URLs
differ from the defaults, update these env vars (each service → **Environment**), then
**Manual Deploy → Clear build cache & deploy**:
- Backend: `FRONTEND_URL` and `BACKEND_URL`
- Frontend: `VITE_API_URL` (set it to the backend URL)

---

## Part 3 — Optional keys (set in the Render dashboard, never in code)

Backend service → **Environment** → Add:

| Key            | Value                          | Enables                    |
|----------------|--------------------------------|----------------------------|
| `AI_PROVIDER`  | `anthropic`                    | LLM daily brief            |
| `AI_API_KEY`   | `sk-ant-…`                     | (your Anthropic key)       |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | from Google Cloud | Google sign-in |

Save → the service redeploys automatically.

---

## Notes
- **Free tier** sleeps after ~15 min idle; the first request then takes ~30–50 s to wake.
- The build runs `seed_demo`, which **resets to demo data on every deploy**. Once you have
  real data, remove `&& python manage.py seed_demo` from `buildCommand` in `render.yaml`.
- To create your own admin instead of the demo user, open the backend service **Shell**
  and run `python manage.py createsuperuser`.
- The backend URL alone is the complete product (dashboard, admin, PDFs, etc.). The React
  site is an optional modern SPA over the same API.
