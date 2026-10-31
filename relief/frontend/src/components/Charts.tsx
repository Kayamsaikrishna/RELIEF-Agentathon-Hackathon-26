import { BLOCKERS } from "../lib";
import type { Blocker } from "../api/types";

export function BlockerBars({ data }: { data: Record<string, number> }) {
  const keys = Object.keys(data) as Blocker[];
  const max = Math.max(1, ...Object.values(data));
  if (!keys.length) return <p className="muted">No diagnosed cases yet.</p>;
  return (
    <div className="bars">
      {keys.sort((a, b) => data[b] - data[a]).map((k) => (
        <div className="bar" key={k}><span>{BLOCKERS[k]?.label ?? k}</span><div className="track"><div className="fill" style={{ width: `${(data[k] / max) * 100}%` }} /></div><b>{data[k]}</b></div>
      ))}
    </div>
  );
}

export function Sparkline({ data: rawData }: { data: { day: string; n: number }[] }) {
  if (!rawData || !rawData.length) return <p className="muted">No activity yet.</p>;

  // Ensure at least a 7-day timeline so single-day entries render as a rich chart
  let data = rawData;
  if (data.length < 7 && data.length > 0) {
    const endStr = data[data.length - 1].day;
    const endDate = new Date(endStr);
    const map = new Map(data.map((d) => [d.day, d.n]));
    const days: { day: string; n: number }[] = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(endDate);
      d.setDate(d.getDate() - i);
      const iso = d.toISOString().slice(0, 10);
      days.push({ day: iso, n: map.get(iso) ?? 0 });
    }
    data = days;
  }

  const W = 520, H = 130, P = 24;
  const max = Math.max(1, ...data.map((d) => d.n));
  const x = (i: number) => P + (i * (W - 2 * P)) / (data.length - 1);
  const y = (n: number) => H - P - (n / max) * (H - 2 * P - 14);
  const line = data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d.n).toFixed(1)}`).join(" ");
  const area = `${line} L${x(data.length - 1)},${H - P} L${x(0)},${H - P} Z`;
  const total = rawData.reduce((acc, d) => acc + d.n, 0);

  return (
    <div style={{ position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6, fontSize: "12px", color: "var(--muted)" }}>
        <span>7-Day Resolution Volume</span>
        <span style={{ fontWeight: 700, color: "var(--green-700)", background: "rgba(18, 112, 95, 0.08)", padding: "2px 8px", borderRadius: "12px" }}>
          {total} {total === 1 ? "case" : "cases"} recorded
        </span>
      </div>
      <svg className="spark" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Cases per day" style={{ width: "100%", height: "auto", overflow: "visible" }}>
        <defs>
          <linearGradient id="sg" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#12705f" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#12705f" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {/* Baseline axis */}
        <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke="var(--border)" strokeWidth="1" strokeDasharray="3 3" />
        {/* Shaded Area */}
        <path d={area} fill="url(#sg)" />
        {/* Trend Line */}
        <path d={line} fill="none" stroke="#12705f" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {/* Data points & labels */}
        {data.map((d, i) => {
          const cx = x(i);
          const cy = y(d.n);
          return (
            <g key={d.day}>
              {d.n > 0 && (
                <text x={cx} y={cy - 8} textAnchor="middle" fontSize="11" fontWeight="700" fill="#12705f">
                  {d.n}
                </text>
              )}
              <circle cx={cx} cy={cy} r={d.n > 0 ? "5" : "3"} fill={d.n > 0 ? "#12705f" : "#fff"} stroke="#12705f" strokeWidth="2">
                <title>{d.day}: {d.n} cases</title>
              </circle>
              {(i === 0 || i === Math.floor(data.length / 2) || i === data.length - 1) && (
                <text x={cx} y={H - 4} textAnchor="middle" fontSize="11" fill="var(--muted)">
                  {d.day.slice(5)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
