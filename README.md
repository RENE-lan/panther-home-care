# Panther Home Care — Plateforme d'opérations de soins à domicile

An **AI-powered Home Care Operations Platform** built with Django, positioned as the
architecture document recommends: not "software for scheduling caregivers" but a
platform that *understands what is happening, flags what needs attention, and
recommends what should happen next — while keeping humans in control of the final
decision.*

Built for the Lubumbashi (RDC) market shown in the pitch, with POPIA / Loi 18/035
privacy in mind. UI is in French to match the pitch; code and models are in English.

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo          # loads the pitch scenario (Client #014, etc.)
python manage.py runserver
```

Open http://127.0.0.1:8000/ — you'll land on the **sign-in** screen. You can:

- **Create an account** (Créer un compte) with any email + password — it works
  immediately, no email server needed, and drops you straight into the dashboard, or
- **Use the demo coordinator** already seeded:

| Rôle          | Identifiant (nom d'utilisateur ou e-mail) | Mot de passe |
|---------------|-------------------------------------------|--------------|
| Coordinateur  | `rene` *or* `rene@panthergroup.cd`        | `panther123` |

**Social sign-in (Google / Apple / Facebook)** — the buttons are on the sign-in and
sign-up screens, wired to real OAuth. A provider activates once its credentials are
supplied via environment variables (see `.env.example`); until then, clicking it shows a
clean "not yet configured" page rather than an error. Email + password covers everything
in the meantime.

Create a Django admin superuser for `/admin/` with
`python manage.py createsuperuser`.

Runs on **SQLite out of the box** (zero config). For PostgreSQL, copy `.env.example`
to `.env` and set the `POSTGRES_*` variables — the settings pick it up automatically.

### Deploying to the web (GitHub + Render)

See **`DEPLOY.md`** for a full step-by-step: push to GitHub, then one-click deploy
the database + Django backend + React frontend on Render via the included
`render.yaml` Blueprint.

### Optional: enable LLM-powered AI

The app's AI (matching, risk detection, daily brief) is rule-based and needs **no key**.
To upgrade the **daily brief** to natural-language generation with a real LLM:

1. Copy `.env.example` to `.env` (in the `panther/` folder).
2. In `.env`, set the provider and **paste your key**:
   ```
   AI_PROVIDER=openai        # or: anthropic | gemini
   AI_API_KEY=sk-...         # your key
   ```
3. Restart `python manage.py runserver`.

The key stays **server-side only** — it is read by Django and used to call the provider
from the backend; it is never exposed to the browser or the React app. `.env` is
git-ignored. If the key is missing or a call fails, the brief automatically falls back
to the built-in rule-based summary, so nothing breaks. Results are cached ~15 minutes to
avoid calling the API on every page load.

### Optional: the React frontend (Vite + TypeScript)

The repo also ships a modern **React + Vite + TypeScript** single-page app in
`frontend/`, which consumes the Django JSON API (`/api/v1/…`). It runs alongside the
Django UI. In a second terminal, with the Django server running:

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api to Django on :8000)
```

Sign in with the same `rene` / `panther123`. See `frontend/README.md` for details.

---

## What's built (Phase 1 MVP + the AI differentiators)

This covers the operational foundation the document insists on building first —
`CLIENT → CARE PLAN → CAREGIVER → SCHEDULE → VISIT → ATTENDANCE → REPORT → INCIDENT` —
plus the five features Panther should be famous for.

**Coordinator web portal** (`/`)
- Live **Tableau de bord** mirroring the pitch: KPIs, uncovered-shift hero card,
  daily AI brief, ATTENTION and CRITIQUE panels.
- **Client 360°** with a care-intelligence timeline (visits, reports, AI flags,
  incidents interleaved).
- **Caregiver 360°** with skills, performance scores and certification compliance.
- **Rapports** section — every care report, filterable to the AI-flagged ones, with
  a detail view per report.
- Planification, Incidents, and one-click **Approuver l'affectation**.

**Accounts & authentication** (`django-allauth`) — a split-screen sign-in and sign-up:
email + password (works with zero setup), plus **Google / Apple / Facebook** wired to
real OAuth (each activates once its credentials are set). Login accepts username *or*
email; sign-up has a live password-strength meter and show/hide toggles.

**Branded admin** — the Django admin at `/admin/` is themed to the Panther brand (navy
header + logo, orange accents) with a KPI dashboard on the home page, and across the
models: colored status badges, filters, search, date hierarchies, and actions (CSV
export, mark-incident-resolved, advance-applicant-stage).

