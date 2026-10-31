import { FormEvent, useEffect, useMemo, useState } from "react";
import { AlertTriangle, BookOpen, CheckCircle2, Database, ExternalLink, Plus, Search, Server, Users as UsersIcon, XCircle, KeyRound, Cpu, ShieldOff } from "lucide-react";
import { api } from "../../api/client";
import type { AuditRow, Hospital, Pkg, RulePassage, Stats, SystemInfo, User } from "../../api/types";
import { BlockerBars, Sparkline } from "../../components/Charts";
import { Alert, Modal, RuleBody, Skeleton, Spinner, useToast } from "../../components/ui";
import { DOC_KINDS, fmtDateTime } from "../../lib";
import { useAuth } from "../../auth/AuthContext";

const Head = ({ t, p }: { t: string; p?: string }) => <div className="page-h"><div><h1>{t}</h1>{p && <p>{p}</p>}</div></div>;
const Health = ({ ok, label, msg }: { ok: boolean; label: string; msg: string }) => (
  <div className="card card-pad"><div className="row">{ok ? <CheckCircle2 color="var(--green-600)" /> : <XCircle color="var(--red)" />}<b style={{ color: "var(--ink)" }}>{label}</b></div><p className="hint" style={{ marginTop: 8, wordBreak: "break-word" }}>{msg}</p></div>
);

export function AdminOverview() {
  const [sys, setSys] = useState<SystemInfo | null>(null);
  const [st, setSt] = useState<Stats | null>(null);
  useEffect(() => { api<SystemInfo>("/admin/system").then(setSys); api<Stats>("/stats").then(setSt); }, []);
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <Head t="Administration" p="System health, rules and users at a glance." />
      {!sys ? <Skeleton h={110} /> : <>
        {sys.registry_synthetic && <Alert kind="warn" title="Synthetic registry">The hospital registry in use is synthetic test data. Replace it with an authorised export before any real use.</Alert>}
        <div className="grid g3">
          <Health ok={sys.model_ok} label={`Language model: ${sys.model}`} msg={sys.model_ok ? sys.model_message : `${sys.model_message} The agent still works on its rule-based path.`} />
          <Health ok={sys.embedder_ok} label={`Rule search: ${sys.embedder}`} msg={sys.embedder_message} />
          <Health ok={sys.rules_checked === sys.rules} label={`Rule quotes checked: ${sys.rules_checked}/${sys.rules}`} msg={sys.rules_checked === sys.rules ? "All rule quotes were checked against the sources." : "Run scripts/verify_sources.py on a machine with internet access."} />
        </div></>}
      <div className="grid g2">
        <div className="card card-pad"><h3 style={{ marginBottom: 14 }}>Blockers found (all cases)</h3>{st ? <BlockerBars data={st.by_blocker} /> : <Skeleton h={120} />}</div>
        <div className="card card-pad"><h3 style={{ marginBottom: 8 }}>Cases per day</h3>{st ? <Sparkline data={st.daily} /> : <Skeleton h={120} />}</div>
      </div>
    </div>
  );
}

