# Panther Home Care — Frontend (React + Vite + TypeScript)

A single-page app that consumes the Django JSON API (`/api/v1/…`). It ships alongside
the server-rendered Django UI; both talk to the same backend and database.

## Run it (two terminals)

**1. Backend** — from the project root:
```bash
python manage.py runserver          # http://localhost:8000
```

**2. Frontend** — from this `frontend/` folder:
```bash
npm install
npm run dev                         # http://localhost:5173
```

Open http://localhost:5173 and sign in with **rene / panther123**.

The Vite dev server proxies `/api` to Django (`http://localhost:8000`), so the session
cookie stays same-origin — no CORS setup needed for local development.

## Build for production
```bash
npm run build      # type-checks (tsc) then bundles to dist/
npm run preview    # serve the production build locally
```

## Structure
```
src/
  api.ts            Typed fetch client for /api/v1
  types.ts          Domain types (User, DashboardData, ClientRow, Analytics…)
  auth.tsx          Auth context (session check, login, logout)
  components/       Layout (sidebar + topbar), Icon
  pages/            Login, Dashboard, Clients, Analytics
  styles.css        Panther design system
```

## Notes for production
- Auth here is session-based via the dev proxy. For a separately-hosted SPA, add proper
  CORS + CSRF (or switch the API to JWT). The endpoints are in `dashboard/api.py`.
- Charts are dependency-free inline SVG; swap in a chart library if you want richer
  interactivity.
