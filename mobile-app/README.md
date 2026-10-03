# Panther Home Care — Application mobile (Expo + React Native + TypeScript)

Reprend les mêmes données que la plateforme web, via l'API Django (`/api/mobile/`).

## Lancer l'app
```bash
cd mobile-app
npm install
npx expo start
```
Puis :
- Scannez le QR code avec **Expo Go** (App Store / Play Store) sur votre téléphone, **ou**
- Appuyez `a` (Android emulator) / `i` (iOS simulator).

## Connecter au backend
Le backend Django doit tourner (`py manage.py runserver 0.0.0.0:8000`).
À l'écran de connexion → « Configurer l'adresse du serveur », mettez :
- **Téléphone réel** (même Wi-Fi/hotspot que le PC) : `http://<IP-du-PC>:8000` (ex. `http://192.168.1.20:8000`) — trouvez l'IP avec `ipconfig`.
- **Émulateur Android** : `http://10.0.2.2:8000`
- **Simulateur iOS** : `http://127.0.0.1:8000`

Connexion démo : **rene / panther123**.

## Construire un APK/IPA téléchargeable
```bash
npm install -g eas-cli
eas login
eas build -p android --profile preview   # génère un .apk téléchargeable
```
(Compte Expo gratuit requis. Pour iOS, un compte Apple Developer est nécessaire.)

## Écrans
Accueil (KPIs, coordinateur IA, visites du jour, actions rapides), Couverture & affectations,
Clients, Soignants, Copilote (chat), Plus (profil, serveur, déconnexion).
