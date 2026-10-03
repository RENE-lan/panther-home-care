# Panther Home Care - Mobile (professional TypeScript scaffold)

This is the full, structured version of the app: TypeScript, React Navigation, Zustand,
typed api layer, components, hooks, services (offline queue, location, notifications).
It talks to the SAME Django backend as `../mobile` (via `/api/mobile/`).

> Your simpler, already-working app is in `../mobile`. Keep it as a fallback.
> This scaffold is generated and syntax-checked but NOT run on a device yet —
> expect to fix a few import/type issues on first launch.

## Setup
1. Set your backend in `src/config.ts` (API_BASE), e.g. `http://172.20.10.6:8000/api/mobile`
   (or set it in-app on the login screen via "Adresse du serveur").
2. Install and run:
```
npm install
npx expo install --fix        # aligns native deps to your Expo SDK
npx expo start --clear
```
3. Scan the QR in Expo Go (same Wi-Fi / hotspot as your PC).

## Structure
- `src/api/` - typed API modules (auth, dashboard, visits, evv, messages, ...)
- `src/store/` - Zustand stores (authStore is wired)
- `src/navigation/` - RootNavigator -> Auth/Main -> MainTabs (role-aware) + detail stack
- `src/screens/` - screens by domain (auth, home, schedule, evv, care, incidents, messages, profile, clients, caregivers, ai)
- `src/components/` - Button, Input, Card, StatCard, VisitCard, StatusBadge, Icon, SignaturePad, ...
- `src/services/` - offlineQueue, locationService, notificationService, syncService
- `src/theme/` - colors, spacing, typography

## What's functional
Login/signup + server-address, role-aware Home (office KPIs / caregiver / family),
Schedule, EVV check-in (GPS geofence) + check-out with drawn signature, Report incident (+photo),
Messages, Requests, Clients, Reports, Invoices (pay), AI copilot, Profile (biometric toggle),
offline queue, push registration. Secondary screens are present as stubs to extend.

## Accounts
rene / panther123  ·  soignant / soignant123  ·  famille / famille123
