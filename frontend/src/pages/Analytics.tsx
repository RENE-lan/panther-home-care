import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { api } from "../api";
import type { Analytics as A } from "../types";

// Lightweight inline-SVG charts (no external chart dependency).
function BarChart({ labels, values, color = "#0e1c38" }:
  { labels: string[]; values: number[]; color?: string }) {
  const max = Math.max(1, ...values);
  const W = 520, H = 180, pad = 24, bw = (W - pad * 2) / values.length;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="svgchart">
      {values.map((v, i) => {
        const h = (v / max) * (H - pad * 2);
        return (
          <g key={i}>
            <rect x={pad + i * bw + bw * 0.15} y={H - pad - h}
                  width={bw * 0.7} height={h} rx={3} fill={color} />
            {i % 2 === 0 && (
              <text x={pad + i * bw + bw / 2} y={H - 6} fontSize="9"
                    fill="#6b7688" textAnchor="middle">{labels[i]}</text>)}
          </g>
        );
      })}
    </svg>
  );
}

function LineChart({ values, color = "#e8622a" }: { values: number[]; color?: string }) {
  const max = Math.max(1, ...values), min = Math.min(...values);
  const W = 520, H = 180, pad = 24;
  const pts = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (W - pad * 2);
    const y = H - pad - ((v - min) / (max - min || 1)) * (H - pad * 2);
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="svgchart">
      <polyline points={pts} fill="none" stroke={color} strokeWidth={2.4}
                strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Analytics() {
  const [a, setA] = useState<A | null>(null);
  useEffect(() => { api.analytics(14).then(setA).catch(() => {}); }, []);
  if (!a) return <Layout title="Analytique & IA"><div className="loading">Chargement…</div></Layout>;

  return (
    <Layout title="Analytique & Intelligence">
      <div className="kpis kpis-5">
        <Kpi label="Taux d'utilisation" val={a.kpi.utilization + "%"} sub="Effectif / 30 j" />
        <Kpi label="Visites / jour" val={a.kpi.avg_visits_day} sub="Moyenne 14 j" />
        <Kpi label="Satisfaction" val={a.kpi.satisfaction + "%"} sub="Humeur clients" />
        <Kpi label="Visites terminées" val={a.kpi.completed_30} sub="30 derniers jours" />
        <Kpi label="Incidents ouverts" val={a.kpi.open_incidents} sub="À traiter" />
      </div>
      <div className="chart-grid">
        <div className="card chart-card">
          <div className="head"><h2>Volume des visites (14 j)</h2></div>
          <div className="body"><BarChart labels={a.labels} values={a.visits_total} /></div>
        </div>
        <div className="card chart-card">
          <div className="head"><h2>Signalements IA (14 j)</h2><span className="chip">IA</span></div>
          <div className="body"><LineChart values={a.flags} /></div>
        </div>
        <div className="card chart-card">
          <div className="head"><h2>Satisfaction / humeur (14 j)</h2></div>
          <div className="body"><LineChart values={a.mood} color="#2b6cb0" /></div>
        </div>
        <div className="card chart-card">
          <div className="head"><h2>Charge des soignants — top 8</h2></div>
          <div className="body"><BarChart labels={a.occ_labels.map((s) => s.replace("Soignant #", "#"))}
                                          values={a.occ_hours} /></div>
        </div>
      </div>
    </Layout>
  );
}

function Kpi({ label, val, sub }: { label: string; val: string | number; sub: string }) {
  return <div className="kpi"><div className="label">{label}</div>
    <div className="val">{val}</div><div className="delta">{sub}</div></div>;
}
