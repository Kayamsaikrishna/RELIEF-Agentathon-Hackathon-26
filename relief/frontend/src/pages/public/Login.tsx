import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, ArrowLeft, ShieldCheck, Zap, Shield, CheckCircle2, Lock } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { Alert, Brand, Spinner } from "../../components/ui";

export default function Login() {
  const { user, login, register } = useAuth();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [role, setRole] = useState<"facilitator" | "admin">("facilitator");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={loc.state?.from ?? (user.role === "admin" ? "/admin" : "/app")} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "register") {
        if (!name.trim()) throw new Error("Full name is required.");
        if (!email.trim() || !email.includes("@")) throw new Error("Please enter a valid email address.");
        if (pw.length < 8) throw new Error("Password must be at least 8 characters long.");
        const u = await register(name.trim(), email.trim(), pw, role);
        nav(loc.state?.from ?? (u.role === "admin" ? "/admin" : "/app"), { replace: true });
      } else {
        const u = await login(email.trim(), pw);
        nav(loc.state?.from ?? (u.role === "admin" ? "/admin" : "/app"), { replace: true });
      }
    } catch (x) {
      setErr((x as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      {/* Left Artwork & Authority Showcase Panel */}
      <aside className="login-art">
        <div className="login-art-top">
          <Brand to="/" />
          <span className="eyebrow-dark">
            <Lock size={13} /> 100% Offline Local Model
          </span>
        </div>

        <div className="login-art-body">
          <div className="login-kicker">Arogya Mitra Co-Pilot</div>
          <h2>
            AI prepares.<br />
            <span>People decide.</span>
          </h2>
          <p className="login-art-desc">
            When cashless treatment is refused at the hospital desk, RELIEF diagnoses the reason,
            cross-checks 31 codified NHA guidelines, and pre-drafts the clearance memo.
          </p>

          <ul className="login-highlights">
            <li>
              <div className="hl-ic"><Zap size={18} /></div>
              <div>
                <b>Instant Roadblock Identification</b>
                <span>6 deterministic blockers checked in code before human review</span>
              </div>
            </li>
            <li>
              <div className="hl-ic"><CheckCircle2 size={18} /></div>
              <div>
                <b>Zero Hallucination Grounding</b>
                <span>Every claim cites exact scheme circular, section & date</span>
              </div>
            </li>
            <li>
              <div className="hl-ic"><Shield size={18} /></div>
              <div>
                <b>Mandatory Human Approval Gate</b>
                <span>Nothing transmitted without facilitator sign-off</span>
              </div>
            </li>
          </ul>
        </div>

        <div className="login-quote-card">
          <div className="quote-header">
            <ShieldCheck size={22} color="var(--green)" />
            <b>Safety Boundary Guarantee</b>
          </div>
          <p>
            No automated actions without review. Every letter, dispute attestation, and escalation
            requires an authenticated Arogya Mitra or Administrator signature.
          </p>
        </div>
      </aside>

      {/* Right Sign-in Form Panel */}
      <main className="login-main">
        <div className="login-card">
          <div className="login-card-top">
            <Link to="/" className="btn btn-ghost btn-sm back-link">
              <ArrowLeft size={14} /> Back to Overview
            </Link>
          </div>

          <div className="login-header">
            <h1>{mode === "register" ? "Create Facilitator Account" : "Sign in to RELIEF"}</h1>
            <p className="muted">
              {mode === "register"
                ? "Register your official Arogya Mitra or Administrator credentials."
                : "Enter your official credentials or use 1-click evaluation access."}
            </p>
          </div>

          <div className="login-mode-tabs" style={{ display: "flex", gap: 8, background: "rgba(0,0,0,0.04)", padding: 4, borderRadius: 8, marginBottom: 16 }}>
            <button
              type="button"
              className={`btn btn-sm ${mode === "signin" ? "btn-ink" : "btn-ghost"}`}
              style={{ flex: 1 }}
              onClick={() => { setMode("signin"); setErr(""); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`btn btn-sm ${mode === "register" ? "btn-ink" : "btn-ghost"}`}
              style={{ flex: 1 }}
              onClick={() => { setMode("register"); setErr(""); }}
            >
              + Create Real Account
            </button>
          </div>

          <form className="login-form-fields" onSubmit={submit}>
            {err && <Alert kind="err">{err}</Alert>}

            {mode === "register" && (
              <>
                <div className="field">
                  <label htmlFor="name">Full Name <span className="req">*</span></label>
                  <input
                    id="name"
                    className="input"
                    type="text"
                    required
                    autoFocus
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Sai Krishna"
                  />
                </div>

                <div className="field">
                  <label htmlFor="role">Account Role <span className="req">*</span></label>
                  <select
                    id="role"
                    className="input"
                    value={role}
                    onChange={(e) => setRole(e.target.value as "facilitator" | "admin")}
                  >
                    <option value="facilitator">Arogya Mitra Facilitator (Case Intake & Approval)</option>
                    <option value="admin">Administrator (Registry, Users & Audit Logs)</option>
                  </select>
                </div>
              </>
            )}

            <div className="field">
              <label htmlFor="email">Email address <span className="req">*</span></label>
              <input
                id="email"
                className="input"
                type="email"
                autoComplete="username"
                required
                autoFocus={mode === "signin"}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. saikrishna@gmail.com"
              />
            </div>

            <div className="field">
              <label htmlFor="pw">Password <span className="req">*</span></label>
              <div style={{ position: "relative" }}>
                <input
                  id="pw"
                  className="input"
                  type={show ? "text" : "password"}
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                  required
                  value={pw}
                  onChange={(e) => setPw(e.target.value)}
                  style={{ paddingRight: 44 }}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  className="btn btn-ghost btn-sm pw-toggle"
                  aria-label={show ? "Hide password" : "Show password"}
                  onClick={() => setShow(!show)}
                >
                  {show ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {mode === "register" && <span className="hint">Minimum 8 characters.</span>}
            </div>

            <button type="submit" className="btn btn-ink btn-lg btn-block login-submit-btn" disabled={busy}>
              {busy ? <Spinner /> : mode === "register" ? "Create Account & Sign In →" : "Sign In to Workspace →"}
            </button>
          </form>

          <div className="login-footer-hint">
            {mode === "signin" ? (
              <>
                <span>Verified Account: <code>saikrishna@gmail.com</code></span>
                <p>100% offline local model · Codified NHA & PM-JAY scheme engine.</p>
              </>
            ) : (
              <p>Creates a live authenticated account in the local secure database.</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
