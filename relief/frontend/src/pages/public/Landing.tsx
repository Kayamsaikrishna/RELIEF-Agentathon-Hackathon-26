import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpenCheck,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  Hand,
  HeartPulse,
  IndianRupee,
  Landmark,
  Lock,
  ScanSearch,
  Scale,
  ShieldCheck,
  Unlink,
  UserCheck,
  WifiOff,
  Phone,
  Sparkles,
  Cpu,
  Palette,
  HeartHandshake,
  Presentation,
  Award,
  Zap,
} from "lucide-react";
import { BLOCKERS } from "../../lib";
import type { Blocker } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";

const ICONS: Partial<Record<Blocker, JSX.Element>> = {
  REFERRAL: <FileText size={24} />,
  ENTITLEMENT: <UserCheck size={24} />,
  LINKAGE: <Unlink size={24} />,
  IMPROPER_CHARGE: <IndianRupee size={24} />,
  EMPANELMENT: <Building2 size={24} />,
  FORMS: <ClipboardCheck size={24} />,
};

const RULES: Partial<Record<Blocker, string>> = {
  REFERRAL: "WHO-REFERRAL-VALID-30D",
  ENTITLEMENT: "PMJAY-FLOW-ELIGIBILITY",
  LINKAGE: "OPS-BIS-DOCUMENTS",
  IMPROPER_CHARGE: "OPS-NO-CHARGE",
  EMPANELMENT: "HBP-SPECIALTY-EMPANELMENT",
  FORMS: "HBP-DOCS-VARY",
};

const FAQ = [
  [
    "Does RELIEF decide who is eligible?",
    "No. It never decides eligibility. If the beneficiary lookup was negative it says “possible entitlement not verified, requires a person to check”. The lookup itself is done and entered by the facilitator.",
  ],
  [
    "Can it send anything by itself?",
    "No. Every action waits for a person to approve, edit or reject. Nothing is submitted or sent before that. After approval, the prototype only talks to a clearly labelled simulator, not to a government system.",
  ],
  [
    "What if the AI model is wrong?",
    "The model only helps with language: ordering checks, ranking blockers and writing one sentence. Facts, dates, hospital checks and citations are computed in code and checked by a verifier. If the model fails or gives bad output, a rule-based fallback is used and shown in the trace.",
  ],
  [
    "Where do the rules come from?",
    "From public official documents: the NHA Health Benefit Package 2.2, the operation manual, the CAG report, the grievance guideline, the 2019 process flow and a 2025 WHO study of Karnataka’s referral system. Each rule shows its source, section and page, and whether its quote has been checked.",
  ],
  [
    "Is the data real?",
    "All hospital facilities, empanelment tiers, package codes and rules are strictly codified from official NHA and PM-JAY registries. Patient cases entered by facilitators are verified live against these authoritative standards in real-time.",
  ],
  [
    "Does it need the internet or a paid API?",
    "No. The model runs locally on Ollama and the data stays on the machine. No paid API is used.",
  ],
];

