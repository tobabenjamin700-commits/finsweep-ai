"use client";
import { useEffect, useState } from "react";

const card = { background: "#131a26", border: "1px solid #232d3f", borderRadius: 12, padding: 20 };
const color = { BUY: "#22c55e", SELL: "#ef4444", WAIT: "#f59e0b" };

export default function Home() {
  const [tab, setTab] = useState("dash");
  const [s, setS] = useState(null);
  const [h, setH] = useState({ open: [], closed: [] });

  useEffect(() => {
    const load = async () => {
      setS(await (await fetch("/api/engine/status")).json());
      if (tab === "history") setH(await (await fetch("/api/engine/history")).json());
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [tab]);

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginTop: 0 }}>FibSweep <span style={{ color: "#38bdf8" }}>AI</span></h1>
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {["dash", "history"].map((t) => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: "8px 16px", borderRadius: 8, border: 0, cursor: "pointer",
                     background: tab === t ? "#38bdf8" : "#1b2433", color: tab === t ? "#04121d" : "#e6e9ef" }}>
            {t === "dash" ? "Dashboard" : "History"}
          </button>
        ))}
      </div>

      {tab === "dash" && s && (
        <div style={{ display: "grid", gap: 16 }}>
          <div style={{ ...card, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ color: "#8b97ab", fontSize: 13 }}>cTrader connection</div>
              <b style={{ color: s.connected ? "#22c55e" : "#ef4444" }}>{s.connected ? "● Connected" : "● Disconnected"}</b>
            </div>
            {!s.connected && <a href="/api/auth/ctrader/login" style={{ color: "#38bdf8" }}>Connect cTrader →</a>}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            <div style={card}><div style={{ color: "#8b97ab", fontSize: 13 }}>Live balance</div><h2>${(s.balance || 0).toFixed(2)}</h2></div>
            <div style={card}><div style={{ color: "#8b97ab", fontSize: 13 }}>Locked capital</div><h2>${(s.initial || 0).toFixed(2)}</h2></div>
            <div style={card}><div style={{ color: "#8b97ab", fontSize: 13 }}>House money</div>
              <h2 style={{ color: (s.profit || 0) > 0 ? "#22c55e" : "#8b97ab" }}>${(s.profit || 0).toFixed(2)}</h2></div>
          </div>
          {Object.entries(s.signals || {}).map(([sym, g]) => (
            <div key={sym} style={card}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <b>{sym}</b><b style={{ color: color[g.signal] }}>{g.signal}</b>
              </div>
              <p style={{ color: "#8b97ab", marginBottom: 0 }}>{g.explanation}</p>
            </div>
          ))}
          {s.error && <div style={{ ...card, borderColor: "#7f1d1d", color: "#fca5a5" }}>{s.error}</div>}
        </div>
      )}

      {tab === "history" && (
        <div style={{ display: "grid", gap: 16 }}>
          <Table title="Open positions" rows={h.open} cols={["id", "symbolId", "side", "volume", "entry", "sl", "tp"]} />
          <Table title="Closed trades (30d)" rows={h.closed} cols={["id", "symbolId", "side", "price", "pnl", "time"]} />
        </div>
      )}
    </main>
  );
}

function Table({ title, rows, cols }) {
  return (
    <div style={card}>
      <b>{title}</b>
      <table style={{ width: "100%", marginTop: 10, fontSize: 13, borderCollapse: "collapse" }}>
        <thead><tr>{cols.map((c) => <th key={c} style={{ textAlign: "left", color: "#8b97ab", padding: 4 }}>{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{cols.map((c) => <td key={c} style={{ padding: 4 }}>{c === "time" ? new Date(r[c]).toLocaleString() : String(r[c] ?? "-")}</td>)}</tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p style={{ color: "#8b97ab" }}>Nothing yet.</p>}
    </div>
  );
}
