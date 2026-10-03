# Panther Home Care — Mobile app (Expo / React Native)

An all-in-one app: one login routes each role to its screens (Coordinator, Caregiver, Family).
It talks to the **same Django backend** as the web app via `/api/mobile/` — same data, one source of truth.

## 1. Point the app at your backend
Open **`src_config.js`** and set `API_BASE`:
- **Testing on your phone with the Django dev server:** use your computer's LAN IP, e.g.
  `http://192.168.1.20:8000/api/mobile` (find your IP with `ipconfig` on Windows → IPv4 Address).
  Your phone and PC must be on the **same Wi‑Fi**. Do NOT use `127.0.0.1`.
- **Deployed:** use your Render URL, e.g. `https://panther-backend-xxxx.onrender.com/api/mobile`.

Also make sure the Django server is reachable:
- Run it bound to all interfaces: `python manage.py runserver 0.0.0.0:8000`
- CORS is already open for `/api/` in DEBUG.

## 2. Install & run
Requires **Node.js** (nodejs.org). Then in this `mobile/` folder:
```
npm install
npx expo start
```
Install **Expo Go** on your phone (App Store / Play Store), then **scan the QR code** shown in the terminal.
The app opens on your phone.

## 3. Log in
- Manager: `rene` / `panther123`
- Caregiver: `soignant` / `soignant123`
- Family: `famille` / `famille123`
(You can also log in with an ID number, e.g. `ID-10001`.)

## What each role sees (bottom-tab navigation + detail screens)
- **Caregiver:** **Visites** (clock‑in with GPS, **Terminer & signer** → full EVV form: humeur, notes, signature), **Ouvertes** (open shifts with match %, one‑tap **Demander**), **Heures** (weekly timesheet).
- **Coordinator / Manager:** **Accueil** (live KPIs + AI action cards → tap to open **CareMatch** and **assign** a caregiver), **Demandes** (approve/deny visit requests), **Clients** (searchable, green/red payment), **Copilote** (AI chat).
- **Family:** **Accueil** (wellbeing % + live "today"), **Messages** (2‑way with the agency), **Rapports** (care history), **Factures** (**Payer maintenant**).

**Advanced:** offline cache (screens show last data instantly, then refresh), **pull‑to‑refresh** everywhere, GPS EVV, and persistent login.

## Extending
Every screen is a small component in `App.js` calling `api("/endpoint/")`. Add a Django endpoint in
`dashboard/mobile_api.py`, wire it in `config/mobile_urls.py`, then call it from a new screen.