export function AdminUsers() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [rows, setRows] = useState<User[] | null>(null);
  const [add, setAdd] = useState(false);
  const [edit, setEdit] = useState<User | null>(null);
  const load = () => api<User[]>("/admin/users").then(setRows);
  useEffect(() => { load(); }, []);
  async function patch(u: User, body: Record<string, unknown>, ok: string) {
    try { await api(`/admin/users/${u.id}`, { method: "PATCH", body }); toast(ok); load(); setEdit(null); } catch (e) { toast((e as Error).message, true); }
  }
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <div className="page-h"><div><h1>Users</h1><p>Accounts are created here by an administrator. There is no public sign-up.</p></div><button className="btn btn-primary" onClick={() => setAdd(true)}><Plus size={17} /> Add user</button></div>
      <div className="card">{!rows ? <div className="card-pad"><Skeleton h={120} /></div> : <div className="table-wrap"><table className="t"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Last sign-in</th><th /></tr></thead><tbody>
        {rows.map((u) => <tr key={u.id}><td><b style={{ color: "var(--ink)" }}>{u.name}</b>{u.id === me?.id && <span className="badge ink" style={{ marginLeft: 8 }}>you</span>}</td><td>{u.email}</td><td><span className={`badge ${u.role === "admin" ? "orange" : "ink"}`}>{u.role === "admin" ? "Administrator" : "Facilitator"}</span></td>
          <td><span className={`badge ${u.active ? "green" : "muted"}`}>{u.active ? "Active" : "Disabled"}</span></td><td className="muted">{fmtDateTime(u.last_login)}</td><td><button className="btn btn-ghost btn-sm" onClick={() => setEdit(u)}>Manage</button></td></tr>)}</tbody></table></div>}</div>
      {add && <AddUser onClose={() => setAdd(false)} onDone={() => { setAdd(false); load(); toast("User created"); }} />}
      {edit && <EditUser u={edit} self={edit.id === me?.id} onClose={() => setEdit(null)} patch={patch} />}
    </div>
  );
}
function AddUser({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [f, setF] = useState({ name: "", email: "", role: "facilitator", password: "" });
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) { e.preventDefault(); setBusy(true); setErr(""); try { await api("/admin/users", { body: f }); onDone(); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); } }
  return <Modal title="Add user" onClose={onClose}><form className="stack" onSubmit={submit}>{err && <Alert kind="err">{err}</Alert>}
    <div className="field"><label htmlFor="un">Full name</label><input id="un" className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
    <div className="field"><label htmlFor="ue">Email</label><input id="ue" className="input" type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
    <div className="field"><span className="label">Role</span><div className="seg">{(["facilitator", "admin"] as const).map((r) => <button key={r} type="button" aria-pressed={f.role === r} onClick={() => setF({ ...f, role: r })}>{r === "admin" ? "Administrator" : "Facilitator"}</button>)}</div></div>
    <div className="field"><label htmlFor="up">Temporary password</label><input id="up" className="input" type="text" autoComplete="off" required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /><span className="hint">At least 10 characters with upper and lower case letters and a digit. Ask the person to change it after signing in.</span></div>
    <div className="row" style={{ justifyContent: "flex-end" }}><button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-ink" disabled={busy}>{busy ? <Spinner /> : "Create user"}</button></div></form></Modal>;
}
function EditUser({ u, self, onClose, patch }: { u: User; self: boolean; onClose: () => void; patch: (u: User, b: Record<string, unknown>, ok: string) => void }) {
  const [pw, setPw] = useState("");
  return <Modal title={u.name} onClose={onClose}><div className="stack">
    <p className="muted">{u.email}</p>
    <div className="field"><span className="label">Role</span><div className="seg">{(["facilitator", "admin"] as const).map((r) => <button key={r} aria-pressed={u.role === r} onClick={() => u.role !== r && patch(u, { role: r }, "Role updated")}>{r === "admin" ? "Administrator" : "Facilitator"}</button>)}</div></div>
    <div className="field"><label htmlFor="rp"><KeyRound size={14} /> Reset password</label><div className="row" style={{ flexWrap: "nowrap" }}><input id="rp" className="input" placeholder="New temporary password" value={pw} onChange={(e) => setPw(e.target.value)} /><button className="btn btn-ink" disabled={!pw} onClick={() => patch(u, { new_password: pw }, "Password reset")}>Reset</button></div></div>
    <div className="row" style={{ justifyContent: "space-between" }}><span className="hint">{self ? "You cannot disable your own account." : u.active ? "Disabled users cannot sign in." : "This account is disabled."}</span>
      {!self && <button className={`btn ${u.active ? "btn-danger" : "btn-green"}`} onClick={() => patch(u, { active: !u.active }, u.active ? "User disabled" : "User enabled")}><ShieldOff size={15} /> {u.active ? "Disable" : "Enable"}</button>}</div></div></Modal>;
}

export function AdminRules() {
  const [rules, setRules] = useState<RulePassage[] | null>(null);
  const [q, setQ] = useState(""); const [src, setSrc] = useState(""); const [open, setOpen] = useState<RulePassage | null>(null);
  useEffect(() => { api<RulePassage[]>("/admin/rules").then(setRules); }, []);
  const sources = useMemo(() => Array.from(new Set((rules ?? []).map((r) => r.source_id))), [rules]);
  const shown = (rules ?? []).filter((r) => (!src || r.source_id === src) && (r.rule_id + r.text + r.section).toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <Head t="Rules" p="Every rule the agent can cite: paraphrased from official documents, with its source and verification status." />
      <div className="card"><div className="filters"><div style={{ position: "relative" }}><Search size={16} style={{ position: "absolute", left: 11, top: 12, color: "var(--faint)" }} /><input className="input" style={{ paddingLeft: 34 }} placeholder="Search rules" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search rules" /></div>
        <select className="input" value={src} onChange={(e) => setSrc(e.target.value)} aria-label="Source"><option value="">All sources</option>{sources.map((s) => <option key={s}>{s}</option>)}</select>
        {rules && <span className="muted">{shown.length} of {rules.length}</span>}</div>
        {!rules ? <div className="card-pad"><Skeleton h={160} /></div> : <div className="table-wrap"><table className="t"><thead><tr><th>Rule</th><th>Source</th><th>Section</th><th>Statement</th><th>Quote</th></tr></thead><tbody>
          {shown.map((r) => <tr key={r.rule_id} className="link" onClick={() => setOpen(r)}><td><span className="chip" style={{ cursor: "pointer" }}>{r.rule_id}</span></td><td>{r.source_id}</td><td>{r.section}{r.page ? ` · p.${r.page}` : ""}</td><td style={{ maxWidth: 420 }}>{r.text}</td><td><span className={`badge ${r.quote_checked ? "green" : "orange"}`}>{r.quote_checked ? "checked" : "unchecked"}</span></td></tr>)}</tbody></table></div>}</div>
      {open && <Modal title={open.rule_id} onClose={() => setOpen(null)}><RuleBody r={open} /></Modal>}
    </div>
  );
}