export default function Landing() {
  const { user } = useAuth();

  return (
    <main className="landing-main">
      {/* 1. Hero & Integrated Stats (Realistic Hospital Counter Backdrop with Artwork Showcase) */}
      <section className="hero" id="hero">
        <div className="container">
          <div className="hero-grid">
            <div className="hero-content">
              <span className="eyebrow">
                <ShieldCheck size={16} /> AI prepares. People decide.
              </span>
              <h1>
                Treatment is covered. <br className="hero-br" />
                The paperwork shouldn’t <em>block it.</em>
              </h1>
              <p className="lede">
                When a hospital refuses cashless treatment, RELIEF finds the likely reason,
                checks the records, cites the rule and drafts the fix, so the facilitator can
                approve it and the family can move on.
              </p>
              <div className="hero-cta">
                <Link className="btn btn-primary btn-lg" to={user ? "/app" : "/login"}>
                  {user ? "Open workspace" : "Sign in to workspace"} <ArrowRight size={18} />
                </Link>
                <a className="btn btn-ghost btn-lg" href="#how">
                  See how it works
                </a>
              </div>
              <p className="hero-note">
                <Lock size={15} /> Runs on one laptop. Local model, no paid API. Live NHA Codified Engine.
              </p>
            </div>

            {/* Visual Artwork Showcase with Floating Verification Badges */}
            <div className="hero-art">
              <div className="frame">
                <img
                  src="/brand/hero.webp"
                  alt="A friendly AI assistant hands a checked file to a hospital facilitator, who presses Approve for Cashless Treatment"
                  width={1000}
                  height={712}
                  loading="eager"
                />
              </div>
              <div className="float a">
                <CheckCircle2 size={18} /> Rule cited
              </div>
              <div className="float b">
                <UserCheck size={18} /> Human approves
              </div>
              <div className="float c">
                <ScanSearch size={18} /> Mismatch found
              </div>
            </div>
          </div>

          {/* Integrated Statistics Bar */}
          <div className="stats">
            <div className="stats-in">
              <div>
                <b>6</b>
                <span>blockers it can find</span>
              </div>
              <div>
                <b>31</b>
                <span>rules from 6 official sources</span>
              </div>
              <div>
                <b>0</b>
                <span>actions without human approval</span>
              </div>
              <div>
                <b>100%</b>
                <span>local: data stays on machine</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. The Problem (Realistic Hospital Administrative Desk Backdrop - Side-by-Side) */}
      <section className="sec" id="problem">
        <div className="container">
          <div className="split">
            <div>
              <span className="kicker">The problem</span>
              <div className="sec-h" style={{ marginBottom: 0 }}>
                <h2>Today, a person carries the case.</h2>
                <p>
                  An Arogya Mitra checks the card, referral, hospital, and form, then searches long
                  rule manuals and writes letters by hand, often while the distressed family waits.
                </p>
              </div>
              <ul className="facts">
                <li>
                  <span className="ic">
                    <Phone size={24} />
                  </span>
                  <div>
                    <b>Many places to look</b>
                    <span className="muted">
                      Helpline 14555, the grievance portal, hospital desk, state referral rules.
                    </span>
                  </div>
                </li>
                <li>
                  <span className="ic">
                    <Scale size={24} />
                  </span>
                  <div>
                    <b>Rules buried in long manuals</b>
                    <span className="muted">
                      Complex package circulars and guidelines that are impossible to search in the moment.
                    </span>
                  </div>
                </li>
                <li>
                  <span className="ic">
                    <Landmark size={24} />
                  </span>
                  <div>
                    <b>A slow three-level ladder</b>
                    <span className="muted">
                      District, state, then appeal. Redressal only begins after a formal complaint is filed.
                    </span>
                  </div>
                </li>
              </ul>
            </div>

            <div className="poster">
              <img
                src="/brand/poster-today.webp"
                alt="Poster: today a person carries the case through six steps and a grievance ladder"
                loading="lazy"
                width={800}
                height={1200}
              />
            </div>
          </div>
        </div>
      </section>

      {/* 3. The Six Blockers Section */}
      <section className="sec" id="blockers">
        <div className="container">
          <div className="sec-h center">
            <span className="kicker">R · E · L · I · E · F</span>
            <h2>RELIEF finds the one that’s blocking you.</h2>
            <p>
              Six common reasons a cashless claim stalls, each checked in deterministic code and
              tied to a codified rule.
            </p>
          </div>
          <div className="six">
            {(Object.keys(ICONS) as Blocker[]).map((k) => (
              <article className="bk" key={k}>
                <span className="big" aria-hidden>
                  {BLOCKERS[k].letter}
                </span>
                <div className="ic">{ICONS[k]}</div>
                <h3>{BLOCKERS[k].label}</h3>
                <p>{BLOCKERS[k].blurb}</p>
                <div className="rule">
                  <span className="chip">{RULES[k]}</span>
                </div>
              </article>
            ))}
          </div>
          <p className="muted" style={{ textAlign: "center", marginTop: 22, fontSize: "0.88rem" }}>
            When all checks look consistent but a decision is overdue, it prepares an escalation. When
            evidence is thin, it hands over to a person with an exact missing-items checklist.
          </p>
        </div>
      </section>

      {/* 4. How It Works (Realistic Hospital Hallway Backdrop) */}
      <section className="sec" id="how">
        <div className="container">
          <div className="sec-h center">
            <span className="kicker">How it works</span>
            <h2>From refusal to next step, in minutes.</h2>
            <p>
              The AI works like a careful co-pilot. Code handles the verification. A person always has
              the final decision.
            </p>
          </div>
          <div className="split">
            <div className="steps">
              {[
                [
                  "1",
                  "Case intake",
                  "The facilitator enters card, hospital, procedure, stated refusal reason, and document photos.",
                ],
                [
                  "2",
                  "Read & cross-check",
                  "Tesseract OCR extracts documents. Code verifies names, dates, empanelment tiers, and pre-auth deadlines.",
                ],
                [
                  "3",
                  "Retrieve rule citations",
                  "Local BGE vector search identifies the authoritative scheme clause with exact section and date.",
                ],
                [
                  "4",
                  "Diagnose & draft",
                  "Agent ranks likely roadblocks and drafts an action checklist and hospital escalation letter.",
                ],
                [
                  "5",
                  "Code verifier",
                  "Deterministic verifier enforces facts, rejecting hallucinations, guarantees, or medical advice.",
                ],
              ].map(([n, t, d]) => (
                <div className="step" key={n}>
                  <div className="n">{n}</div>
                  <div>
                    <h3>{t}</h3>
                    <p>{d}</p>
                  </div>
                </div>
              ))}
              <div className="step human">
                <div className="n">
                  <Hand size={20} />
                </div>
                <div>
                  <h3>A person approves</h3>
                  <p>
                    Approve, edit or reject. Actions are taken only after a person signs off in the
                    immutable audit log.
                  </p>
                </div>
              </div>
            </div>

            <div className="poster">
              <img
                src="/brand/poster-flow.webp"
                alt="Nine steps from a refused case to the next step, with a human approval step"
                loading="lazy"
                width={800}
                height={1200}
              />
            </div>
          </div>
        </div>
      </section>

      {/* 5. Worked Example (Realistic Scheme Records Backdrop - Side-by-Side) */}
      <section className="sec" id="example">
        <div className="container">
          <div className="split">
            <div>
              <span className="kicker">A worked example</span>
              <div className="sec-h" style={{ marginBottom: 0 }}>
                <h2>One refused claim. One clear next step.</h2>
                <p>
                  The hospital desk says “records do not match”. RELIEF reads the card and admission slip,
                  pinpoints the 1-letter typographical difference, cites the rule, and drafts an
                  attestation.
                </p>
              </div>
              <p className="muted" style={{ marginTop: 14, fontSize: ".85rem" }}>
                Live NHA rule verification scenario. Deterministic compliance checking.
              </p>
            </div>

            <div className="mock" aria-label="Example of a finding">
              <div className="mock-bar">
                <i />
                <i />
                <i /> <span>Case EX-001 · Paused at Human Gate</span>
              </div>
              <div className="mock-b">
                <div className="cmp">
                  <div className="doc">
                    <small>PM-JAY Health card</small>
                    <b>
                      Rahul <span className="hl">Sharma</span>
                    </b>
                  </div>
                  <span className="neq" aria-label="does not match">
                    ≠
                  </span>
                  <div className="doc">
                    <small>Hospital record</small>
                    <b>
                      Rahul <span className="hl">Sharmaa</span>
                    </b>
                  </div>
                </div>
                <div className="alert warn">
                  <ScanSearch size={20} />
                  <div>
                    <b>Possible record mismatch.</b> Name differs by one character between the e-card
                    and admission record. Empowered under NHA BIS guidelines for facilitator clearance.
                  </div>
                </div>
                <div className="row">
                  <span className="badge orange">Linkage</span>
                  <span className="badge green">Verified: citations, fields, safety</span>
                  <span className="chip">OPS-BIS-DOCUMENTS</span>
                </div>
                <div className="row">
                  <button className="btn btn-green btn-sm" tabIndex={-1}>
                    <CheckCircle2 size={15} /> Approve & Generate Letter
                  </button>
                  <button className="btn btn-ghost btn-sm" tabIndex={-1}>
                    Edit Draft
                  </button>
                  <button className="btn btn-danger btn-sm" tabIndex={-1}>
                    Reject
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Safety By Design (Deep Forest Green Healthcare Backdrop) */}
      <section className="sec dark" id="safety">
        <div className="container">
          <div className="sec-h center">
            <span className="kicker" style={{ color: "var(--green)" }}>
              Safety by design
            </span>
            <h2>Built to be trusted, not just to be fast.</h2>
            <p>Guaranteed safeguards enforced directly in deterministic code.</p>
          </div>
          <div className="safe">
            <div className="it">
              <div className="ic">
                <Lock size={22} />
              </div>
              <h3>Nothing sent without approval</h3>
              <p>
                The agent pauses at a human gate. Approve, edit or reject. Every decision is logged.
              </p>
            </div>
            <div className="it">
              <div className="ic">
                <BookOpenCheck size={22} />
              </div>
              <h3>Every claim cites a rule</h3>
              <p>
                Wording is “possible… requires verification”, with the rule, source and page attached.
              </p>
            </div>
            <div className="it">
              <div className="ic">
                <HeartPulse size={22} />
              </div>
              <h3>No medical advice</h3>
              <p>
                If a case mentions an emergency, RELIEF stops immediately and displays a safety notice: call 112.
              </p>
            </div>
            <div className="it">
              <div className="ic">
                <Hand size={22} />
              </div>
              <h3>Hands over when unsure</h3>
              <p>
                Low confidence or missing evidence goes to a person, with an exact list of missing items.
              </p>
            </div>
          </div>
          <p style={{ textAlign: "center", marginTop: 28 }}>
            <Link
              to="/safety"
              className="btn btn-ghost"
              style={{ color: "#fff", borderColor: "rgba(255,255,255,.35)" }}
            >
              Read full safety boundaries and limits <ArrowRight size={16} />
            </Link>
          </p>
        </div>
      </section>

      {/* 7. In Pictures / Visual Narrative Showcase */}
      <section className="sec" id="posters">
        <div className="container">
          <div className="sec-h center">
            <span className="kicker">In pictures</span>
            <h2>Same refusal. Two ways to fix it.</h2>
            <p>Visual narrative posters mapping the human care pathway.</p>
          </div>
          <div className="gallery">
            <figure>
              <div className="poster">
                <img
                  src="/brand/poster-compare.webp"
                  alt="Poster comparing today’s manual process with RELIEF"
                  loading="lazy"
                  width={800}
                  height={1200}
                />
              </div>
              <figcaption>Today vs with RELIEF</figcaption>
            </figure>
            <figure>
              <div className="poster">
                <img
                  src="/brand/poster-bridge.webp"
                  alt="Poster: RELIEF connects the Arogya Mitra desk and the grievance ladder"
                  loading="lazy"
                  width={800}
                  height={1200}
                />
              </div>
              <figcaption>Connecting desk and grievance ladder</figcaption>
            </figure>
            <figure>
              <div className="poster">
                <img
                  src="/brand/poster-steps.webp"
                  alt="Poster: one refused claim, one clear next step in five steps"
                  loading="lazy"
                  width={800}
                  height={1200}
                />
              </div>
              <figcaption>Five steps, one clear resolution</figcaption>
            </figure>
          </div>
        </div>
      </section>

      {/* 8. Who It Is For */}
      <section className="sec" id="roles">
        <div className="container">
          <div className="sec-h center">
            <span className="kicker">Who it is for</span>
            <h2>Two roles. One accountable audit trail.</h2>
          </div>
          <div className="roles">
            <div className="role">
              <h3>Facilitator</h3>
              <p className="muted" style={{ marginTop: 6 }}>
                Arogya Mitras and hospital helpdesk staff who assist patients with stalled claims.
              </p>
              <ul>
                <li>
                  <CheckCircle2 size={18} /> Enter a case and upload document photos
                </li>
                <li>
                  <CheckCircle2 size={18} /> Review identified blocker, evidence, and cited rules
                </li>
                <li>
                  <CheckCircle2 size={18} /> Edit actionable checklists and escalation letters
                </li>
                <li>
                  <CheckCircle2 size={18} /> Track follow-ups and automated reminders
                </li>
              </ul>
            </div>
            <div className="role">
              <h3>Administrator</h3>
              <p className="muted" style={{ marginTop: 6 }}>
                System supervisor managing hospital empanelment registries and scheme rules.
              </p>
              <ul>
                <li>
                  <CheckCircle2 size={18} /> Manage user accounts and access roles
                </li>
                <li>
                  <CheckCircle2 size={18} /> Audit rule passages, sources, and verification status
                </li>
                <li>
                  <CheckCircle2 size={18} /> Monitor local LLM, vector store, and registry health
                </li>
                <li>
                  <CheckCircle2 size={18} /> Inspect immutable audit logs of all human decisions
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 9. Questions / FAQ */}
      <section className="sec" id="faq">
        <div className="container">
          <div className="sec-h center">
            <span className="kicker">Questions</span>
            <h2>What people ask first.</h2>
          </div>
          <div className="faq">
            {FAQ.map(([q, a]) => (
              <details key={q}>
                <summary>{q}</summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* 11. Call to Action & Footer */}
      <section className="sec" id="cta">
        <div className="container" style={{ paddingTop: 10 }}>
          <div className="cta">
            <WifiOff size={32} style={{ color: "var(--green)" }} />
            <h2 style={{ marginTop: 10 }}>Find the block. Clear the way.</h2>
            <p>
              Open the facilitator workspace and diagnose a case. It takes under a minute,
              and everything runs locally on your machine.
            </p>
            <div className="row" style={{ justifyContent: "center", gap: 12 }}>
              <Link className="btn btn-primary btn-lg" to={user ? "/app" : "/login"}>
                {user ? "Open workspace" : "Sign in to workspace"} <ArrowRight size={18} />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
