import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";
import { Link } from "react-router-dom";

const REAL = ["The agent logic: checks, ranking, plan, verifier and the human approval gate, covered by automated tests.", "Safety rules enforced in code: no eligibility verdicts, no guarantees, no medical advice, fixed emergency notice.", "31 rules paraphrased from six public official documents, each with source, section and page.", "Sign-in, roles, per-user case privacy and an audit log of decisions."];
const NOT = [
  ["Real data", "The hospital registry, packages and all cases are synthetic. Real patient and hospital data are not public, and the app labels this."],
  ["Government systems", "Submissions go to a labelled simulator. RELIEF is not connected to any government portal and does not query the beneficiary identification system."],
  ["Rule quotes", "Rules are paraphrases. Quotes are marked “not yet checked” until the source-check script has been run against the official documents. Sources also disagree on the pre-authorisation time limit (6 hours vs 12 hours), so both are shown."],
  ["Referral tiers", "These come from a 2025 study of Karnataka’s referral system and may have changed since."],
  ["Reading documents", "OCR is tested on clean images. Blurry or angled phone photos may come out unreadable, in which case the case is handed to a person."],
  ["Accuracy", "The built-in evaluation uses 30 synthetic cases written by the team, so it checks that code and rules agree. It is not a measure of accuracy on real cases."],
  ["Privacy review", "There has been no formal data-protection review. Do not enter real personal health information."],
];

export default function Safety() {
  return (
    <main className="sec" style={{ paddingTop: 56 }}>
      <div className="container" style={{ maxWidth: 860 }}>
        <span className="kicker">Safety and limits</span>
        <h1 style={{ fontSize: "clamp(2rem,4vw,3rem)", margin: "12px 0 16px" }}>What RELIEF does, and what it does not.</h1>
        <p className="lede" style={{ maxWidth: "none" }}>RELIEF is a prototype. This page says plainly what has been built and tested and what has not been verified.</p>
        <div className="card card-pad" style={{ marginTop: 32 }}>
          <h3 style={{ marginBottom: 14 }}>What is built and tested</h3>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>{REAL.map((t) => <li key={t} className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}><CheckCircle2 size={20} color="var(--green-600)" style={{ flex: "none", marginTop: 2 }} /> {t}</li>)}</ul>
        </div>
        <div className="card card-pad" style={{ marginTop: 20 }}>
          <h3 style={{ marginBottom: 14 }}>What is not verified or not real</h3>
          <div style={{ display: "grid", gap: 16 }}>{NOT.map(([h, t]) => <div key={h} className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}><CircleDashed size={20} color="var(--orange-600)" style={{ flex: "none", marginTop: 2 }} /><div><b style={{ color: "var(--ink)" }}>{h}.</b> <span className="muted">{t}</span></div></div>)}</div>
        </div>
        <div className="alert warn" style={{ marginTop: 20 }}><AlertTriangle size={20} /><div><b>Emergency.</b> RELIEF gives no medical advice. In an emergency call 112 or go to the nearest hospital.</div></div>
        <p style={{ marginTop: 28 }}><Link className="btn btn-ink" to="/">Back to home</Link></p>
      </div>
    </main>
  );
}
