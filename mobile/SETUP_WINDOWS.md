# Panther Mobile — run it on your phone (Windows)

You need **2 PowerShell windows**: one for the backend, one for the app.

## A) Backend window  (folder: ...\panther, where manage.py is)
```
cd "C:\Users\Admin\Downloads\panther mobile\panther"
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000
```
Leave it running. If Windows Firewall asks, click **Allow access**.

## B) App window  (folder: ...\panther\mobile)
1. Set your PC's IP in **src_config.js** (find it with `ipconfig` → IPv4). Example line:
   `export const API_BASE = "http://192.168.0.154:8000/api/mobile";`

2. Because your Expo Go is a newer SDK, refresh the packages ONCE:
```
cd "C:\Users\Admin\Downloads\panther mobile\panther\mobile"
Remove-Item -Recurse -Force node_modules
Remove-Item -Force package-lock.json
npm install
npx expo install --fix
```

3. Start it, forcing your IP so the phone can connect:
```
$env:REACT_NATIVE_PACKAGER_HOSTNAME="192.168.0.154"
npx expo start --clear
```
The "Metro waiting on" line MUST show `exp://192.168.0.154:8081` (your IP, NOT 127.0.0.1).
Scan the QR in **Expo Go** (phone on the SAME Wi-Fi).

## Firewall (once, as Administrator) — if the phone can't connect
Open PowerShell **as administrator** and run:
```
netsh advfirewall firewall add rule name="Panther" dir=in action=allow protocol=TCP localport=8000,8081,19000,19001,8082
```

## Test the connection (from the phone browser)
Open `http://192.168.0.154:8000/api/mobile/me/` — any JSON reply (e.g. {"detail":"Non authentifié"}) means the phone reaches the backend, so login/signup will work.

## Accounts
- Manager: `rene` / `panther123`   ·   Caregiver: `soignant` / `soignant123`   ·   Family: `famille` / `famille123`
- Or tap **Créer un compte** on the app to register (Famille or Soignant).
