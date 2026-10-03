import React, { useState, useEffect, useCallback, useRef, createContext, useContext } from "react";
import {
  SafeAreaView, View, Text, TextInput, TouchableOpacity, ScrollView, FlatList,
  ActivityIndicator, StyleSheet, StatusBar, Alert, RefreshControl, Image, PanResponder, Linking,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Location from "expo-location";
import Svg, { Path } from "react-native-svg";
import * as LocalAuthentication from "expo-local-authentication";
import * as Notifications from "expo-notifications";
import * as ImagePicker from "expo-image-picker";
import { API_BASE } from "./src_config";

/* ============ theme (healthcare SaaS: navy / white / blue / green / orange / red) ============ */
const C = {
  navy: "#0e1c38", navy2: "#16294a", blue: "#2b6cb0", bg: "#f4f7fb", card: "#fff",
  ink: "#1f2b45", muted: "#6b7688", line: "#e6eaf0", green: "#1f8a4c", orange: "#e59a1c",
  red: "#d93a3a", orangeBrand: "#e8622a",
};

/* ============ api + offline cache ============ */
let TOKEN = null;
let BASE = API_BASE;
async function loadBase() { try { const b = await AsyncStorage.getItem("apibase"); if (b) BASE = b; } catch (e) {} }
async function api(path, method = "GET", body) {
  const headers = { "Content-Type": "application/json" };
  if (TOKEN) headers.Authorization = "Token " + TOKEN;
  const res = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  let data = {}; try { data = await res.json(); } catch (e) {}
  if (!res.ok) throw Object.assign(new Error(data.detail || "Erreur"), { status: res.status });
  return data;
}
function useData(path, deps = []) {
  const [data, setData] = useState(null); const [refreshing, setRefreshing] = useState(false);
  const load = useCallback(async (force) => {
    if (!force) { try { const c = await AsyncStorage.getItem("c:" + path); if (c) setData(JSON.parse(c)); } catch (e) {} }
    try { const d = await api(path); setData(d); AsyncStorage.setItem("c:" + path, JSON.stringify(d)); } catch (e) { setData((p) => p || { __err: true }); }
  }, [path]);
  useEffect(() => { load(); }, deps);
  return { data, refreshing, onRefresh: async () => { setRefreshing(true); await load(true); setRefreshing(false); }, reload: () => load(true) };
}
const Nav = createContext(); const useNav = () => useContext(Nav);

/* ============ advanced tech: offline queue, biometric, push, geofence ============ */
async function queuedApi(path, method, body) {
  try { return await api(path, method, body); }
  catch (e) {
    if (!e.status) { // network failure → queue for later sync
      const q = JSON.parse((await AsyncStorage.getItem("queue")) || "[]");
      q.push({ path, method, body }); await AsyncStorage.setItem("queue", JSON.stringify(q));
      return { __queued: true };
    }
    throw e;
  }
}
async function flushQueue() {
  const q = JSON.parse((await AsyncStorage.getItem("queue")) || "[]");
  if (!q.length) return 0;
  const rest = []; let done = 0;
  for (const it of q) { try { await api(it.path, it.method, it.body); done++; } catch (e) { rest.push(it); } }
  await AsyncStorage.setItem("queue", JSON.stringify(rest));
  return done;
}
async function biometricUnlock() {
  try {
    const ok = (await LocalAuthentication.hasHardwareAsync()) && (await LocalAuthentication.isEnrolledAsync());
    if (!ok) return true;
    const r = await LocalAuthentication.authenticateAsync({ promptMessage: "Déverrouiller Panther", fallbackLabel: "Mot de passe" });
    return !!r.success;
  } catch (e) { return true; }
}
async function registerPush() {
  try {
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== "granted") return;
    const token = (await Notifications.getExpoPushTokenAsync()).data;
    if (token) await api("/push-token/", "POST", { token });
  } catch (e) {}
}
function haversine(a, b, c, d) {
  const R = 6371000, r = Math.PI / 180;
  const dLat = (c - a) * r, dLng = (d - b) * r;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin(dLng / 2) ** 2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x)));
}
async function getCoords() {
  try { const { status } = await Location.requestForegroundPermissionsAsync(); if (status !== "granted") return null; const p = await Location.getCurrentPositionAsync({}); return { lat: p.coords.latitude, lng: p.coords.longitude }; }
  catch (e) { return null; }
}

/* ============ drawn signature pad (react-native-svg) ============ */
function SignaturePad({ onChange }) {
  const [paths, setPaths] = useState([]); const cur = useRef("");
  const pan = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => true, onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: (e) => { cur.current = `M${e.nativeEvent.locationX.toFixed(1)},${e.nativeEvent.locationY.toFixed(1)}`; },
    onPanResponderMove: (e) => { cur.current += ` L${e.nativeEvent.locationX.toFixed(1)},${e.nativeEvent.locationY.toFixed(1)}`; setPaths((p) => [...p.slice(0, -1), cur.current]); },
    onPanResponderStart: () => setPaths((p) => [...p, cur.current]),
    onPanResponderRelease: () => { setPaths((p) => { const np = [...p]; onChange && onChange(np.join(" ")); return np; }); },
  })).current;
  const clear = () => { setPaths([]); cur.current = ""; onChange && onChange(""); };
  return (
    <View>
      <View style={s.sigPad} {...pan.panHandlers}>
        <Svg width="100%" height="100%">{paths.map((d, i) => <Path key={i} d={d} stroke={C.navy} strokeWidth={2.5} fill="none" strokeLinejoin="round" strokeLinecap="round" />)}</Svg>
      </View>
      <TouchableOpacity onPress={clear} style={s.sigClear}><Text style={{ color: C.muted, fontSize: 12 }}>Effacer</Text></TouchableOpacity>
    </View>
  );
}

/* ============ UI kit ============ */
const Card = ({ children, style }) => <View style={[s.card, style]}>{children}</View>;
const Center = () => <View style={s.center}><ActivityIndicator size="large" color={C.blue} /></View>;
const Empty = ({ t }) => <Card style={{ alignItems: "center", paddingVertical: 26 }}><View style={s.emptyIcon}><Icon name="inbox" size={22} color={C.muted} /></View><Text style={[s.muted, { marginTop: 10, textAlign: "center" }]}>{t}</Text></Card>;
const NotLinked = ({ what }) => (
  <View style={s.body}><Card style={{ alignItems: "center", paddingVertical: 26 }}>
    <View style={s.emptyIcon}><Icon name="user" size={22} color={C.blue} /></View>
    <Text style={[s.title, { marginTop: 10, textAlign: "center" }]}>Aucun proche lié</Text>
    <Text style={[s.muted, { marginTop: 6, textAlign: "center" }]}>Liez votre proche depuis l'onglet Accueil (avec le code de l'agence) pour {what}.</Text>
  </Card></View>
);
const Row = ({ children, style }) => <View style={[{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }, style]}>{children}</View>;
const Dot = ({ c }) => <View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: c, marginRight: 8 }} />;
function Btn({ t, onPress, kind = "primary", icon }) {
  const bg = kind === "primary" ? C.blue : kind === "green" ? C.green : kind === "red" ? C.red : kind === "navy" ? C.navy : "#fff";
  const col = kind === "ghost" ? C.ink : "#fff";
  return <TouchableOpacity onPress={onPress} style={[s.bigBtn, { backgroundColor: bg, borderWidth: kind === "ghost" ? 1 : 0, borderColor: C.line }]}>
    <Text style={[s.bigBtnTxt, { color: col }]}>{icon ? icon + "  " : ""}{t}</Text></TouchableOpacity>;
}
function Status({ st }) {
  const map = { COMPLETED: ["Terminée", C.green, ""], IN_PROGRESS: ["En cours", C.blue, "●"], UNCOVERED: ["Non couvert", C.red, "!"], SCHEDULED: ["À venir", C.muted, "○"] };
  const [lbl, col, ic] = map[st] || map.SCHEDULED;
  return <View style={[s.status, { backgroundColor: col + "1a" }]}><Text style={{ color: col, fontWeight: "700", fontSize: 12 }}>{ic} {lbl}</Text></View>;
}
const Refresher = (h) => <RefreshControl refreshing={h.refreshing} onRefresh={h.onRefresh} tintColor={C.blue} />;

/* ---- clean line icons (SVG, not emoji) ---- */
const ICONS = {
  home: "M3 10.5L12 3l9 7.5M5 9v11a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9",
  calendar: "M3 5h18v16H3zM3 9h18M8 3v4M16 3v4",
  users: "M16 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 20v-2a4 4 0 0 0-3-3.9M15 2.1a4 4 0 0 1 0 7.8",
  user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8",
  inbox: "M22 12h-6l-2 3h-4l-2-3H2M5.5 5L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6L18.5 5A2 2 0 0 0 16.8 4H7.2A2 2 0 0 0 5.5 5z",
  grid: "M4 4h6v6H4zM14 4h6v6h-6zM14 14h6v6h-6zM4 14h6v6H4z",
  pin: "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0zM12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  message: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  file: "M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h8",
  card: "M2 5h20v14H2zM2 10h20",
  check: "M22 11v1a10 10 0 1 1-6-9M22 5L12 15l-3-3",
  alert: "M10.3 4L2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 4a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01",
  dollar: "M12 2v20M17 6H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6",
  activity: "M22 12h-4l-3 8L9 4l-3 8H2",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
};
function Icon({ name, size = 20, color = C.blue }) {
  return <Svg width={size} height={size} viewBox="0 0 24 24"><Path d={ICONS[name] || ICONS.home} stroke={color} strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" /></Svg>;
}
function Avatar({ name, size = 44, bg = C.navy }) {
  const init = (name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  return <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: bg, alignItems: "center", justifyContent: "center" }}><Text style={{ color: "#fff", fontWeight: "800", fontSize: size * 0.36 }}>{init}</Text></View>;
}
function Skeleton({ rows = 4 }) {
  return <View style={s.body}>{Array.from({ length: rows }).map((_, i) => (
    <View key={i} style={s.skelCard}><View style={[s.skelBar, { width: "55%" }]} /><View style={[s.skelBar, { width: "80%", marginTop: 8 }]} /></View>
  ))}</View>;
}
function MiniBar({ data }) {
  const max = Math.max(1, ...data.map((d) => d.n));
  return <View style={{ flexDirection: "row", alignItems: "flex-end", height: 70, gap: 8, marginTop: 6 }}>
    {data.map((d, i) => (<View key={i} style={{ flex: 1, alignItems: "center" }}>
      <View style={{ width: "70%", height: Math.max(4, (d.n / max) * 56), backgroundColor: i === data.length - 1 ? C.blue : "#cfe0f5", borderRadius: 4 }} />
      <Text style={{ fontSize: 10, color: C.muted, marginTop: 4 }}>{d.d}</Text>
    </View>))}
  </View>;
}

