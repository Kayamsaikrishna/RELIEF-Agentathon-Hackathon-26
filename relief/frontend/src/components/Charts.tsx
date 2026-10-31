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

export function Sparkline({ data }: { data: { day: string; n: number }[] }) {
  if (!data.length) return <p className="muted">No activity yet.</p>;
  const W = 520, H = 120, P = 18;
  const max = Math.max(1, ...data.map((d) => d.n));
  const x = (i: number) => P + (data.length === 1 ? (W - 2 * P) / 2 : (i * (W - 2 * P)) / (data.length - 1));
  const y = (n: number) => H - P - (n / max) * (H - 2 * P - 6);
  const line = data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d.n).toFixed(1)}`).join(" ");
  const area = `${line} L${x(data.length - 1)},${H - P} L${x(0)},${H - P} Z`;
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Cases per day">
      <defs><linearGradient id="sg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#65d25d" stopOpacity=".45" /><stop offset="1" stopColor="#65d25d" stopOpacity="0" /></linearGradient></defs>
      <path d={area} fill="url(#sg)" /><path d={line} fill="none" stroke="#12705f" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      {data.map((d, i) => <g key={d.day}><circle cx={x(i)} cy={y(d.n)} r="4" fill="#fff" stroke="#12705f" strokeWidth="2"><title>{d.day}: {d.n}</title></circle>{(i === 0 || i === data.length - 1) && <text x={x(i)} y={H - 2} textAnchor={i ? "end" : "start"}>{d.day.slice(5)}</text>}</g>)}
    </svg>
  );
}
