import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { FolderOpen, PlusCircle, Search } from "lucide-react";
import { api } from "../../api/client";
import type { CaseRow } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { BlockerBadge, Empty, Skeleton, StatusBadge } from "../../components/ui";
import { BLOCKERS, STATUS, fmtDateTime } from "../../lib";

export default function Cases() {
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [rows, setRows] = useState<CaseRow[] | null>(null);
  const [q, setQ] = useState(sp.get("q") ?? "");
  const status = sp.get("status") ?? "", blocker = sp.get("blocker") ?? "";
  useEffect(() => {
    setRows(null);
    const p = new URLSearchParams(); if (status) p.set("status", status); if (blocker) p.set("blocker", blocker); if (sp.get("q")) p.set("q", sp.get("q")!);
    api<CaseRow[]>("/cases?" + p).then(setRows).catch(() => setRows([]));
  }, [status, blocker, sp]);
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); setSp(n); };
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <div className="page-h"><div><h1>Cases</h1><p>{user?.role === "admin" ? "All cases in the system." : "Cases you created."}</p></div><Link className="btn btn-primary" to="/app/cases/new"><PlusCircle size={18} /> New case</Link></div>
      <div className="card">
        <form className="filters" onSubmit={(e) => { e.preventDefault(); set("q", q.trim()); }}>
          <div style={{ position: "relative" }}><Search size={16} style={{ position: "absolute", left: 11, top: 12, color: "var(--faint)" }} /><input className="input" style={{ paddingLeft: 34 }} placeholder="Search by case id" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search by case id" /></div>
          <select className="input" value={status} onChange={(e) => set("status", e.target.value)} aria-label="Status"><option value="">All statuses</option>{Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select>
          <select className="input" value={blocker} onChange={(e) => set("blocker", e.target.value)} aria-label="Blocker"><option value="">All blockers</option>{Object.entries(BLOCKERS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select>
        </form>
        {rows === null ? <div className="card-pad stack"><Skeleton h={40} /><Skeleton h={40} /><Skeleton h={40} /></div> : rows.length === 0 ? <Empty icon={<FolderOpen size={36} color="var(--faint)" />} title="No cases found" action={<Link className="btn btn-ink" to="/app/cases/new">Create the first case</Link>}>Try clearing the filters, or create a case.</Empty> : (
          <div className="table-wrap"><table className="t"><thead><tr><th>Case</th><th>Likely blocker</th><th>Status</th><th>Created</th>{user?.role === "admin" && <th>By</th>}</tr></thead>
            <tbody>{rows.map((c) => (
              <tr key={c.case_id} className="link" tabIndex={0} onClick={() => nav(`/app/cases/${c.case_id}`)} onKeyDown={(e) => e.key === "Enter" && nav(`/app/cases/${c.case_id}`)}>
                <td><b style={{ color: "var(--ink)" }}>{c.case_id}</b></td>
                <td><BlockerBadge b={c.main_blocker} /></td><td><StatusBadge s={c.status} /></td><td className="muted">{fmtDateTime(c.created_at)}</td>{user?.role === "admin" && <td className="muted">{c.created_by}</td>}
              </tr>))}</tbody></table></div>)}
      </div>
    </div>
  );
}