export function AdminRegistry() {
  const [h, setH] = useState<Hospital[]>([]); const [p, setP] = useState<Pkg[]>([]); const [info, setInfo] = useState<{ version: string; synthetic: boolean; note: string } | null>(null);
  useEffect(() => { api<Hospital[]>("/registry/hospitals").then(setH); api<Pkg[]>("/registry/packages").then(setP); api<typeof info>("/registry/info").then(setInfo); }, []);
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <Head t="Registry" p="Hospitals and packages the agent checks against." />
      {info && <Alert kind={info.synthetic ? "warn" : "ok"} title={`Registry ${info.version}${info.synthetic ? " · synthetic test data" : ""}`}>{info.note}</Alert>}
      <div className="card"><div className="card-h"><h3><Database size={16} style={{ verticalAlign: "-3px" }} /> Hospitals</h3><span className="badge muted">{h.length}</span></div><div className="table-wrap"><table className="t"><thead><tr><th>Id</th><th>Name</th><th>Type</th><th>District</th><th>Specialities</th><th>Empanelment</th></tr></thead><tbody>
        {h.map((x) => <tr key={x.hospital_id}><td className="mono">{x.hospital_id}</td><td><b style={{ color: "var(--ink)" }}>{x.name}</b></td><td>{x.type}</td><td>{x.district}</td><td className="muted">{x.specialties.join(", ")}</td><td><span className={`badge ${x.empanelment_active ? "green" : "red"}`}>{x.empanelment_active ? "active" : "not active"}</span></td></tr>)}</tbody></table></div></div>
      <div className="card"><div className="card-h"><h3>Packages</h3><span className="badge muted">{p.length}</span></div><div className="table-wrap"><table className="t"><thead><tr><th>Code</th><th>Name</th><th>Speciality</th><th>Tier</th><th>Public only</th><th>Required documents</th></tr></thead><tbody>
        {p.map((x) => <tr key={x.code}><td className="mono">{x.code}</td><td>{x.name}</td><td>{x.specialty}</td><td><span className="badge ink">{x.tier}</span></td><td>{x.reserved_for_public ? "yes" : "no"}</td><td className="muted">{x.required_docs.map((d) => DOC_KINDS[d] ?? d).join(", ")}</td></tr>)}</tbody></table></div></div>
    </div>
  );
}

export function AdminAudit() {
  const [rows, setRows] = useState<AuditRow[] | null>(null);
  useEffect(() => { api<AuditRow[]>("/admin/audit?limit=300").then(setRows); }, []);
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <Head t="Audit log" p="Who did what, newest first. Sign-ins, case creation, decisions and account changes." />
      <div className="card">{!rows ? <div className="card-pad"><Skeleton h={160} /></div> : <div className="table-wrap"><table className="t"><thead><tr><th>When</th><th>Who</th><th>Action</th><th>Case</th><th>Detail</th></tr></thead><tbody>
        {rows.map((r) => <tr key={r.id}><td className="muted" style={{ whiteSpace: "nowrap" }}>{fmtDateTime(r.ts)}</td><td>{r.actor}</td><td><span className="chip" style={{ cursor: "default" }}>{r.action}</span></td><td className="mono">{r.case_id ?? "—"}</td><td className="muted">{r.detail}</td></tr>)}</tbody></table></div>}</div>
    </div>
  );
}

export function AdminSystem() {
  const [s, setS] = useState<SystemInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const load = () => { setBusy(true); api<SystemInfo>("/admin/system").then(setS).finally(() => setBusy(false)); };
  useEffect(load, []);
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px" }}>
      <div className="page-h"><div><h1>System</h1><p>Versions and the status of the local model and rule search.</p></div><button className="btn btn-ghost" onClick={load} disabled={busy}>{busy ? <Spinner /> : "Re-check"}</button></div>
      {!s ? <Skeleton h={200} /> : <>
        <div className="grid g2"><Health ok={s.model_ok} label={`Model ${s.model}`} msg={s.model_message} /><Health ok={s.embedder_ok} label={`Embeddings (${s.embedder})`} msg={s.embedder_message} /></div>
        {!s.model_ok && <Alert kind="info" title="How to fix">Start Ollama, then run <span className="mono">ollama pull {s.model}</span> (or set RELIEF_LLM_MODEL to a model you already have, then restart the backend).</Alert>}
        <div className="card card-pad"><dl className="kv" style={{ gridTemplateColumns: "200px 1fr" }}>
          <dt>RELIEF version</dt><dd>{s.version}</dd><dt>Python</dt><dd>{s.python}</dd><dt>Rules</dt><dd>{s.rules} ({s.rules_checked} with checked quotes)</dd><dt>Registry</dt><dd>{s.registry_version}{s.registry_synthetic ? " (synthetic)" : ""} · {s.hospitals} hospitals · {s.packages} packages</dd><dt>Users</dt><dd>{s.users}</dd></dl></div></>}
    </div>
  );
}
