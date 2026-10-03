import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import Icon from "../components/Icon";
import { api } from "../api";
import type { DashboardData } from "../types";

const SEGS = [
  ["skills", "#e8622a"], ["distance", "#2b6cb0"], ["reliability", "#1f8a4c"],
  ["punctuality", "#e59a1c"], ["workload", "#0e1c38"], ["language", "#9aa6b6"],
] as const;

export default function Dashboard() {
  const [d, setD] = useState<DashboardData | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.dashboard().then(setD).catch((e) => setErr(e.message)); }, []);

  if (err) return <Layout title="Tableau de bord"><div className="err">{err}</div></Layout>;
  if (!d) return <Layout title="Tableau de bord"><div className="loading">Chargement…</div></Layout>;

  const r = d.recommendation;
  return (
    <Layout title="Tableau de bord">
      <div className="kpis">
        <Kpi label="Clients actifs" val={d.kpis.clients} sub="Suivis en continu" />
        <Kpi label="Soignants actifs" val={d.kpis.caregivers} sub="Disponibles au planning" />
        <Kpi label="Visites aujourd'hui" val={d.kpis.visits_today} sub={`${d.kpis.completed} terminées`} />
        <Kpi label="Incidents ouverts" val={d.kpis.incidents_open}
             sub={`${d.kpis.incidents_critical} critique`} alert={d.kpis.incidents_critical > 0} />
      </div>

      <div className="grid">
        <div>
          <div className="card">
            <div className="head">
              <div className="ai-head"><span className="brain"><Icon name="ai" size={16} /></span>
                <h2>PANTHER AI CARE COORDINATOR</h2></div>
              <span className="chip">IA</span>
            </div>
            <div className="body">
              {r ? (
                <>
                  <div className="uncovered-banner">
                    <div className="t">1 VISITE NON COUVERTE</div>
                    <div className="dsc">{r.client} — {r.start}–{r.end} · Soins : {r.care_type || "—"}</div>
                  </div>
                  {r.match ? (
                    <>
                      <div className="reco">
                        <div className="av">{r.match.code.slice(-2)}</div>
                        <div className="meta">
                          <b>{r.match.code} — {r.match.name}</b>
                          <div className="sub">
                            {r.match.skills_ok ? "Compétences requises ✓ · " : ""}
                            {r.match.distance_km ? `${r.match.distance_km} km · ` : ""}
                            Charge : {r.match.workload}
                          </div>
                        </div>
                        <div className="score"><div className="n">{r.match.score}%</div><div className="l">Score IA</div></div>
                      </div>
                      <div className="xbar">
                        {SEGS.map(([k, c]) => (
                          <span key={k} className="xseg"
                                style={{ width: `${r.match!.components[k]}%`, background: c }} />
                        ))}
                      </div>
                      <div className="xcaption">Décomposition : compétences · distance · fiabilité · ponctualité · charge · langue</div>
                    </>
                  ) : <p className="empty">Aucun soignant disponible ne correspond.</p>}
                </>
              ) : <p className="empty">Toutes les visites du jour sont couvertes.</p>}
            </div>
          </div>

          <div className="card">
            <div className="head"><h2><span className="hdot a" /> ATTENTION</h2></div>
            <div className="body">
              {d.late.map((l, i) => (
                <div className="row-item" key={i}>
                  <div className="l">{l.caregiver} en retard de {l.minutes_late} min
                    <small>{l.client} · visite {l.time}</small></div>
                  <span className="pill a">Retard</span>
                </div>
              ))}
              {d.flags.map((f, i) => (
                <div className="row-item" key={"f" + i}>
                  <div className="l">{f.client} — {f.concern?.slice(0, 70)}<small>Rapport {f.time} · IA</small></div>
                </div>
              ))}
              {d.late.length === 0 && d.flags.length === 0 && <p className="empty">Rien à signaler.</p>}
            </div>
          </div>
        </div>

        <div>
          <div className="card">
            <div className="head"><div className="ai-head"><span className="brain"><Icon name="ai" size={15} /></span>
              <h2>RÉSUMÉ QUOTIDIEN PAR IA</h2></div></div>
            <div className="body">
              <div className="brief-line"><span className="dot g" />{d.brief.confirmed} soignant(s) confirmé(s) sur {d.brief.scheduled}</div>
              <div className="brief-line"><span className="dot a" />{d.brief.late} soignant(s) en retard</div>
              <div className="brief-line"><span className="dot r" />{d.brief.uncovered} visite(s) non couverte(s)</div>
              <div className="brief-line"><span className="dot b" />{d.flags.length} client(s) nécessite(nt) votre attention</div>
              <div className="brief-summary">"{d.brief.summary}"</div>
            </div>
          </div>
          <div className="card">
            <div className="head"><h2><span className="hdot r" /> CRITIQUE</h2></div>
            <div className="body">
              {d.critical.map((c, i) => (
                <div className="row-item" key={i}>
                  <div className="l">{c.title}<small>{c.client ? c.client + " · " : ""}{c.at}</small></div>
                  <span className="pill r">Critique</span>
                </div>
              ))}
              {d.critical.length === 0 && <p className="empty">Aucun incident critique.</p>}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

function Kpi({ label, val, sub, alert }: { label: string; val: number; sub: string; alert?: boolean }) {
  return (
    <div className={"kpi" + (alert ? " alert" : "")}>
      <div className="label">{label}</div>
      <div className="val">{val}</div>
      <div className="delta">{sub}</div>
    </div>
  );
}
