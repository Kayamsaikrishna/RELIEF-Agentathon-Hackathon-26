import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bell, CheckCircle2, FolderOpen, Hand, PlusCircle, Stamp } from "lucide-react";
import { api } from "../../api/client";
import type { CaseRow, Reminder, Stats } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { BlockerBars, Sparkline } from "../../components/Charts";
import { BlockerBadge, Empty, Skeleton, StatusBadge } from "../../components/ui";
import { ago } from "../../lib";

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [cases, setCases] = useState<CaseRow[] | null>(null);
  const [rem, setRem] = useState<Reminder[]>([]);
  useEffect(() => {
    api<Stats>("/stats").then(setStats).catch(() => {});
    api<CaseRow[]>("/cases?limit=50").then(setCases).catch(() => setCases([]));
    api<Reminder[]>("/reminders?state=due").then(setRem).catch(() => {});
  }, []);
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const wait = (cases ?? []).filter((c) => c.status === "awaiting_approval");
  const s = stats?.by_status ?? {};
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <div className="page-h"><div><h1>{greet}, {user?.name.split(" ")[0]}.</h1><p>Here is where your cases stand.</p></div>
        <Link className="btn btn-primary" to="/app/cases/new"><PlusCircle size={18} /> New case</Link></div>
      <div className="grid g4">
        {[["Total cases", stats?.total, <FolderOpen size={24} />, "ink"], ["Need your approval", s.awaiting_approval ?? 0, <Stamp size={24} />, "orange"],
          ["Completed", s.completed ?? 0, <CheckCircle2 size={24} />, "green"], ["Handed to a person", s.handover ?? 0, <Hand size={24} />, "red"]].map(([l, v, ic, tone]) => (
          <div className="card kpi" key={l as string}><div className={`ic ${tone}`}>{ic}</div><div>{stats ? <b>{v as number}</b> : <Skeleton h={30} w="50px" />}<span>{l as string}</span></div></div>
        ))}
      </div>
      <div className="grid" style={{ gridTemplateColumns: "minmax(0,1.4fr) minmax(0,1fr)" }}>
        <div className="card">
          <div className="card-h"><h3>Waiting for your decision</h3><Link to="/app/cases?status=awaiting_approval" className="btn btn-ghost btn-sm">All <ArrowRight size={14} /></Link></div>
          {cases === null ? <div className="card-pad"><Skeleton h={50} /></div> : wait.length === 0 ? <Empty icon={<CheckCircle2 size={34} color="var(--green-600)" />} title="Nothing waiting">New cases that need approval will appear here.</Empty> :
            wait.slice(0, 6).map((c) => (
              <Link key={c.case_id} className="list-row" to={`/app/cases/${c.case_id}`}><div className="grow"><b>{c.case_id}</b><small>{ago(c.created_at)}</small></div><BlockerBadge b={c.main_blocker} /><StatusBadge s={c.status} /></Link>))}
        </div>
        <div className="card">
          <div className="card-h"><h3>Reminders due</h3><Link to="/app/reminders" className="btn btn-ghost btn-sm">All <ArrowRight size={14} /></Link></div>
          {rem.length === 0 ? <Empty icon={<Bell size={32} color="var(--faint)" />} title="No reminders due">Follow-ups you set after approving a case show up here.</Empty> :
            rem.slice(0, 5).map((r) => <Link key={r.id} to={`/app/cases/${r.case_id}`} className="list-row"><Bell size={18} color="var(--orange-600)" /><div className="grow"><b>{r.case_id}</b><small>{r.message}</small></div></Link>)}
        </div>
      </div>
      <div className="grid g2">
        <div className="card card-pad"><h3 style={{ marginBottom: 16 }}>What is blocking cases</h3>{stats ? <BlockerBars data={stats.by_blocker} /> : <Skeleton h={120} />}</div>
        <div className="card card-pad"><h3 style={{ marginBottom: 8 }}>Cases per day</h3>{stats ? <Sparkline data={stats.daily} /> : <Skeleton h={120} />}</div>
      </div>
    </div>
  );
}