**Notifications center** (`/notifications/`) — the bell opens a full alert feed with
unread badges and one-click mark-all-read.

**Analytics & Intelligence** (`/analytics/`) — a live BI dashboard (Chart.js,
vendored locally so it works offline): visit volume, AI-flag trend, satisfaction,
client-risk distribution, incidents by severity, and caregiver workload — with
headline KPIs (utilization, satisfaction, avg visits/day).

**Geospatial operations map** (`/map/`) — clients and caregivers plotted from their
real GPS coordinates on a dependency-free SVG canvas (no tiles, no API key). When a
visit is uncovered, the AI draws weighted match lines to the top candidates.

**Schedule timeline** (`/schedule/`) — a day-grid of caregivers × hours with visit
blocks positioned by time and coloured by status, plus a highlighted "unassigned" lane
and day navigation.

**Explainable AI matching** — the matching engine shows a per-candidate score
breakdown (skills / distance / reliability / punctuality / workload / language), so the
recommendation is transparent rather than a black box.

**PDF export & printing** (`dashboard/pdf.py`, pure-Python `fpdf2` — no native libs)
- **Client 360° dossier** — full care dossier (profile, care plan, contacts, visit
  history, recent reports, AI concerns, incidents) from the "Dossier PDF" button.
- **Care report PDF** — a single visit report with vitals, tasks and the AI analysis.
- **Daily brief PDF** — the coordinator's operations brief with a KPI band.
- Every page also carries an **Imprimer** button; a dedicated print stylesheet gives
  clean "Save as PDF" output straight from the browser.
- Add `?download` to any `*.pdf` URL to force a file download instead of inline view.

**Interface** — clean inline-SVG icon set throughout (no emoji dependencies), so the
UI renders identically on every OS and browser.

**Panther AI Care Coordinator** (`ai/services.py`) — rule-based, swappable:
- **AI Care Matching Engine** — scores every available caregiver on skills fit,
  distance (haversine on GPS), reliability, punctuality, language and workload;
  returns ranked recommendations. This is genuinely computed, not hardcoded — so the
  top pick reflects your data.
- **Daily Operations Brief** — the 08:00 summary (on-schedule %, confirmed, late,
  uncovered).
- **Risk detection** — scans each care report for concern signals and low mood, and
  flags it for human review. **It never diagnoses** — output is always
  *"préoccupation potentielle — revue professionnelle recommandée."*

**Caregiver mobile API** (`/api/…`, plain JSON, no extra deps)
- `GET /api/my-visits/` — today's visits for the signed-in caregiver.
- `POST /api/visits/<id>/check-in/` — GPS check-in (EVV).
- `POST /api/visits/<id>/report/` — submit report + auto-complete visit; the AI risk
  pass runs on save.

**Cross-cutting:** role-based users (Coordinator / Caregiver / Family / Clinical),
audit log helper, alert/notification model, recruitment + training pipeline
(Talent Hub) in the admin.

---

## Module layout (flat, one concern per app)

```
config/         settings, urls, wsgi
accounts/       custom User with roles
clients/        Client, EmergencyContact, CarePlan, CareTask  (+ seed_demo command)
caregivers/     Skill, Caregiver, Certification, Availability, Applicant
scheduling/     Visit (attendance/EVV inline) + JSON mobile API
reports/        CareReport (mood, vitals, AI flag)
incidents/      Incident (severity, escalation)
notifications/  Notification / Alert engine
audit/          AuditLog (+ log() helper)
ai/             services.py — matching, daily brief, risk detection
dashboard/      coordinator web views + templates + pdf.py (PDF export)
                templatetags/icons.py — inline SVG icon set
```

The AI lives in plain functions over the ORM, so a rule can later be swapped for an
ML model without touching any caller.

---

## Roadmap (from the architecture document)

- **Phase 1 — MVP (done here):** clients, caregivers, scheduling, attendance,
  replacement, reports, incidents, dashboard, recruitment/training.
- **Phase 2 — Digital operations:** family portal, full mobile apps, offline sync,
  e-signatures, billing/payments (Mobile Money), document management.
- **Phase 3 — AI operations:** deeper matching, report analysis, predictive staffing.
- **Phase 4 — Intelligent care platform:** workforce forecasting, external
  healthcare integrations.

## Notes for production
- Set `DEBUG=0` and a real `SECRET_KEY` — security hardening (SSL redirect, HSTS,
  secure cookies) switches on automatically.
- Add MFA, per-role permission checks on views, and data-retention jobs for full
  POPIA alignment.
- The mobile API is intentionally dependency-free; swap in Django REST Framework when
  you want serializers and a browsable API.
