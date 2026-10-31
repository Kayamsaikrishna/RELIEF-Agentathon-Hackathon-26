import { FormEvent, useState } from "react";
import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { Alert, Spinner, useToast } from "../../components/ui";

export default function Account() {
  const { user } = useAuth();
  const toast = useToast();
  const [cur, setCur] = useState(""); const [nw, setNw] = useState(""); const [nw2, setNw2] = useState("");
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault(); setErr("");
    if (nw !== nw2) return setErr("The new passwords do not match.");
    setBusy(true);
    try { await api("/auth/password", { body: { current: cur, new: nw } }); toast("Password changed"); setCur(""); setNw(""); setNw2(""); }
    catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }
  return (
    <div className="stack" style={{ ["--gap" as string]: "22px", maxWidth: 560 }}>
      <div className="page-h"><div><h1>Your account</h1></div></div>
      <div className="card card-pad"><dl className="kv"><dt>Name</dt><dd>{user?.name}</dd><dt>Email</dt><dd>{user?.email}</dd><dt>Role</dt><dd>{user?.role === "admin" ? "Administrator" : "Facilitator"}</dd></dl></div>
      <form className="card card-pad stack" onSubmit={submit}>
        <h3>Change password</h3>{err && <Alert kind="err">{err}</Alert>}
        <div className="field"><label htmlFor="c">Current password</label><input id="c" className="input" type="password" autoComplete="current-password" required value={cur} onChange={(e) => setCur(e.target.value)} /></div>
        <div className="field"><label htmlFor="n">New password</label><input id="n" className="input" type="password" autoComplete="new-password" required value={nw} onChange={(e) => setNw(e.target.value)} /><span className="hint">At least 10 characters with upper and lower case letters and a digit.</span></div>
        <div className="field"><label htmlFor="n2">Repeat new password</label><input id="n2" className="input" type="password" autoComplete="new-password" required value={nw2} onChange={(e) => setNw2(e.target.value)} /></div>
        <div><button className="btn btn-ink" disabled={busy}>{busy ? <Spinner /> : "Change password"}</button></div>
      </form>
    </div>
  );
}