/* ============ LOGIN + SIGNUP ============ */
function Login({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [login, setLogin] = useState(""); const [pw, setPw] = useState("");
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [phone, setPhone] = useState("");
  const [role, setRole] = useState("FAMILY"); const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const [srvOpen, setSrvOpen] = useState(false); const [srv, setSrv] = useState(BASE);
  const save = async (d) => { TOKEN = d.token; await AsyncStorage.setItem("tok", d.token); await AsyncStorage.setItem("me", JSON.stringify(d)); onLogin(d); };
  const doLogin = async () => { setBusy(true); setErr(""); try { save(await api("/login/", "POST", { login, password: pw })); } catch (e) { setErr(e.status ? "Identifiants invalides." : "Serveur injoignable — vérifiez src_config.js et le Wi-Fi."); } setBusy(false); };
  const doSignup = async () => { setBusy(true); setErr(""); try { save(await api("/signup/", "POST", { name, email, phone, password: pw, role })); } catch (e) { setErr(e.message || "Impossible de créer le compte."); } setBusy(false); };
  return (
    <ScrollView contentContainerStyle={s.loginWrap} keyboardShouldPersistTaps="handled">
      <Image source={require("./assets/logo.jpg")} style={s.logoImg} resizeMode="contain" />
      {mode === "login" ? (<>
        <Text style={s.h1}>Bienvenue</Text><Text style={s.sub}>Connectez-vous à votre espace de soins.</Text>
        <TextInput style={s.input} placeholder="E-mail, identifiant ou N° d'identification" autoCapitalize="none" value={login} onChangeText={setLogin} placeholderTextColor={C.muted} />
        <TextInput style={s.input} placeholder="Mot de passe" secureTextEntry value={pw} onChangeText={setPw} placeholderTextColor={C.muted} />
        {err ? <Text style={s.err}>{err}</Text> : null}
        <Btn t={busy ? "…" : "Se connecter"} onPress={doLogin} />
        <TouchableOpacity onPress={() => { setMode("signup"); setErr(""); }} style={{ marginTop: 16 }}><Text style={s.link}>Pas de compte ? <Text style={{ color: C.orangeBrand, fontWeight: "700" }}>Créer un compte</Text></Text></TouchableOpacity>
      </>) : (<>
        <Text style={s.h1}>Créer un compte</Text><Text style={s.sub}>Inscrivez-vous pour suivre les soins en direct.</Text>
        <TextInput style={s.input} placeholder="Nom complet" value={name} onChangeText={setName} placeholderTextColor={C.muted} />
        <TextInput style={s.input} placeholder="E-mail" autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} placeholderTextColor={C.muted} />
        <TextInput style={s.input} placeholder="Téléphone (optionnel)" value={phone} onChangeText={setPhone} placeholderTextColor={C.muted} />
        <TextInput style={s.input} placeholder="Mot de passe (8+ caractères)" secureTextEntry value={pw} onChangeText={setPw} placeholderTextColor={C.muted} />
        <Text style={s.lbl}>Je suis :</Text>
        <View style={{ flexDirection: "row", gap: 8, marginBottom: 12 }}>
          <TouchableOpacity style={[s.roleBtn, role === "FAMILY" && s.roleBtnOn]} onPress={() => setRole("FAMILY")}><Text style={[s.roleTxt, role === "FAMILY" && { color: "#fff" }]}>Famille</Text></TouchableOpacity>
          <TouchableOpacity style={[s.roleBtn, role === "CAREGIVER" && s.roleBtnOn]} onPress={() => setRole("CAREGIVER")}><Text style={[s.roleTxt, role === "CAREGIVER" && { color: "#fff" }]}>Soignant</Text></TouchableOpacity>
        </View>
        {err ? <Text style={s.err}>{err}</Text> : null}
        <Btn t={busy ? "…" : "Créer mon compte"} onPress={doSignup} kind="green" />
        <TouchableOpacity onPress={() => { setMode("login"); setErr(""); }} style={{ marginTop: 16 }}><Text style={s.link}>Déjà un compte ? <Text style={{ color: C.orangeBrand, fontWeight: "700" }}>Se connecter</Text></Text></TouchableOpacity>
      </>)}
      <TouchableOpacity onPress={() => setSrvOpen(!srvOpen)} style={{ marginTop: 22 }}><Text style={[s.link, { fontSize: 12 }]}> Adresse du serveur</Text></TouchableOpacity>
      {srvOpen ? (
        <View style={{ marginTop: 10 }}>
          <TextInput style={s.input} placeholder="http://192.168.0.154:8000/api/mobile" autoCapitalize="none" value={srv} onChangeText={setSrv} placeholderTextColor={C.muted} />
          <View style={{ flexDirection: "row", gap: 8 }}>
            <View style={{ flex: 1 }}><Btn t="Enregistrer" kind="navy" onPress={async () => { const v = srv.trim().replace(/\/$/, ""); BASE = v; await AsyncStorage.setItem("apibase", v); setErr(""); Alert.alert("Serveur enregistré", v); }} /></View>
            <View style={{ flex: 1 }}><Btn t="Tester" kind="ghost" onPress={async () => { try { const r = await fetch((srv.trim().replace(/\/$/, "")) + "/me/"); Alert.alert(r.status ? " Serveur joignable" : "Injoignable", "Réponse HTTP " + r.status); } catch (e) { Alert.alert("Injoignable", "Vérifiez l'IP, le Wi-Fi et que le backend tourne (runserver 0.0.0.0:8000)."); } }} /></View>
          </View>
        </View>
      ) : null}
    </ScrollView>
  );
}

