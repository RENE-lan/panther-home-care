import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import Icon from "../components/Icon";
import { api } from "../api";
import type { ClientRow } from "../types";

const riskClass: Record<string, string> = {
  LOW: "g", MEDIUM: "a", HIGH: "r", CRITICAL: "r",
};

export default function Clients() {
  const [rows, setRows] = useState<ClientRow[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      api.clients(q).then((r) => setRows(r.results)).finally(() => setLoading(false));
    }, 200);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <Layout title="Clients">
      <div className="card">
        <div className="searchbar">
          <span className="si"><Icon name="search" size={16} /></span>
          <input value={q} onChange={(e) => setQ(e.target.value)}
                 placeholder="Rechercher par nom ou code…" />
        </div>
        <table>
          <thead><tr><th>Code</th><th>Nom</th><th>Type de soins</th><th>Langue</th><th>Risque</th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td><b>{c.code}</b></td>
                <td>{c.name}</td>
                <td>{c.care_type || "—"}</td>
                <td>{c.language || "—"}</td>
                <td><span className={"risk " + (riskClass[c.risk] || "n")}>{c.risk_label}</span></td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr><td colSpan={5} className="empty">Aucun client trouvé.</td></tr>)}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
