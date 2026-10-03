import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import logo from "../assets/panther-logo-full.png";
import mark from "../assets/panther-mark.png";

const socials = [
  { id: "google", label: "Google" },
  { id: "apple", label: "Apple" },
  { id: "facebook", label: "Facebook" },
];

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try { await login(username, password); nav("/"); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <div className="auth-split">
      <aside className="auth-hero">
        <div className="brand">
          <div className="logo-tile lg"><img src={mark} alt="Panther Home Care" /></div>
          <div><b>PANTHER</b><span>HOME CARE</span></div>
        </div>
        <div className="auth-hero-mid">
          <h2>La plateforme intelligente<br />de gestion des soins à domicile.</h2>
          <p>Coordination, affectation par IA et supervision qualité — dans un seul espace de travail.</p>
        </div>
        <div className="auth-hero-foot">Lubumbashi, RDC · Conforme POPIA / Loi 18/035</div>
      </aside>

      <main className="auth-panel">
        <div className="auth-card">
          <img className="auth-logo" src={logo} alt="Panther Home Care" />
          <h1>Content de vous revoir</h1>
          <p className="auth-sub">Connectez-vous à votre espace de coordination.</p>

          <div className="social-row">
            {socials.map((s) => (
              <div key={s.id} className="social-btn">{s.label}</div>
            ))}
          </div>
          <div className="social-note">Connexion sécurisée via OAuth.</div>
          <div className="auth-divider"><span>ou avec une adresse e-mail</span></div>

          <form className="authform" onSubmit={submit}>
            {err && <div className="err">{err}</div>}
            <label>Identifiant</label>
            <input value={username} onChange={(e) => setU(e.target.value)}
                   placeholder="Nom d'utilisateur ou e-mail" autoFocus />
            <label>Mot de passe</label>
            <div className="pw-wrap">
              <input type={show ? "text" : "password"} value={password}
                     onChange={(e) => setP(e.target.value)} placeholder="Mot de passe" />
              <button type="button" className="pw-toggle" onClick={() => setShow(!show)}>
                {show ? "Masquer" : "Afficher"}</button>
            </div>
            <button className="btn btn-approve authsubmit" disabled={busy}>
              {busy ? "Connexion…" : "Se connecter"}</button>
          </form>
        </div>
      </main>
    </div>
  );
}