/* ============ CAREGIVER ============ */
function CgHome({ me }) {
  const h = useData("/cg-home/"); const nav = useNav();
  if (!h.data) return <Skeleton />;
  const d = h.data;
  if (d.caregiver === false) return <View style={s.body}><Empty t="Profil soignant non lié à ce compte." /></View>;
  const t = d.today || {};
  return (
    <ScrollView style={s.body} refreshControl={Refresher(h)}>
      <Text style={s.hello}>Bonjour, {d.name}</Text>
      <Text style={s.subInline}>Prêt pour vos visites d'aujourd'hui ?</Text>
      <Card>
        <Text style={s.cardLabel}>AUJOURD'HUI</Text>
        <Row style={{ marginTop: 8 }}>
          <View style={s.todayCell}><Text style={s.todayN}>{t.total || 0}</Text><Text style={s.todayL}>Visites</Text></View>
          <View style={s.todayCell}><Text style={[s.todayN, { color: C.green }]}>{t.completed || 0}</Text><Text style={s.todayL}>Terminées</Text></View>
          <View style={s.todayCell}><Text style={[s.todayN, { color: C.blue }]}>{t.in_progress || 0}</Text><Text style={s.todayL}>En cours</Text></View>
          <View style={s.todayCell}><Text style={[s.todayN, { color: C.orange }]}>{t.upcoming || 0}</Text><Text style={s.todayL}>À venir</Text></View>
        </Row>
      </Card>
      {d.next_visit && (<>
        <Text style={s.section}>PROCHAINE VISITE</Text>
        <Card>
          <Text style={s.title}>{d.next_visit.client} — {d.next_visit.name}</Text>
          <Text style={s.muted}>{d.next_visit.time}–{d.next_visit.end} · {d.next_visit.care}</Text>
          {d.next_visit.km != null && <Text style={{ color: C.blue, marginTop: 4 }}>{d.next_visit.km} km</Text>}
          <View style={{ marginTop: 12 }}><Btn t="Voir la visite" onPress={() => nav.push("visitDetail", { id: d.next_visit.id })} /></View>
        </Card>
      </>)}
      {d.cert_warning && (
        <View style={s.warnBox}><Text style={s.warnTitle}> Information importante</Text><Text style={s.warnTxt}>Votre certification « {d.cert_warning.name} » expire dans {d.cert_warning.days} jours.</Text></View>
      )}
      <Text style={s.section}>ASSISTANT PANTHER IA</Text>
      <Card style={{ backgroundColor: "#eaf1fb", borderColor: "#cfe0f5" }}>
        {(d.tips || []).length === 0 ? <Text style={s.muted}>Aucune alerte. Bonne journée !</Text> :
          (d.tips || []).map((tip, i) => <View key={i} style={{ flexDirection: "row", marginBottom: 6 }}><Text style={{ color: C.blue, marginRight: 6 }}>•</Text><Text style={{ flex: 1, color: C.ink }}>{tip}</Text></View>)}
      </Card>
    </ScrollView>
  );
}
function CgPlanning({ me }) {
  const h = useData("/my-visits/"); const nav = useNav();
  if (!h.data) return <Skeleton />;
  return (
    <ScrollView style={s.body} refreshControl={Refresher(h)}>
      <Text style={s.section}>MES VISITES (7 JOURS)</Text>
      {(h.data.visits || []).length === 0 && <Empty t="Aucune visite planifiée." />}
      {(h.data.visits || []).map((v) => (
        <TouchableOpacity key={v.id} onPress={() => nav.push("visitDetail", { id: v.id })}>
          <Card style={{ borderLeftWidth: 4, borderLeftColor: v.status === "COMPLETED" ? C.green : v.status === "IN_PROGRESS" ? C.blue : C.line }}>
            <Row><Text style={s.title}>{v.start}–{v.end}</Text><Status st={v.status} /></Row>
            <Text style={s.muted}>{v.client} · {v.care}</Text>
          </Card>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}
function CgEVV({ me }) {
  const h = useData("/my-visits/"); const nav = useNav();
  if (!h.data) return <Skeleton />;
  const visits = h.data.visits || [];
  const active = visits.find((v) => v.status === "IN_PROGRESS");
  const nextS = visits.find((v) => v.status === "SCHEDULED");
  const checkin = async (v) => {
    const coords = await getCoords();
    let geo = "";
    if (coords && v.lat != null) {
      const dist = haversine(coords.lat, coords.lng, v.lat, v.lng); geo = `Distance ${dist} m. `;
      if (dist > 300) { const go = await new Promise((r) => Alert.alert("Hors zone", `Vous etes a ${dist} m du client. Pointer quand meme ?`, [{ text: "Annuler", onPress: () => r(false) }, { text: "Pointer", onPress: () => r(true) }])); if (!go) return; }
    }
    try { const res = await queuedApi(`/visits/${v.id}/checkin/`, "POST", coords || {}); h.reload(); Alert.alert(res.__queued ? "Hors-ligne" : "Arrivee pointee", (res.__queued ? "Synchro a la reconnexion. " : geo) + "Localisation verifiee."); } catch (e) { Alert.alert("Erreur"); }
  };
  return (
    <ScrollView style={s.body} refreshControl={Refresher(h)}>
      {active ? (
        <Card style={{ borderColor: C.green, borderWidth: 1.5 }}>
          <Row><Text style={{ color: C.green, fontWeight: "800" }}>● VISITE EN COURS</Text></Row>
          <Text style={[s.title, { marginTop: 8 }]}>{active.client}</Text>
          <Text style={s.muted}>{active.start}–{active.end}</Text>
          <View style={{ marginTop: 12 }}><Btn t="Terminer & signer" kind="green" onPress={() => nav.push("carenotes", { v: active, done: h.reload })} /></View>
          <View style={{ marginTop: 8 }}><Btn t="Signaler un incident" kind="ghost" onPress={() => nav.push("incident", { v: active })} /></View>
        </Card>
      ) : nextS ? (
        <Card>
          <View style={{ alignItems: "center", paddingVertical: 10 }}>
            <View style={s.pinDot} />
            <Text style={{ fontWeight: "800", color: C.ink, marginTop: 6 }}>PROCHAINE VISITE</Text>
          </View>
          <Text style={s.title}>{nextS.client}</Text>
          <Text style={s.muted}>{nextS.start}–{nextS.end} · {nextS.care}</Text>
          <View style={s.evvPolicy}>
            <Text style={s.evvPolicyItem}> Localisation</Text><Text style={s.evvPolicyItem}> Soignant</Text><Text style={s.evvPolicyItem}> Heure prévue</Text>
          </View>
          <View style={{ marginTop: 12 }}><Btn t="Pointer l'arrivée (Check-in)" onPress={() => checkin(nextS)} /></View>
        </Card>
      ) : <Empty t="Aucune visite à pointer pour le moment." />}
      <Text style={s.section}>AUJOURD'HUI</Text>
      {visits.map((v) => (
        <Card key={v.id}><Row><Text style={s.title}>{v.start}–{v.end} · {v.client}</Text><Status st={v.status} /></Row></Card>
      ))}
    </ScrollView>
  );
}
function VisitDetail({ params }) {
  const nav = useNav(); const [d, setD] = useState(null);
  useEffect(() => { (async () => { try { setD(await api(`/visits/${params.id}/detail/`)); } catch (e) { setD({ __err: true }); } })(); }, []);
  if (!d) return <Center />;
  if (d.__err) return <View style={s.body}><Empty t="Impossible de charger la visite." /></View>;
  const checkin = async () => {
    const coords = await getCoords();
    let geo = "";
    if (coords && d.lat != null) { const dist = haversine(coords.lat, coords.lng, d.lat, d.lng); geo = `Distance ${dist} m. `; if (dist > 300) { const go = await new Promise((r) => Alert.alert("Hors zone", `Vous etes a ${dist} m du client. Pointer quand meme ?`, [{ text: "Annuler", onPress: () => r(false) }, { text: "Pointer", onPress: () => r(true) }])); if (!go) return; } }
    try { const res = await queuedApi(`/visits/${params.id}/checkin/`, "POST", coords || {}); Alert.alert(res.__queued ? "Hors-ligne" : "Arrivee pointee", (res.__queued ? "Synchro a la reconnexion." : geo + "Localisation verifiee.")); nav.pop(); } catch (e) { Alert.alert("Erreur"); }
  };
  return (
    <ScrollView style={s.body}>
      <Card>
        <Text style={s.title}>{d.client} — {d.name}</Text>
        <Text style={s.muted}> {d.time}–{d.end}</Text>
        <Text style={s.muted}> {d.address}</Text>
      </Card>
      <Text style={s.section}>PLAN DE SOINS</Text>
      <Card>{(d.tasks || []).map((t, i) => (<View key={i} style={s.taskRow}><Text style={{ color: C.green, marginRight: 8, fontWeight: "700" }}>{"\u2713"}</Text><Text style={{ flex: 1 }}>{t.label}</Text></View>))}</Card>
      <Text style={s.section}>INFORMATIONS IMPORTANTES</Text>
      <Card><Text>{d.note}</Text></Card>
      <View style={{ marginTop: 14 }}>
        {d.status === "IN_PROGRESS" ? <Btn t="Terminer & signer" kind="green" onPress={() => nav.push("carenotes", { v: { id: d.id, client: d.client } })} />
          : d.status === "SCHEDULED" || d.status === "UNCOVERED" ? <Btn t="Commencer la visite (Check-in)" onPress={checkin} />
            : <Btn t="Visite terminée" kind="ghost" onPress={() => nav.pop()} />}
      </View>
      <View style={{ marginTop: 8 }}><Btn t="Signaler un incident" kind="ghost" onPress={() => nav.push("incident", { v: { id: d.id } })} /></View>
    </ScrollView>
  );
}
function CareNotes({ params }) {
  const nav = useNav(); const v = params.v;
  const [mood, setMood] = useState(4); const [notes, setNotes] = useState(""); const [sign, setSign] = useState(""); const [sig, setSig] = useState("");
  const opts = [[2, "À surveiller"], [3, "Stable"], [4, "Amélioré"]];
  const submit = async () => {
    if (!sig) { Alert.alert("Signature", "Veuillez signer avec votre doigt."); return; }
    if (!sign.trim()) { Alert.alert("Signature", "Entrez votre nom."); return; }
    try {
      const r = await queuedApi(`/visits/${v.id}/checkout/`, "POST", { mood, notes, signed_by: sign, signature: sig });
      params.done && params.done();
      Alert.alert(r.__queued ? "Enregistre hors-ligne" : "Verifie", r.__queued ? "Sera synchronise des le retour du reseau." : "Visite terminee et signee."); nav.pop();
    } catch (e) { Alert.alert("Erreur"); }
  };
  return (
    <ScrollView style={s.body}>
      <Text style={s.section}>NOTES DE SOINS — {v.client}</Text>
      <Card>
        <Text style={s.lbl}>Comment va le client aujourd'hui ?</Text>
        {opts.map(([val, fr]) => (
          <TouchableOpacity key={val} style={s.radioRow} onPress={() => setMood(val)}>
            <View style={[s.radio, mood === val && { borderColor: C.blue }]}>{mood === val ? <View style={s.radioDot} /> : null}</View>
            <Text style={{ fontSize: 15 }}>{fr}</Text>
          </TouchableOpacity>
        ))}
        <Text style={s.lbl}>Observations</Text>
        <TextInput style={[s.input, { height: 90, textAlignVertical: "top" }]} multiline placeholder="Ajoutez vos observations" value={notes} onChangeText={setNotes} placeholderTextColor={C.muted} />
        <Text style={s.lbl}>Signature (dessinez ci-dessous)</Text>
        <SignaturePad onChange={setSig} />
        <Text style={s.lbl}>Nom du signataire</Text>
        <TextInput style={s.input} placeholder="Votre nom" value={sign} onChangeText={setSign} placeholderTextColor={C.muted} />
        <Btn t="Enregistrer & terminer (Check-out)" kind="green" onPress={submit} />
      </Card>
    </ScrollView>
  );
}
function Incident({ params }) {
  const nav = useNav();
  const [type, setType] = useState("Chute"); const [sev, setSev] = useState("high"); const [desc, setDesc] = useState(""); const [photo, setPhoto] = useState(null);
  const types = ["Chute", "Medication", "Probleme de sante", "Comportement", "Autre"];
  const pick = async () => {
    try { const r = await ImagePicker.launchCameraAsync({ base64: true, quality: 0.4 }); if (!r.canceled && r.assets) { setPhoto(r.assets[0].base64); return; } } catch (e) {}
    try { const r2 = await ImagePicker.launchImageLibraryAsync({ base64: true, quality: 0.4 }); if (!r2.canceled && r2.assets) setPhoto(r2.assets[0].base64); } catch (e) { Alert.alert("Photo indisponible"); }
  };
  const submit = async () => {
    try { const r = await queuedApi(`/visits/${params.v.id}/incident/`, "POST", { type, severity: sev, description: desc, photo }); Alert.alert(r.__queued ? "Enregistre hors-ligne" : "Incident signale", r.__queued ? "Synchro a la reconnexion." : "Le bureau a ete alerte."); nav.pop(); } catch (e) { Alert.alert("Erreur"); }
  };
  return (
    <ScrollView style={s.body}>
      <Text style={s.section}>RAPPORT D'INCIDENT</Text>
      <Card>
        <Text style={s.lbl}>Quel est le probleme ?</Text>
        {types.map((tp) => (<TouchableOpacity key={tp} style={[s.choice, type === tp && { borderColor: C.red, backgroundColor: "#fdecec" }]} onPress={() => setType(tp)}><Text style={{ fontWeight: type === tp ? "700" : "400", color: type === tp ? C.red : C.ink }}>{tp}</Text></TouchableOpacity>))}
        <Text style={s.lbl}>Severite</Text>
        <View style={{ flexDirection: "row", gap: 8, marginBottom: 6 }}>
          {[["low", "Faible"], ["medium", "Moyenne"], ["high", "Elevee"]].map(([val, l]) => (
            <TouchableOpacity key={val} style={[s.sevBtn, sev === val && { backgroundColor: val === "high" ? C.red : val === "medium" ? C.orange : C.muted, borderColor: "transparent" }]} onPress={() => setSev(val)}><Text style={{ color: sev === val ? "#fff" : C.ink, fontWeight: "600", fontSize: 13 }}>{l}</Text></TouchableOpacity>
          ))}
        </View>
        <Text style={s.lbl}>Photo (optionnel)</Text>
        <Btn t={photo ? "Photo jointe - remplacer" : "Ajouter une photo"} kind="ghost" onPress={pick} />
        <Text style={s.lbl}>Description</Text>
        <TextInput style={[s.input, { height: 80, textAlignVertical: "top" }]} multiline placeholder="Decrivez ce qui s'est passe" value={desc} onChangeText={setDesc} placeholderTextColor={C.muted} />
        <Btn t="Soumettre le rapport" kind="red" onPress={submit} />
      </Card>
    </ScrollView>
  );
}

/* ============ MESSAGES (shared) ============ */
function Messages({ me }) {
  const h = useData("/messages/"); const [body, setBody] = useState("");
  const send = async () => { if (!body.trim()) return; const b = body; setBody(""); try { await api("/messages/", "POST", { body: b }); h.reload(); } catch (e) { Alert.alert("Message non envoyé", e.message || "Réessayez."); setBody(b); } };
  if (h.data && h.data.linked === false) {
    return (me && me.role === "FAMILY")
      ? <NotLinked what="écrire à l'agence" />
      : <View style={s.body}><Empty t="Aucun message pour ce compte." /></View>;
  }
  return (
    <View style={{ flex: 1 }}>
      <ScrollView style={s.body} refreshControl={Refresher(h)}>
        {h.data && (h.data.messages || []).map((m, i) => (
          <View key={i} style={[s.bubble, m.from_agency ? s.bubbleBot : s.bubbleMe]}>
            <Text style={{ color: m.from_agency ? C.ink : "#fff" }}>{m.body}</Text>
            <Text style={{ fontSize: 10, color: m.from_agency ? C.muted : "#dbe4f2", marginTop: 3 }}>{m.from_agency ? "Agence" : "Vous"} · {m.at}</Text>
          </View>))}
        {h.data && (h.data.messages || []).length === 0 && <Empty t="Aucun message. Écrivez à l'agence." />}
      </ScrollView>
      <View style={s.composer}><TextInput style={[s.input, { flex: 1, marginBottom: 0 }]} placeholder="Votre message…" value={body} onChangeText={setBody} placeholderTextColor={C.muted} /><TouchableOpacity style={s.sendBtn} onPress={send}><Text style={{ color: "#fff", fontSize: 15, fontWeight: "700" }}>OK</Text></TouchableOpacity></View>
    </View>
  );
}

/* ============ PLUS / MORE menu ============ */
function Plus({ me }) {
  const nav = useNav();
  const office = me.role !== "CAREGIVER" && me.role !== "FAMILY";
  const items = [["Mon profil", "profile"]];
  if (me.role === "CAREGIVER") items.push(["Mon planning", "cgplanning"], ["Certifications", "profile"], ["Mes performances", "profile"]);
  if (office) items.push(["Demandes", "requests"], ["Personnel", "personnel"], ["Portail familial", "familyPortals"], ["Copilote IA", "copilot"]);
  if (me.is_full_access) items.push(["Utilisateurs & accès", "admin"]);
  if (me.role === "FAMILY") items.push(["Rapports", "reports"], ["Factures", "invoices"]);
  return (
    <ScrollView style={s.body}>
      <Card>
        <Row><View style={{ flexDirection: "row", alignItems: "center", flex: 1 }}><Avatar name={me.name} /><View style={{ marginLeft: 12 }}><Text style={s.title}>{me.name}</Text><Text style={s.muted}>{me.id_number} · {me.role_label}</Text></View></View></Row>
      </Card>
      {items.map(([label, screen], i) => (
        <TouchableOpacity key={i} onPress={() => nav.push(screen, {})}>
          <Card style={{ paddingVertical: 15 }}><Row><Text style={{ fontSize: 15 }}>{label}</Text><Text style={{ color: C.muted, fontSize: 18 }}>›</Text></Row></Card>
        </TouchableOpacity>
      ))}
      <Text style={{ textAlign: "center", color: C.muted, marginTop: 20, marginBottom: 6 }}>Panther Home Care</Text>
      <Text style={{ textAlign: "center", color: C.muted, fontSize: 12 }}>Better Care. Stronger Teams.</Text>
    </ScrollView>
  );
}
function Profile({ me }) {
  const [bio, setBio] = useState(false);
  useEffect(() => { (async () => setBio((await AsyncStorage.getItem("bio")) === "1"))(); }, []);
  const toggleBio = async () => { const nv = !bio; setBio(nv); await AsyncStorage.setItem("bio", nv ? "1" : "0"); Alert.alert("Verrouillage biometrique", nv ? "Active - Face ID / empreinte demande au demarrage." : "Desactive."); };
  return (<ScrollView style={s.body}>
    <Card>
      <Text style={s.section}>MON PROFIL</Text>
      <Row><Text style={s.muted}>Nom</Text><Text style={s.title}>{me.name}</Text></Row>
      <Row style={{ marginTop: 10 }}><Text style={s.muted}>N identification</Text><Text style={s.title}>{me.id_number}</Text></Row>
      <Row style={{ marginTop: 10 }}><Text style={s.muted}>Role</Text><Text style={s.title}>{me.role_label}</Text></Row>
    </Card>
    <Text style={s.section}>SECURITE</Text>
    <TouchableOpacity onPress={toggleBio}><Card><Row><Text style={{ fontSize: 15 }}>Verrouillage biometrique</Text><View style={[s.toggle, bio && { backgroundColor: C.green }]}><View style={[s.toggleDot, bio && { marginLeft: 22 }]} /></View></Row></Card></TouchableOpacity>
  </ScrollView>);
}

/* ============ COORDINATOR ============ */
function CoHome({ me }) {
  const h = useData("/dashboard/"); const nav = useNav();
  if (!h.data) return <Skeleton rows={5} />;
  const k = h.data.kpis || {};
  const cells = [
    ["users", C.blue, "Clients", k.clients], ["activity", "#7c3aed", "Soignants", k.caregivers],
    ["calendar", C.orange, "Visites", k.today], ["check", C.green, "Terminées", k.completed],
    ["alert", k.incidents ? C.red : C.muted, "Incidents", k.incidents], ["dollar", k.outstanding ? C.red : C.green, "À encaisser", (k.outstanding || 0) + "$"],
  ];
  const qa = [["Planning", "calendar", 1], ["Demandes", "inbox", 2], ["Clients", "users", 3], ["Copilote", "activity", "copilot"]];
  return (
    <ScrollView style={s.body} refreshControl={Refresher(h)}>
      <View style={{ flexDirection: "row", alignItems: "center", marginBottom: 14 }}>
        <Avatar name={h.data.greeting || me.name} size={44} />
        <View style={{ marginLeft: 12 }}><Text style={s.hello}>Bonjour, {h.data.greeting || me.name}</Text><Text style={s.muted}>Voici votre journée</Text></View>
      </View>
      <View style={s.kpiGrid}>
        {cells.map(([ic, col, label, val], i) => (
          <View key={i} style={s.kpi}>
            <View style={[s.kpiIcon, { backgroundColor: col + "1a" }]}><Icon name={ic} size={17} color={col} /></View>
            <Text style={s.kpiVal}>{val}</Text><Text style={s.kpiLbl}>{label}</Text>
          </View>
        ))}
      </View>

      <Text style={s.section}>ACTIONS RECOMMANDÉES</Text>
      {(h.data.actions || []).length === 0 && <View style={s.okCard}><Icon name="check" size={18} color={C.green} /><Text style={{ color: C.green, marginLeft: 8, fontWeight: "600" }}>Rien à signaler.</Text></View>}
      {(h.data.actions || []).map((a, i) => (
        <TouchableOpacity key={i} onPress={() => a.visit_id && nav.push("matches", { visitId: a.visit_id })}>
          <Card style={{ borderLeftWidth: 4, borderLeftColor: a.type === "replacement" ? C.red : C.orange }}>
            <Text style={s.acHead}>{a.type === "replacement" ? "ACTION RECOMMANDÉE" : "REVUE CLINIQUE"}</Text>
            <Text style={s.title}>{a.title}</Text><Text style={s.muted}>{a.detail}{a.top ? " · " + a.top : ""}</Text>
          </Card>
        </TouchableOpacity>
      ))}

      <Text style={s.section}>ACCÈS RAPIDE</Text>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        {qa.map(([label, ic, target], i) => (
          <TouchableOpacity key={i} style={s.qaBtn} onPress={() => typeof target === "number" ? nav.setTab(target) : nav.push(target, {})}>
            <View style={s.qaIcon}><Icon name={ic} size={18} color={C.navy} /></View><Text style={s.qaLbl}>{label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={s.section}>VISITES TERMINÉES (7 JOURS)</Text>
      <Card><MiniBar data={h.data.trend || []} /></Card>

      <Text style={s.section}>AUJOURD'HUI</Text>
      <Card>
        {(h.data.today_list || []).length === 0 && <Text style={s.muted}>Aucune visite aujourd'hui.</Text>}
        {(h.data.today_list || []).map((v, i) => (
          <View key={i} style={s.timeRow}>
            <Text style={s.timeH}>{v.time}</Text>
            <View style={[s.timeDot, { backgroundColor: v.status === "COMPLETED" ? C.green : v.status === "IN_PROGRESS" ? C.blue : v.status === "UNCOVERED" ? C.red : "#c2cad6" }]} />
            <Text style={{ flex: 1 }}>{v.client}{v.caregiver ? " · " + v.caregiver : ""}</Text>
          </View>
        ))}
      </Card>
    </ScrollView>
  );
}
function CoSchedule() {
  const [offset, setOffset] = useState(0); const [d, setD] = useState(null);
  const jd = new Date().getDay(); const [day, setDay] = useState(jd === 0 ? 6 : jd - 1); const nav = useNav();
  useEffect(() => { (async () => { setD(null); try { setD(await api("/schedule/?week=" + offset)); } catch (e) { setD({ days: [] }); } })(); }, [offset]);
  if (!d) return <Center />;
  const days = d.days || []; const sel = days[day] || { visits: [] };
  return (
    <View style={{ flex: 1 }}>
      <View style={s.weekHead}>
        <TouchableOpacity onPress={() => setOffset(offset - 1)} style={s.weekNav}><Text style={s.weekNavTxt}>‹</Text></TouchableOpacity>
        <View style={{ alignItems: "center" }}><Text style={s.weekLabel}>{d.week_label}</Text><Text style={s.muted}>{d.total} visites · {d.uncovered} non couvertes</Text></View>
        <TouchableOpacity onPress={() => setOffset(offset + 1)} style={s.weekNav}><Text style={s.weekNavTxt}>›</Text></TouchableOpacity>
      </View>
      <View style={s.dayStrip}><ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 8 }}>
        {days.map((dd, i) => (<TouchableOpacity key={i} onPress={() => setDay(i)} style={[s.dayChip, i === day && { backgroundColor: C.navy, borderColor: C.navy }, dd.is_today && i !== day && { borderColor: C.orangeBrand }]}>
          <Text style={[s.dayChipLbl, i === day && { color: "#fff" }]}>{dd.label}</Text><Text style={[s.dayChipDate, i === day && { color: "#cdd9ee" }]}>{dd.date}</Text>
          <View style={{ flexDirection: "row", alignItems: "center", marginTop: 4 }}><Text style={[s.dayChipN, i === day && { color: "#fff" }]}>{dd.visits.length}</Text>{dd.uncovered > 0 ? <View style={s.dayDot} /> : null}</View>
        </TouchableOpacity>))}
      </ScrollView></View>
      <ScrollView style={s.body}>
        <Text style={s.section}>{sel.label} {sel.date} — {sel.visits.length} VISITE(S)</Text>
        {sel.visits.length === 0 && <Empty t="Aucune visite ce jour." />}
        {sel.visits.map((v) => (
          <TouchableOpacity key={v.id} onPress={() => v.status === "UNCOVERED" && nav.push("matches", { visitId: v.id })}>
            <Card style={{ borderLeftWidth: 4, borderLeftColor: v.status === "UNCOVERED" ? C.red : v.status === "COMPLETED" ? C.green : v.status === "IN_PROGRESS" ? C.blue : C.line }}>
              <Row><View style={{ flex: 1 }}><Text style={s.title}>{v.time}–{v.end} · {v.client}</Text><Text style={s.muted}>{v.caregiver || "Non affecté"}</Text></View><Status st={v.status} /></Row>
              {v.status === "UNCOVERED" ? <Text style={{ color: C.orangeBrand, marginTop: 6, fontWeight: "600" }}>Affecter </Text> : null}
            </Card>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}
function CoMatches({ params }) {
  const nav = useNav(); const [d, setD] = useState(null);
  useEffect(() => { (async () => { try { setD(await api(`/visits/${params.visitId}/matches/`)); } catch (e) { setD({ matches: [] }); } })(); }, []);
  if (!d) return <Center />;
  const assign = async (m) => { try { await api(`/visits/${params.visitId}/assign/`, "POST", { caregiver_id: m.caregiver_id }); Alert.alert("Affecté", `${m.code} affecté.`); nav.pop(); } catch (e) { Alert.alert("Erreur"); } };
  return (
    <ScrollView style={s.body}>
      <Text style={s.section}>MEILLEURS PROFILS — {d.client}</Text>
      {(d.matches || []).map((m, i) => (
        <Card key={i}>
          <Row><View style={{ flex: 1 }}><Text style={s.title}>{m.code} — {m.score}%</Text><Text style={s.muted}>{m.continuity} visite(s){m.km != null ? ` · ${m.km} km` : ""} · arrivée {m.arrival}%</Text></View>
            <View style={[s.status, { backgroundColor: (m.verdict === "recommended" ? C.green : m.verdict === "alternative" ? C.orange : C.red) + "1a" }]}><Text style={{ color: m.verdict === "recommended" ? C.green : m.verdict === "alternative" ? C.orange : C.red, fontWeight: "700", fontSize: 12 }}>{m.verdict === "recommended" ? "Recommandé" : m.verdict === "alternative" ? "Alt." : "Décon."}</Text></View></Row>
          <View style={{ marginTop: 10 }}><Btn t={`Affecter ${m.code}`} onPress={() => assign(m)} /></View>
        </Card>
      ))}
    </ScrollView>
  );
}
function CoRequests() {
  const h = useData("/requests/");
  if (!h.data) return <Skeleton />;
  const decide = async (r, decision) => { try { await api(`/requests/${r.id}/decide/`, "POST", { decision }); h.reload(); } catch (e) { Alert.alert("Erreur"); } };
  return (
    <ScrollView style={s.body} refreshControl={Refresher(h)}>
      <Text style={s.section}>DEMANDES DE VISITE</Text>
      {(h.data.requests || []).length === 0 && <Empty t="Aucune demande en attente." />}
      {(h.data.requests || []).map((r) => (
        <Card key={r.id}><Text style={s.title}>{r.caregiver}  {r.client}</Text><Text style={s.muted}>{r.when} · compatibilité {r.score}%</Text>
          <View style={{ flexDirection: "row", gap: 8, marginTop: 10 }}><View style={{ flex: 1 }}><Btn t="Approuver" kind="green" onPress={() => decide(r, "approve")} /></View><View style={{ flex: 1 }}><Btn t="Refuser" kind="ghost" onPress={() => decide(r, "deny")} /></View></View>
        </Card>
      ))}
    </ScrollView>
  );
}
function CoClients() {
  const [q, setQ] = useState(""); const h = useData("/clients/?q=" + encodeURIComponent(q), [q]);
  return (
    <View style={s.body}>
      <TextInput style={s.input} placeholder="Rechercher un client…" value={q} onChangeText={setQ} placeholderTextColor={C.muted} />
      {!h.data ? <Center /> : <FlatList data={h.data.clients || []} keyExtractor={(c) => String(c.id)} refreshControl={Refresher(h)}
        renderItem={({ item: c }) => (<Card><Row><View style={{ flex: 1 }}><Text style={s.title}>{c.code} — {c.name}</Text><Text style={s.muted}>{c.care}</Text>
          <Text style={{ color: C.blue, fontSize: 12, marginTop: 4 }}>Code famille : {c.family_code}{c.has_family ? "  (lié)" : "  (à partager)"}</Text></View>
          {c.pay === "paid" ? <View style={[s.status, { backgroundColor: C.green + "1a" }]}><Text style={{ color: C.green, fontWeight: "700", fontSize: 12 }}>● Payé</Text></View> : c.pay === "unpaid" ? <View style={[s.status, { backgroundColor: C.red + "1a" }]}><Text style={{ color: C.red, fontWeight: "700", fontSize: 12 }}>● Impayé</Text></View> : <Text style={s.muted}>—</Text>}</Row></Card>)}
        ListEmptyComponent={<Empty t="Aucun client." />} />}
    </View>
  );
}
function CoCopilot() {
  const [q, setQ] = useState(""); const [log, setLog] = useState([{ bot: true, t: "Bonjour ! Posez une question sur les opérations." }]);
  const ask = async () => { if (!q.trim()) return; const question = q; setQ(""); setLog((l) => [...l, { bot: false, t: question }, { bot: true, t: "…" }]); try { const r = await api("/copilot/", "POST", { q: question }); setLog((l) => [...l.slice(0, -1), { bot: true, t: r.answer }]); } catch (e) { setLog((l) => [...l.slice(0, -1), { bot: true, t: "Erreur." }]); } };
  return (
    <View style={{ flex: 1 }}>
      <ScrollView style={s.body}>{log.map((m, i) => (<View key={i} style={[s.bubble, m.bot ? s.bubbleBot : s.bubbleMe]}><Text style={{ color: m.bot ? C.ink : "#fff" }}>{m.t}</Text></View>))}</ScrollView>
      <View style={s.composer}><TextInput style={[s.input, { flex: 1, marginBottom: 0 }]} placeholder="Votre question…" value={q} onChangeText={setQ} placeholderTextColor={C.muted} /><TouchableOpacity style={s.sendBtn} onPress={ask}><Text style={{ color: "#fff", fontSize: 15, fontWeight: "700" }}>OK</Text></TouchableOpacity></View>
    </View>
  );
}
function Personnel() {
  const h = useData("/personnel/");
  if (!h.data) return <Skeleton />;
  return (
    <ScrollView style={s.body} refreshControl={Refresher(h)}>
      <Text style={s.section}>PERSONNEL DE BUREAU</Text>
      {(h.data.office || []).map((u, i) => (<Card key={i}><Row><View><Text style={s.title}>{u.name}</Text><Text style={s.muted}>{u.id}</Text></View><View style={[s.status, { backgroundColor: C.navy + "12" }]}><Text style={{ color: C.navy, fontWeight: "700", fontSize: 12 }}>{u.role}</Text></View></Row></Card>))}
      <Text style={s.section}>SOIGNANTS ({(h.data.caregivers || []).length})</Text>
      {(h.data.caregivers || []).map((c, i) => (<Card key={i}><Row><View><Text style={s.title}>{c.code} — {c.name}</Text><Text style={s.muted}>Fiabilité {c.reliability}%</Text></View>{c.has_account ? <View style={[s.status, { backgroundColor: C.green + "1a" }]}><Text style={{ color: C.green, fontWeight: "700", fontSize: 12 }}>Accès app</Text></View> : <Text style={s.muted}>Sans compte</Text>}</Row></Card>))}
    </ScrollView>
  );
}
function FamilyPortals() {
  const h = useData("/family-portals/");
  if (!h.data) return <Skeleton />;
  return (
    <ScrollView style={s.body} refreshControl={Refresher(h)}>
      <Text style={s.section}>PORTAILS FAMILIAUX</Text>
      {(h.data.clients || []).map((c, i) => (
        <Card key={i}><Row><View style={{ flex: 1 }}><Text style={s.title}>{c.code} — {c.name}</Text><Text style={s.muted}>{c.has_family ? "Compte famille lié" : "Aucun compte famille"}</Text></View>
          {c.has_family ? <View style={[s.status, { backgroundColor: C.green + "1a" }]}><Text style={{ color: C.green, fontWeight: "700", fontSize: 12 }}>● Actif</Text></View> : <Text style={s.muted}>—</Text>}</Row></Card>
      ))}
    </ScrollView>
  );
}

/* ============ FAMILY ============ */
function FaHome({ me }) {
  const h = useData("/family/");
  const [code, setCode] = useState(""); const [busy, setBusy] = useState(false);
  const link = async () => {
    if (!code.trim()) { Alert.alert("Code", "Entrez le code fourni par l'agence."); return; }
    setBusy(true);
    try { const r = await api("/link-family/", "POST", { code }); Alert.alert("Proche lié", `Vous suivez désormais les soins de ${r.client}.`); h.reload(); }
    catch (e) { Alert.alert("Erreur", e.message || "Code invalide."); }
    setBusy(false);
  };
  if (!h.data) return <Skeleton />;
  if (h.data.__err || h.data.detail) return (
    <ScrollView style={s.body}>
      <Card style={{ alignItems: "center", paddingVertical: 22 }}>
        <Avatar name={me.name} size={56} bg={C.blue} />
        <Text style={[s.title, { marginTop: 12, textAlign: "center" }]}>Bienvenue, {me.name}</Text>
        <Text style={[s.muted, { textAlign: "center", marginTop: 6 }]}>Votre compte est créé. Pour suivre les soins de votre proche en direct, liez-le avec le code fourni par l'agence.</Text>
      </Card>
      <Text style={s.section}>LIER MON PROCHE</Text>
      <Card>
        <Text style={s.lbl}>Code d'invitation</Text>
        <TextInput style={s.input} placeholder="ex. 2F4EE5" autoCapitalize="characters" value={code} onChangeText={setCode} placeholderTextColor={C.muted} />
        <Btn t={busy ? "..." : "Lier mon proche"} onPress={link} />
        <Text style={[s.muted, { marginTop: 10, fontSize: 12 }]}>Vous n'avez pas de code ? Demandez-le à votre coordinateur Panther.</Text>
      </Card>
    </ScrollView>
  );
  const d = h.data;
  return (
    <ScrollView style={s.body} refreshControl={Refresher(h)}>
      <Card style={{ backgroundColor: C.navy }}>
        <Text style={{ color: "#dbe4f2" }}>Suivi des soins de</Text><Text style={{ color: "#fff", fontSize: 22, fontWeight: "800" }}>{d.client}</Text>
        {d.wellbeing != null && <Text style={{ color: "#8ff0b6", fontWeight: "700", marginTop: 6 }}>Bien-être : {d.wellbeing}%</Text>}
      </Card>
      {d.next && <Card><Text style={s.lbl}>Prochaine visite</Text><Text style={s.title}>{d.next.when}</Text><Text style={s.muted}>Soignant : {d.next.caregiver}</Text></Card>}
      <Text style={s.section}>AUJOURD'HUI — EN DIRECT</Text>
      <Card>{(d.today || []).length === 0 && <Text style={s.muted}>Aucune visite aujourd'hui.</Text>}
        {(d.today || []).map((e, i) => (<View key={i} style={{ flexDirection: "row", alignItems: "center", paddingVertical: 8 }}><Text style={{ fontWeight: "700", width: 50 }}>{e.time}</Text><Dot c={e.tone === "g" ? C.green : e.tone === "b" ? C.blue : "#c2cad6"} /><Text style={{ flex: 1 }}>{e.text}</Text></View>))}
      </Card>
    </ScrollView>
  );
}
function FaReports() {
  const h = useData("/reports/");
  if (!h.data) return <Skeleton />;
  if (h.data.linked === false) return <NotLinked what="voir l'historique de soins" />;
  return (<ScrollView style={s.body} refreshControl={Refresher(h)}><Text style={s.section}>HISTORIQUE DE SOINS</Text>
    {(h.data.reports || []).length === 0 && <Empty t="Aucun rapport." />}
    {(h.data.reports || []).map((r, i) => (<Card key={i}><Row><Text style={s.title}>{r.date}</Text>{r.signed ? <View style={[s.status, { backgroundColor: C.green + "1a" }]}><Text style={{ color: C.green, fontWeight: "700", fontSize: 12 }}> signé</Text></View> : null}</Row><Text style={s.muted}>{r.caregiver} · {r.mood}</Text>{r.notes ? <Text style={{ marginTop: 6 }}>{r.notes}</Text> : null}</Card>))}
  </ScrollView>);
}
function FaInvoices() {
  const h = useData("/family/");
  if (!h.data) return <Skeleton />;
  if (h.data.__err || h.data.detail) return <NotLinked what="voir vos factures" />;
  const pay = async (inv) => { try { await api(`/invoices/${inv.id}/pay/`, "POST"); h.reload(); Alert.alert("Paiement confirmé", "Merci !"); } catch (e) { Alert.alert("Erreur"); } };
  return (<ScrollView style={s.body} refreshControl={Refresher(h)}><Text style={s.section}>FACTURES</Text>
    {((h.data && h.data.invoices) || []).map((inv, i) => (<Card key={i}><Row><View><Text style={s.title}>{inv.period}</Text><Text style={s.muted}>{inv.amount} $</Text></View>{inv.paid ? <View style={[s.status, { backgroundColor: C.green + "1a" }]}><Text style={{ color: C.green, fontWeight: "700", fontSize: 12 }}>● Payé</Text></View> : <View style={[s.status, { backgroundColor: C.red + "1a" }]}><Text style={{ color: C.red, fontWeight: "700", fontSize: 12 }}>● Impayé</Text></View>}</Row>
      {!inv.paid && inv.id ? <View style={{ marginTop: 10 }}><Btn t="Payer maintenant" onPress={() => pay(inv)} /></View> : null}</Card>))}
  </ScrollView>);
}

/* ============ ADMIN (manager: passwords, roles, accounts) ============ */
function Admin({ me }) {
  const nav = useNav(); const [q, setQ] = useState("");
  const h = useData("/admin/users/?q=" + encodeURIComponent(q), [q]);
  return (
    <View style={s.body}>
      <Row style={{ marginBottom: 10 }}><Text style={s.section}>UTILISATEURS &amp; ACCÈS</Text>
        <TouchableOpacity onPress={() => nav.push("newUser", {})}><Text style={{ color: C.blue, fontWeight: "700" }}>+ Nouveau</Text></TouchableOpacity></Row>
      <TextInput style={s.input} placeholder="Rechercher (nom, e-mail, ID)…" value={q} onChangeText={setQ} placeholderTextColor={C.muted} />
      {!h.data ? <Center /> : <FlatList data={h.data.users || []} keyExtractor={(u) => String(u.id)} refreshControl={Refresher(h)}
        renderItem={({ item: u }) => (
          <TouchableOpacity disabled={u.self} onPress={() => nav.push("adminUser", { user: u, reload: h.reload })}>
            <Card style={!u.active && { opacity: 0.5 }}>
              <Row><View style={{ flex: 1 }}><Text style={s.title}>{u.name}{u.self ? "  (vous)" : ""}</Text><Text style={s.muted}>@{u.username} · {u.id_number}</Text></View>
                <View style={[s.status, { backgroundColor: C.navy + "12" }]}><Text style={{ color: C.navy, fontWeight: "700", fontSize: 12 }}>{u.role_label}</Text></View></Row>
              {!u.self ? <Text style={{ color: C.blue, marginTop: 6, fontSize: 12 }}>Gérer l'accès / mot de passe </Text> : null}
            </Card>
          </TouchableOpacity>
        )} ListEmptyComponent={<Empty t="Aucun utilisateur." />} />}
    </View>
  );
}
function AdminUser({ params }) {
  const u = params.user; const rh = useData("/roles/");
  const [pw, setPw] = useState(""); const [role, setRole] = useState(u.role); const [active, setActive] = useState(u.active); const [link, setLink] = useState("");
  const resetPw = async () => { if (pw.length < 8) { Alert.alert("Mot de passe", "8 caractères minimum."); return; } try { await api(`/admin/users/${u.id}/password/`, "POST", { password: pw }); setPw(""); Alert.alert(" Mot de passe réinitialisé", `${u.name} peut se connecter avec le nouveau mot de passe.`); } catch (e) { Alert.alert("Erreur"); } };
  const setUserRole = async (r) => { try { const res = await api(`/admin/users/${u.id}/role/`, "POST", { role: r }); setRole(r); params.reload && params.reload(); Alert.alert(" Accès mis à jour", res.role_label); } catch (e) { Alert.alert("Erreur"); } };
  const toggle = async () => { try { const res = await api(`/admin/users/${u.id}/active/`, "POST"); setActive(res.active); params.reload && params.reload(); } catch (e) { Alert.alert("Erreur"); } };
  const doLink = async () => { if (!link.trim()) { Alert.alert("Client", "Entrez un code client."); return; } try { const r = await api("/admin/link-family/", "POST", { user_id: u.id, client: link }); setRole("FAMILY"); Alert.alert("Lié", `${u.name} suit désormais ${r.client}.`); params.reload && params.reload(); } catch (e) { Alert.alert("Erreur", e.message || ""); } };
  return (
    <ScrollView style={s.body}>
      <Card><Text style={s.title}>{u.name}</Text><Text style={s.muted}>@{u.username} · {u.email}</Text><Text style={s.muted}>{u.id_number}</Text></Card>
      <Text style={s.section}>ACCÈS (RÔLE)</Text>
      <Card><View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {rh.data && (rh.data.roles || []).map((r) => (<TouchableOpacity key={r.value} style={[s.roleChip, role === r.value && { backgroundColor: C.navy, borderColor: C.navy }]} onPress={() => setUserRole(r.value)}><Text style={[s.roleChipTxt, role === r.value && { color: "#fff" }]}>{r.label}</Text></TouchableOpacity>))}
      </View></Card>
      <Text style={s.section}>RÉINITIALISER LE MOT DE PASSE</Text>
      <Card><TextInput style={s.input} placeholder="Nouveau mot de passe (8+)" value={pw} onChangeText={setPw} placeholderTextColor={C.muted} /><Btn t="Réinitialiser le mot de passe" onPress={resetPw} /></Card>
      <Text style={s.section}>COMPTE</Text>
      <Card><Btn t={active ? "Désactiver le compte" : "Activer le compte"} kind={active ? "red" : "green"} onPress={toggle} /></Card>
      <Text style={s.section}>LIER À UN CLIENT (FAMILLE)</Text>
      <Card>
        <Text style={s.lbl}>Code client ou code famille</Text>
        <TextInput style={s.input} placeholder="ex. Client #014 ou 2F4EE5" value={link} onChangeText={setLink} placeholderTextColor={C.muted} />
        <Btn t="Lier ce compte au client" onPress={doLink} />
      </Card>
    </ScrollView>
  );
}
function NewUser() {
  const nav = useNav(); const rh = useData("/roles/");
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [phone, setPhone] = useState(""); const [role, setRole] = useState("COORDINATOR");
  const create = async () => { try { const r = await api("/admin/users/create/", "POST", { name, email, password: pw, phone, role }); Alert.alert(" Utilisateur créé", `${r.username} · ${r.role_label}\nN° : ${r.id_number}`); nav.pop(); } catch (e) { Alert.alert("Erreur", e.message || ""); } };
  return (
    <ScrollView style={s.body}>
      <Text style={s.section}>NOUVEL UTILISATEUR</Text>
      <Card>
        <TextInput style={s.input} placeholder="Nom complet" value={name} onChangeText={setName} placeholderTextColor={C.muted} />
        <TextInput style={s.input} placeholder="E-mail" autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} placeholderTextColor={C.muted} />
        <TextInput style={s.input} placeholder="Téléphone (optionnel)" value={phone} onChangeText={setPhone} placeholderTextColor={C.muted} />
        <TextInput style={s.input} placeholder="Mot de passe (8+)" secureTextEntry value={pw} onChangeText={setPw} placeholderTextColor={C.muted} />
        <Text style={s.lbl}>Rôle / accès</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
          {rh.data && (rh.data.roles || []).map((r) => (<TouchableOpacity key={r.value} style={[s.roleChip, role === r.value && { backgroundColor: C.navy, borderColor: C.navy }]} onPress={() => setRole(r.value)}><Text style={[s.roleChipTxt, role === r.value && { color: "#fff" }]}>{r.label}</Text></TouchableOpacity>))}
        </View>
        <Btn t="Créer l'utilisateur" kind="green" onPress={create} />
      </Card>
    </ScrollView>
  );
}

/* ============ tab config (5 tabs, mockup-style) ============ */
const TABS = {
  CAREGIVER: [["Accueil", "home", CgHome], ["Planning", "calendar", CgPlanning], ["EVV", "pin", CgEVV], ["Messages", "message", Messages], ["Plus", "grid", Plus]],
  FAMILY: [["Accueil", "home", FaHome], ["Rapports", "file", FaReports], ["Factures", "card", FaInvoices], ["Messages", "message", Messages], ["Plus", "grid", Plus]],
  MANAGER: [["Accueil", "home", CoHome], ["Planning", "calendar", CoSchedule], ["Demandes", "inbox", CoRequests], ["Clients", "users", CoClients], ["Plus", "grid", Plus]],
};
TABS.ADMIN = TABS.COORDINATOR = TABS.SUPERVISOR = TABS.FINANCE = TABS.CLINICAL = TABS.MANAGER;
const DETAIL = {
  visitDetail: VisitDetail, carenotes: CareNotes, incident: Incident, matches: CoMatches,
  profile: Profile, personnel: Personnel, familyPortals: FamilyPortals, copilot: CoCopilot,
  requests: CoRequests, cgplanning: CgPlanning, reports: FaReports, invoices: FaInvoices,
  admin: Admin, adminUser: AdminUser, newUser: NewUser,
};

/* ============ root ============ */
export default function App() {
  const [me, setMe] = useState(null); const [ready, setReady] = useState(false); const [locked, setLocked] = useState(false);
  const [tab, setTab] = useState(0); const [stack, setStack] = useState([]);
  const unlock = async () => { const ok = await biometricUnlock(); if (ok) setLocked(false); };
  useEffect(() => { (async () => {
    await loadBase(); TOKEN = await AsyncStorage.getItem("tok"); const m = await AsyncStorage.getItem("me");
    if (TOKEN && m) {
      try { await api("/me/"); setMe(JSON.parse(m)); flushQueue(); registerPush();
        const bio = await AsyncStorage.getItem("bio");
        if (bio === "1") { setLocked(true); const ok = await biometricUnlock(); if (ok) setLocked(false); }
      } catch (e) { TOKEN = null; }
    }
    setReady(true);
  })(); }, []);
  const onLogin = async (d) => { setMe(d); flushQueue(); registerPush(); };
  const logout = async () => { try { await api("/logout/", "POST"); } catch (e) {} TOKEN = null; await AsyncStorage.multiRemove(["tok", "me"]); setMe(null); setTab(0); setStack([]); };
  const nav = { push: (name, params) => setStack((x) => [...x, { name, params }]), pop: () => setStack((x) => x.slice(0, -1)), setTab: (i) => { setStack([]); setTab(i); } };
  if (!ready) return <SafeAreaView style={s.app}><Center /></SafeAreaView>;
  if (!me) return <SafeAreaView style={s.app}><StatusBar barStyle="dark-content" /><Login onLogin={onLogin} /></SafeAreaView>;
  if (locked) return <SafeAreaView style={s.app}><View style={s.center}><Image source={require("./assets/logo.jpg")} style={{ width: 120, height: 120 }} resizeMode="contain" /><Text style={{ color: C.ink, fontWeight: "700", marginVertical: 14 }}>Application verrouillée</Text><View style={{ width: 220 }}><Btn t="Déverrouiller" onPress={unlock} /></View></View></SafeAreaView>;
  const tabs = TABS[me.role] || TABS.MANAGER;
  const detail = stack[stack.length - 1]; const DetailScreen = detail ? DETAIL[detail.name] : null; const TabScreen = tabs[tab][2];
  return (
    <Nav.Provider value={nav}>
      <SafeAreaView style={s.app}>
        <StatusBar barStyle="light-content" />
        <View style={s.topbar}>
          {detail ? <TouchableOpacity onPress={nav.pop} style={{ paddingRight: 8 }}><Text style={{ color: "#fff", fontSize: 24 }}>‹</Text></TouchableOpacity> : <Image source={require("./assets/logo.jpg")} style={s.tbLogo} resizeMode="contain" />}
          <View style={{ flex: 1 }}><Text style={s.tbTitle}>{detail ? "Détail" : tabs[tab][0]}</Text><Text style={s.tbSub}>{me.name} · {me.role_label}</Text></View>
          <TouchableOpacity onPress={logout} style={s.logoutBtn}><Text style={s.logoutTxt}>Sortir</Text></TouchableOpacity>
        </View>
        <View style={{ flex: 1 }}>{DetailScreen ? <DetailScreen params={detail.params} me={me} /> : <TabScreen me={me} />}</View>
        {!detail && <View style={s.tabbar}>{tabs.map(([label, icon], i) => (
          <TouchableOpacity key={i} style={s.tab} onPress={() => setTab(i)}>
            <View style={[s.tabInd, tab === i && { backgroundColor: C.blue }]} />
            <Icon name={icon} size={20} color={tab === i ? C.blue : C.muted} />
            <Text style={[s.tabLbl, tab === i && { color: C.blue, fontWeight: "700" }]}>{label}</Text>
          </TouchableOpacity>
        ))}</View>}
      </SafeAreaView>
    </Nav.Provider>
  );
}

/* ============ styles ============ */
const s = StyleSheet.create({
  app: { flex: 1, backgroundColor: C.bg },
  center: { flex: 1, justifyContent: "center", alignItems: "center", paddingVertical: 60 },
  topbar: { backgroundColor: C.navy, paddingHorizontal: 14, paddingVertical: 12, flexDirection: "row", alignItems: "center" },
  tbLogo: { width: 30, height: 30, marginRight: 8, borderRadius: 6, backgroundColor: "#fff" },
  tbTitle: { color: "#fff", fontSize: 17, fontWeight: "800" }, tbSub: { color: "#9fb0cc", fontSize: 11, marginTop: 1 },
  logoutBtn: { borderWidth: 1, borderColor: "#33456a", borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 }, logoutTxt: { color: "#cdd9ee", fontSize: 12, fontWeight: "600" },
  tabbar: { flexDirection: "row", backgroundColor: "#fff", borderTopWidth: 1, borderTopColor: C.line, paddingBottom: 8, paddingTop: 7 },
  tab: { flex: 1, alignItems: "center" }, tabLbl: { fontSize: 10.5, color: C.muted, marginTop: 3 },
  body: { flex: 1, padding: 14 },
  loginWrap: { padding: 26, paddingTop: 40 }, logoImg: { width: 150, height: 150, alignSelf: "center", marginBottom: 6 },
  h1: { fontSize: 25, fontWeight: "800", color: C.ink, textAlign: "center" }, sub: { color: C.muted, textAlign: "center", marginTop: 6, marginBottom: 20 },
  link: { textAlign: "center", color: C.muted, fontSize: 14 },
  roleBtn: { flex: 1, borderWidth: 1, borderColor: C.line, borderRadius: 11, paddingVertical: 13, alignItems: "center", backgroundColor: "#fff" }, roleBtnOn: { backgroundColor: C.navy, borderColor: C.navy }, roleTxt: { fontSize: 14, fontWeight: "700", color: C.ink },
  input: { backgroundColor: "#fff", borderWidth: 1, borderColor: C.line, borderRadius: 11, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15, marginBottom: 12, color: C.ink },
  err: { color: C.red, marginBottom: 10, textAlign: "center" },
  bigBtn: { borderRadius: 12, alignItems: "center", justifyContent: "center", paddingVertical: 15 }, bigBtnTxt: { fontWeight: "700", fontSize: 15.5 },
  card: { backgroundColor: C.card, borderRadius: 14, padding: 15, marginBottom: 12, borderWidth: 1, borderColor: C.line, shadowColor: "#0e1c38", shadowOpacity: 0.05, shadowRadius: 8, shadowOffset: { width: 0, height: 3 }, elevation: 2 },
  hello: { fontSize: 22, fontWeight: "800", color: C.ink }, subInline: { color: C.muted, marginBottom: 14, marginTop: 2 },
  cardLabel: { fontSize: 11, fontWeight: "800", color: C.muted, letterSpacing: 0.4 },
  todayCell: { alignItems: "center", flex: 1 }, todayN: { fontSize: 24, fontWeight: "800", color: C.ink }, todayL: { fontSize: 11, color: C.muted, marginTop: 2 },
  section: { fontSize: 12, fontWeight: "800", color: C.muted, marginTop: 10, marginBottom: 10, letterSpacing: 0.4 },
  lbl: { fontSize: 13, fontWeight: "700", color: C.ink, marginBottom: 8, marginTop: 6 },
  title: { fontSize: 15.5, fontWeight: "700", color: C.ink }, muted: { color: C.muted, fontSize: 13 },
  acHead: { fontSize: 11, fontWeight: "800", color: C.muted, marginBottom: 2 },
  status: { borderRadius: 20, paddingHorizontal: 11, paddingVertical: 4 },
  warnBox: { backgroundColor: "#fdf6e3", borderWidth: 1, borderColor: "#f5e2a8", borderRadius: 12, padding: 14, marginBottom: 12 },
  warnTitle: { fontWeight: "800", color: "#8a6d1a" }, warnTxt: { color: "#8a6d1a", marginTop: 4 },
  kpiGrid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between" },
  kpi: { backgroundColor: C.card, borderRadius: 14, padding: 13, width: "31.5%", marginBottom: 10, borderWidth: 1, borderColor: C.line, shadowColor: "#0e1c38", shadowOpacity: 0.05, shadowRadius: 6, shadowOffset: { width: 0, height: 2 }, elevation: 2 },
  kpiVal: { fontSize: 21, fontWeight: "800", color: C.ink }, kpiLbl: { fontSize: 10.5, color: C.muted, marginTop: 1 },
  kpiIcon: { width: 30, height: 30, borderRadius: 9, alignItems: "center", justifyContent: "center", marginBottom: 8 },
  okCard: { flexDirection: "row", alignItems: "center", backgroundColor: "#e8f6ee", borderRadius: 12, padding: 14, marginBottom: 12 },
  qaBtn: { width: "23%", alignItems: "center" }, qaIcon: { width: 52, height: 52, borderRadius: 15, backgroundColor: "#fff", borderWidth: 1, borderColor: C.line, alignItems: "center", justifyContent: "center" }, qaLbl: { fontSize: 11, color: C.ink, marginTop: 6, fontWeight: "600" },
  timeRow: { flexDirection: "row", alignItems: "center", paddingVertical: 9 }, timeH: { width: 48, fontWeight: "700", color: C.ink }, timeDot: { width: 9, height: 9, borderRadius: 5, marginRight: 10 },
  emptyIcon: { width: 46, height: 46, borderRadius: 23, backgroundColor: "#eef1f6", alignItems: "center", justifyContent: "center" },
  skelCard: { backgroundColor: "#fff", borderRadius: 14, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: C.line }, skelBar: { height: 12, borderRadius: 6, backgroundColor: "#e9edf3" },
  taskRow: { flexDirection: "row", alignItems: "center", paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: C.line },
  radioRow: { flexDirection: "row", alignItems: "center", paddingVertical: 9 }, radio: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: C.line, marginRight: 12, alignItems: "center", justifyContent: "center" }, radioDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: C.blue },
  choice: { borderWidth: 1, borderColor: C.line, borderRadius: 11, paddingVertical: 13, paddingHorizontal: 14, marginBottom: 8 },
  sevBtn: { flex: 1, borderWidth: 1, borderColor: C.line, borderRadius: 10, paddingVertical: 11, alignItems: "center", backgroundColor: "#fff" },
  evvPolicy: { flexDirection: "row", justifyContent: "space-around", marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: C.line }, evvPolicyItem: { color: C.green, fontSize: 12, fontWeight: "600" },
  bubble: { maxWidth: "82%", padding: 11, borderRadius: 13, marginBottom: 8 }, bubbleBot: { alignSelf: "flex-start", backgroundColor: "#fff", borderWidth: 1, borderColor: C.line }, bubbleMe: { alignSelf: "flex-end", backgroundColor: C.blue },
  composer: { flexDirection: "row", gap: 8, padding: 10, backgroundColor: "#fff", borderTopWidth: 1, borderTopColor: C.line, alignItems: "center" }, sendBtn: { width: 46, height: 46, borderRadius: 12, backgroundColor: C.blue, alignItems: "center", justifyContent: "center" },
  weekHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: "#fff", paddingHorizontal: 14, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: C.line },
  weekNav: { width: 38, height: 38, borderRadius: 10, backgroundColor: C.bg, alignItems: "center", justifyContent: "center" }, weekNavTxt: { fontSize: 24, color: C.navy, marginTop: -3 }, weekLabel: { fontSize: 15, fontWeight: "800", color: C.ink },
  dayStrip: { backgroundColor: "#fff", paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: C.line },
  dayChip: { width: 58, borderRadius: 12, borderWidth: 1, borderColor: C.line, paddingVertical: 8, alignItems: "center", marginHorizontal: 4 },
  dayChipLbl: { fontSize: 12, fontWeight: "700", color: C.ink }, dayChipDate: { fontSize: 10, color: C.muted, marginTop: 1 }, dayChipN: { fontSize: 13, fontWeight: "800", color: C.orangeBrand }, dayDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: C.red, marginLeft: 4 },
  roleChip: { borderWidth: 1, borderColor: C.line, borderRadius: 20, paddingHorizontal: 13, paddingVertical: 8, backgroundColor: "#fff" }, roleChipTxt: { fontSize: 12.5, fontWeight: "600", color: C.ink },
  sigPad: { height: 150, borderWidth: 1, borderColor: C.line, borderRadius: 11, backgroundColor: "#fcfdff", overflow: "hidden" },
  sigClear: { alignSelf: "flex-end", paddingVertical: 6, paddingHorizontal: 4, marginBottom: 4 },
  pinDot: { width: 22, height: 22, borderRadius: 11, backgroundColor: C.blue, alignSelf: "center", marginBottom: 6 },
  tabInd: { width: 26, height: 3, borderRadius: 2, backgroundColor: "transparent", marginBottom: 5 },
  toggle: { width: 44, height: 24, borderRadius: 12, backgroundColor: C.line, justifyContent: "center", paddingHorizontal: 2 }, toggleDot: { width: 20, height: 20, borderRadius: 10, backgroundColor: "#fff" },
});
