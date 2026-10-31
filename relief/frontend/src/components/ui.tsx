import { createContext, useCallback, useContext, useState, ReactNode, useEffect } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Info, X, Copy, Check } from "lucide-react";
import type { Blocker, CaseStatus, Confidence, RulePassage } from "../api/types";
import { BLOCKERS, STATUS } from "../lib";

export function Brand({ to = "/", sub = true }: { to?: string; sub?: boolean }) {
  return (
    <Link to={to} className="brand" aria-label="RELIEF home">
      <img src="/brand/icon-512.png" alt="" width={38} height={38} />
      <span><b>RELIEF</b>{sub && <small>FIND THE BLOCK. CLEAR THE WAY.</small>}</span>
    </Link>
  );
}

export const Spinner = () => <span className="spinner" role="status" aria-label="Loading" />;
export const Skeleton = ({ h = 20, w = "100%" }: { h?: number; w?: string }) => <div className="skeleton" style={{ height: h, width: w }} />;

export function Alert({ kind = "info", children, title }: { kind?: "info" | "warn" | "err" | "ok" | "emergency"; children: ReactNode; title?: string }) {
  const Icon = kind === "ok" ? CheckCircle2 : kind === "info" ? Info : AlertTriangle;
  return (
    <div className={`alert ${kind}`} role={kind === "err" || kind === "emergency" ? "alert" : undefined}>
      <Icon size={20} />
      <div>{title && <b style={{ display: "block", marginBottom: 2 }}>{title}</b>}{children}</div>
    </div>
  );
}

export const BlockerBadge = ({ b }: { b: Blocker | null | undefined }) =>
  b ? <span className={`badge ${BLOCKERS[b].tone === "muted" ? "muted" : BLOCKERS[b].tone}`}>{BLOCKERS[b].label}</span> : <span className="badge muted">—</span>;

export const StatusBadge = ({ s }: { s: CaseStatus }) => (
  <span className={`badge ${STATUS[s].tone}`}>{s === "running" ? <Spinner /> : <i className="dot" />}{STATUS[s].label}</span>
);

export function ConfidenceBar({ level }: { level: Confidence }) {
  const n = level === "high" ? 3 : level === "medium" ? 2 : 1;
  return <span className="row" style={{ gap: 8 }}><span className="confbar" aria-hidden>{[1, 2, 3].map((i) => <i key={i} className={i <= n ? "on" : ""} />)}</span><span className="muted" style={{ fontSize: ".8rem", fontWeight: 700 }}>{level} confidence</span></span>;
}

export function Empty({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return <div className="empty">{icon}<h4>{title}</h4><p>{children}</p>{action && <div style={{ marginTop: 16 }}>{action}</div>}</div>;
}

// ---------- toasts
type Toast = { id: number; text: string; err?: boolean };
const ToastCtx = createContext<(t: string, err?: boolean) => void>(() => {});
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, err = false) => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, text, err }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4500);
  }, []);
  return <ToastCtx.Provider value={push}>{children}<div className="toast-host" aria-live="polite">{items.map((t) => <div key={t.id} className={`toast ${t.err ? "err" : ""}`}>{t.text}</div>)}</div></ToastCtx.Provider>;
}

// ---------- modal
export function Modal({ title, onClose, children, footer }: { title: string; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-h spread"><h3>{title}</h3><button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
        <div className="modal-b">{children}</div>
        {footer && <div className="modal-f">{footer}</div>}
      </div>
    </div>
  );
}

// ---------- rule chip + viewer
export function RuleChip({ id, rules }: { id: string; rules: RulePassage[] }) {
  const [open, setOpen] = useState(false);
  const r = rules.find((x) => x.rule_id === id);
  return (
    <>
      <button className="chip" onClick={() => setOpen(true)} title="Show the rule">{id}</button>
      {open && <Modal title={id} onClose={() => setOpen(false)}>{r ? <RuleBody r={r} /> : <p className="muted">Rule text is not loaded for this item.</p>}</Modal>}
    </>
  );
}
export function RuleBody({ r }: { r: RulePassage }) {
  return (
    <div className="stack" style={{ ["--gap" as string]: "10px" }}>
      <p style={{ fontWeight: 600 }}>{r.text}</p>
      {r.quote && <blockquote style={{ margin: 0, paddingLeft: 12, borderLeft: "3px solid var(--green)", color: "var(--muted)" }}>“{r.quote}”</blockquote>}
      <dl className="kv"><dt>Source</dt><dd>{r.source_title}</dd><dt>Issuer</dt><dd>{r.issuer} · {r.date}</dd><dt>Section</dt><dd>{r.section}{r.page ? `, page ${r.page}` : ""}</dd></dl>
      <div className="row">
        <span className={`badge ${r.quote_checked ? "green" : "orange"}`}>{r.quote_checked ? "Quote checked against the source" : "Paraphrase — quote not yet checked"}</span>
        <a href={r.url} target="_blank" rel="noreferrer noopener" className="btn btn-ghost btn-sm">Open source</a>
      </div>
    </div>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button className="btn btn-ghost btn-sm" onClick={async () => { try { await navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 1600); } catch { /* clipboard blocked */ } }}>
      {ok ? <Check size={14} /> : <Copy size={14} />} {ok ? "Copied" : label}
    </button>
  );
}
