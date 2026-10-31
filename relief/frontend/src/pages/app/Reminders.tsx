import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, Check } from "lucide-react";
import { api } from "../../api/client";
import type { Reminder } from "../../api/types";
import { Empty, Skeleton, useToast } from "../../components/ui";
import { fmtDateTime } from "../../lib";

export default function Reminders() {
  const [rows, setRows] = useState<Reminder[] | null>(null);
  const toast = useToast();
  const load = () => api<Reminder[]>("/reminders").then(setRows).catch(() => setRows([]));
  useEffect(() => { load(); }, []);
  const done = async (id: number) => { try { await api(`/reminders/${id}/done`, { method: "POST", body: {} }); toast("Marked done"); load(); } catch (e) { toast((e as Error).message, true); } };
  const groups = [["due", "Due now"], ["pending", "Coming up"], ["done", "Done"]] as const;
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <div className="page-h"><div><h1>Reminders</h1><p>Follow-ups set when you approved a case.</p></div></div>
      {rows === null ? <Skeleton h={90} /> : rows.length === 0 ? <div className="card"><Empty icon={<Bell size={36} color="var(--faint)" />} title="No reminders yet">When you approve a plan, a follow-up reminder is created for the case.</Empty></div> :
        groups.map(([k, label]) => { const g = rows.filter((r) => r.state === k); return g.length ? (
          <div className="card" key={k}><div className="card-h"><h3>{label}</h3><span className="badge muted">{g.length}</span></div>
            {g.map((r) => <div className="list-row" key={r.id}><Bell size={18} color={k === "due" ? "var(--orange-600)" : "var(--faint)"} /><div className="grow"><Link to={`/app/cases/${r.case_id}`}><b>{r.case_id}</b></Link><small>{r.message} · {k === "done" ? "done" : `due ${fmtDateTime(r.due_at)}`}</small></div>
              {k !== "done" && <button className="btn btn-ghost btn-sm" onClick={() => done(r.id)}><Check size={14} /> Done</button>}</div>)}</div>) : null; })}
    </div>
  );
}
