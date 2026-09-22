import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import Icon from "./Icon";
import mark from "../assets/panther-mark.png";
import type { ReactNode } from "react";

export default function Layout({ title, actions, children }:
  { title: string; actions?: ReactNode; children: ReactNode }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const doLogout = async () => { await logout(); nav("/login"); };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo-tile"><img src={mark} alt="Panther Home Care" /></div>
          <div><b>PANTHER</b><span>HOME CARE</span></div>
        </div>
        <nav className="nav">
          <NavLink to="/" end><span className="ic"><Icon name="dashboard" /></span> Tableau de bord</NavLink>
          <NavLink to="/clients"><span className="ic"><Icon name="clients" /></span> Clients</NavLink>
          <NavLink to="/analytics"><span className="ic"><Icon name="analytics" /></span> Analytique &amp; IA</NavLink>
        </nav>
        <div className="side-foot">Lubumbashi, RDC · POPIA / Loi 18/035</div>
      </aside>
      <div className="main">
        <header className="topbar">
          <h1>{title}</h1>
          <div className="top-right">
            {actions}
            <div className="whoami">
              <div className="av">{(user?.name || "?").charAt(0)}</div>
              <div>Bonjour, {user?.name}<small>{user?.role_label}</small></div>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={doLogout}>
              <Icon name="logout" size={15} /> Déconnexion
            </button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
