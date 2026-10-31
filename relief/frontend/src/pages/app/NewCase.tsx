import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check, FileImage, FileText, Plus, Send, Sparkles, Trash2, Upload, AlertCircle, ShieldCheck } from "lucide-react";
import { api } from "../../api/client";
import type { Hospital, Pkg } from "../../api/types";
import { Alert, Spinner, useToast } from "../../components/ui";
import { DOC_KINDS } from "../../lib";

interface DocDraft {
  id: string;
  kind: string;
  mode: "image" | "text";
  file?: File;
  text: string;
}

interface SchemeOption {
  id: string;
  name: string;
  shortName: string;
  state: string;
}

interface IdTypeOption {
  id: string;
  label: string;
  shortLabel: string;
  placeholder: string;
  hint: string;
  sampleVal: string;
}

export const SCHEMES: SchemeOption[] = [
  { id: "karnataka", name: "Karnataka · Ayushman Bharat - Arogya Karnataka (AB-ArK / SAST)", shortName: "AB-ArK (Karnataka)", state: "Karnataka" },
  { id: "maharashtra", name: "Maharashtra · Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY)", shortName: "MJPJAY (Maharashtra)", state: "Maharashtra" },
  { id: "andhra_pradesh", name: "Andhra Pradesh · Dr. YSR Aarogyasri Health Scheme", shortName: "YSR Aarogyasri (AP)", state: "Andhra Pradesh" },
  { id: "telangana", name: "Telangana · Aarogyasri Health Care Scheme", shortName: "Aarogyasri (Telangana)", state: "Telangana" },
  { id: "tamil_nadu", name: "Tamil Nadu · Chief Minister's Comprehensive Health Insurance Scheme (CMCHIS)", shortName: "CMCHIS (Tamil Nadu)", state: "Tamil Nadu" },
  { id: "rajasthan", name: "Rajasthan · Chiranjeevi Swasthya Bima / Jan Aadhaar Scheme", shortName: "Chiranjeevi (Rajasthan)", state: "Rajasthan" },
  { id: "west_bengal", name: "West Bengal · Swasthya Sathi Scheme", shortName: "Swasthya Sathi (WB)", state: "West Bengal" },
  { id: "gujarat", name: "Gujarat · Mukhyamantri Amrutam (MA / MA Vatsalya) - PMJAY", shortName: "MA-PMJAY (Gujarat)", state: "Gujarat" },
  { id: "central", name: "National / Central Pool · Ayushman Bharat PM-JAY (AB-PMJAY)", shortName: "AB-PMJAY (National)", state: "National Pool" },
];

export const ID_TYPES: IdTypeOption[] = [
  {
    id: "state_card",
    label: "State Scheme Health Card (e.g. ArK ID, Aarogyasri Card, MJPJAY Card)",
    shortLabel: "State Health Card ID",
    placeholder: "e.g. KA700100 (ArK ID)",
    hint: "Official state health card number issued under the state health protection scheme.",
    sampleVal: "KA700100",
  },
  {
    id: "ration_card",
    label: "Ration Card (BPL / Antyodaya AAY / Priority Household PHH)",
    shortLabel: "BPL Ration Card No",
    placeholder: "e.g. RC-KA9821491024",
    hint: "Recognized proof of eligibility under state Food & Civil Supplies database.",
    sampleVal: "RC-KA982149",
  },
  {
    id: "aadhaar",
    label: "Aadhaar Card (UIDAI 12-digit e-KYC Verification)",
    shortLabel: "Aadhaar UIDAI Number",
    placeholder: "e.g. 5812 9012 3456",
    hint: "Instant biometric/OTP authentication on the Beneficiary Identification System (BIS).",
    sampleVal: "5812 9012 3456",
  },
  {
    id: "abha",
    label: "ABHA Number (Ayushman Bharat Health Account - 14 digits)",
    shortLabel: "ABHA Health ID",
    placeholder: "e.g. 91-8271-9281-2291",
    hint: "National digital health account number recognized across all empanelled hospital registries.",
    sampleVal: "91-8271-9281-2291",
  },
  {
    id: "pmjay",
    label: "National PM-JAY Card ID (Gold / Plastic Card)",
    shortLabel: "PM-JAY Beneficiary ID",
    placeholder: "e.g. P100298172",
    hint: "National Ayushman Bharat beneficiary identification number.",
    sampleVal: "P100298172",
  },
];

interface Form {
  case_id: string;
  scheme_state: string;
  id_type: string;
  name: string;
  card_id: string;
  family_id: string;
  dob: string;
  hospital_id: string;
  procedure_code: string;
  reason: string;
  bis: "unknown" | "verified" | "not_found";
  ref_present: "unknown" | "yes" | "no";
  ref_date: string;
  admission: string;
  preauth_at: string;
  pay: boolean;
  amount: string;
  purpose: string;
  wallet: string;
  disclosed: string;
  synthetic: boolean;
  docs: DocDraft[];
}

const newId = () => `C-${new Date().toISOString().slice(2, 10).replace(/-/g, "")}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;

const blank = (): Form => ({
  case_id: newId(),
  scheme_state: "central",
  id_type: "pmjay_id",
  name: "",
  card_id: "",
  family_id: "",
  dob: "",
  hospital_id: "",
  procedure_code: "",
  reason: "",
  bis: "verified",
  ref_present: "no",
  ref_date: "",
  admission: new Date().toISOString().slice(0, 10),
  preauth_at: "",
  pay: false,
  amount: "",
  purpose: "",
  wallet: "no",
  disclosed: "no",
  synthetic: false,
  docs: [],
});

const ident = (n: string, id: string, dob: string, idLabel: string, scheme: string) =>
  `Name: ${n}\nCard ID: ${id}\nID Type: ${idLabel}\nScheme: ${scheme}\nDOB: ${dob}`;

const sampleDocs = (n: string, id: string, dob: string, hosp: string, proc: string, idLabel: string, scheme: string): DocDraft[] => [
  { id: "d1", kind: "card", mode: "text", text: ident(n, id, dob, idLabel, scheme) },
  { id: "d2", kind: "id_proof", mode: "text", text: ident(n, id, dob, idLabel, scheme) },
  { id: "d3", kind: "preauth_form", mode: "text", text: `Hospital: ${hosp}\nProcedure: ${proc}\nScheme: ${scheme}\nPre-auth Form Submitted` },
  { id: "d4", kind: "clinical_notes", mode: "text", text: `Clinical assessment: Severe osteoarthritis right knee. Indicated for Total Knee Arthroplasty.` },
  { id: "d5", kind: "diagnostic_report", mode: "text", text: `X-Ray Right Knee: Grade 4 Tricompartmental Osteoarthritis with joint space obliteration.` },
];

const STEPS = ["1. Scheme & Patient", "2. Hospital & Reason", "3. Referral & Financials", "4. Documents & Submission"];

export default function NewCase() {
  const nav = useNavigate();
  const toast = useToast();
  const [f, setF] = useState<Form>(blank());
  const [step, setStep] = useState(0);
  const [hosp, setHosp] = useState<Hospital[]>([]);
  const [pk, setPk] = useState<Pkg[]>([]);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [fail, setFail] = useState("");

  useEffect(() => {
    api<Hospital[]>("/registry/hospitals").then(setHosp).catch(() => {});
    api<Pkg[]>("/registry/packages").then(setPk).catch(() => {});
  }, []);

  const set = <K extends keyof Form>(k: K, v: Form[K]) => {
    setF((x) => ({ ...x, [k]: v }));
    if (errs[k]) {
      setErrs((e) => {
        const copy = { ...e };
        delete copy[k];
        return copy;
      });
    }
  };

  const pkg = useMemo(() => pk.find((p) => p.code === f.procedure_code), [pk, f.procedure_code]);
  const hospital = useMemo(() => hosp.find((h) => h.hospital_id === f.hospital_id), [hosp, f.hospital_id]);
  const curScheme = useMemo(() => SCHEMES.find((s) => s.id === f.scheme_state) ?? SCHEMES[0], [f.scheme_state]);
  const curIdType = useMemo(() => ID_TYPES.find((t) => t.id === f.id_type) ?? ID_TYPES[0], [f.id_type]);

  const { stateHospitals, otherHospitals } = useMemo(() => {
    const targetState = curScheme.state;
    if (!targetState || targetState === "National Pool") {
      return { stateHospitals: hosp, otherHospitals: [] };
    }
    const stateMatches = hosp.filter((h) => h.state.toLowerCase() === targetState.toLowerCase());
    const otherMatches = hosp.filter((h) => h.state.toLowerCase() !== targetState.toLowerCase());
    return { stateHospitals: stateMatches, otherHospitals: otherMatches };
  }, [hosp, curScheme.state]);

  function validate(s: number): boolean {
    const e: Record<string, string> = {};
    if (s === 0) {
      if (!f.scheme_state) e.scheme_state = "Please select the applicable health scheme.";
      if (!f.id_type) e.id_type = "Please select the beneficiary identifier type.";
      if (!f.name.trim()) e.name = "Patient full name is mandatory.";
      if (!f.card_id.trim()) e.card_id = `${curIdType.shortLabel} is mandatory.`;
      if (!f.case_id.trim() || !/^[A-Za-z0-9_-]{1,64}$/.test(f.case_id)) e.case_id = "Valid Case ID required (letters, digits, - and _ only).";
    }
    if (s === 1) {
      if (!f.hospital_id) e.hospital_id = "Please select the admitting hospital.";
      if (!f.procedure_code) e.procedure_code = "Please select the clinical procedure / package.";
      if (!f.reason.trim()) e.reason = "Please enter the refusal reason stated by the hospital desk.";
    }
    if (s === 2) {
      if (!f.admission) e.admission = "Admission date is mandatory.";
      if (f.pay) {
        if (!f.amount || Number(f.amount) <= 0) e.amount = "Enter the amount demanded by the hospital.";
        if (!f.purpose.trim()) e.purpose = "Specify what payment was requested for.";
      }
    }
    if (s === 3) {
      if (f.docs.length === 0) {
        e.docs = "Please attach at least one patient document (Health Card photo, Aadhaar ID, or hospital refusal slip).";
      }
    }
    setErrs(e);
    return Object.keys(e).length === 0;
  }

  const next = () => {
    if (validate(step)) setStep(step + 1);
  };

  const addDoc = () => {
    set("docs", [...f.docs, { id: `d${Date.now()}`, kind: "card", mode: "image", text: "" }]);
    if (errs.docs) {
      setErrs((e) => {
        const copy = { ...e };
        delete copy.docs;
        return copy;
      });
    }
  };

  const upd = (id: string, patch: Partial<DocDraft>) => set("docs", f.docs.map((d) => (d.id === id ? { ...d, ...patch } : d)));

  async function submit() {
    if (![0, 1, 2, 3].every((s) => validate(s) || (setStep(s), false))) return;
    setBusy(true);
    setFail("");
    try {
      const documents = [];
      for (const [i, d] of f.docs.entries()) {
        if (d.mode === "image") {
          if (!d.file) throw new Error(`Document ${i + 1}: please choose an image file or switch to typed text.`);
          const fd = new FormData();
          fd.append("file", d.file);
          const up = await api<{ path: string }>("/uploads", { form: fd });
          documents.push({ doc_id: `D${i + 1}`, kind: d.kind, path: up.path });
        } else {
          if (!d.text.trim()) throw new Error(`Document ${i + 1}: text cannot be empty.`);
          documents.push({ doc_id: `D${i + 1}`, kind: d.kind, text: d.text });
        }
      }
      const body: Record<string, unknown> = {
        case_id: f.case_id,
        card: {
          name: f.name.trim(),
          card_id: f.card_id.trim(),
          family_id: f.family_id.trim() || null,
          dob: f.dob || null,
          scheme_name: curScheme.shortName,
          id_type: f.id_type,
          state: curScheme.state,
        },
        documents,
        hospital_id: f.hospital_id,
        procedure_code: f.procedure_code,
        refusal_reason: f.reason.trim(),
        bis_status: f.bis,
        referral: { present: f.ref_present, issued_on: f.ref_date || null },
        admission_date: f.admission || null,
        preauth_submitted_at: f.preauth_at ? new Date(f.preauth_at).toISOString() : null,
        synthetic: false,
      };
      if (f.pay) {
        body.payment_request = {
          amount_inr: Number(f.amount),
          purpose: f.purpose.trim(),
          wallet_exhausted: f.wallet,
          disclosed_in_advance: f.disclosed,
        };
      }
      await api("/cases", { body });
      nav(`/app/cases/${f.case_id}`);
    } catch (e) {
      setFail((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const E = ({ k }: { k: string }) =>
    errs[k] ? (
      <span className="hint" style={{ color: "#d9342b", fontWeight: 700, marginTop: 4, display: "flex", alignItems: "center", gap: 4 }}>
        <AlertCircle size={13} /> {errs[k]}
      </span>
    ) : null;

  return (
    <div className="stack" style={{ ["--gap" as string]: "22px", maxWidth: 960 }}>
      <div className="page-h">
        <div>
          <h1>Register Hospital Claim Denial</h1>
          <p>Enter patient and refusal details with mandatory verification fields marked in red.</p>
        </div>
      </div>

      <div className="wiz-steps" role="tablist">
        {STEPS.map((s, i) => (
          <button
            key={s}
            role="tab"
            aria-selected={i === step}
            className={i === step ? "cur" : i < step ? "done" : ""}
            onClick={() => (i < step || validate(step)) && setStep(i)}
          >
            <span className="n">{i < step ? <Check size={14} /> : i + 1}</span>
            {s}
          </button>
        ))}
      </div>

      {/* Step 1: Scheme, Identifier & Patient Details */}
      {step === 0 && (
        <div className="card card-pad stack" style={{ ["--gap" as string]: "20px" }}>
          <div style={{ background: "rgba(10, 66, 60, 0.05)", border: "1px solid rgba(10, 66, 60, 0.14)", borderRadius: 10, padding: "12px 16px" }}>
            <div className="row" style={{ gap: 8, alignItems: "center" }}>
              <ShieldCheck size={18} color="var(--green)" />
              <b style={{ color: "var(--ink)", fontSize: "0.95rem" }}>Multi-State & Multi-Card Support</b>
            </div>
            <p className="muted" style={{ margin: "4px 0 0", fontSize: "0.85rem", lineHeight: 1.5 }}>
              Patients across states carry different cards (e.g. <b>ArK</b> in Karnataka, <b>Aarogyasri</b> in AP/TS, <b>MJPJAY</b> in Maharashtra, <b>CMCHIS</b> in TN)
              or authenticate via <b>Ration Card (BPL/AAY)</b>, <b>Aadhaar e-KYC</b>, or <b>ABHA ID</b>. Select the patient's card or ID type below.
            </p>
          </div>

          <div className="grid g2">
            <div className="field">
              <label htmlFor="scheme_state">
                State / Government Health Scheme <span className="req">*</span>
              </label>
              <select
                id="scheme_state"
                className={`input ${errs.scheme_state ? "has-error" : ""}`}
                value={f.scheme_state}
                onChange={(e) => set("scheme_state", e.target.value)}
                aria-invalid={!!errs.scheme_state}
              >
                {SCHEMES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <E k="scheme_state" />
              <span className="hint">Jurisdiction rules and benefit package for this patient.</span>
            </div>

            <div className="field">
              <label htmlFor="id_type">
                Beneficiary Identifier Type <span className="req">*</span>
              </label>
              <select
                id="id_type"
                className={`input ${errs.id_type ? "has-error" : ""}`}
                value={f.id_type}
                onChange={(e) => set("id_type", e.target.value)}
                aria-invalid={!!errs.id_type}
              >
                {ID_TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
              <E k="id_type" />
              <span className="hint">{curIdType.hint}</span>
            </div>
          </div>

          <div className="grid g2">
            <div className="field">
              <label htmlFor="name">
                Patient Full Name <span className="req">*</span>
              </label>
              <input
                id="name"
                className={`input ${errs.name ? "has-error" : ""}`}
                placeholder="e.g. Asha Rao"
                value={f.name}
                onChange={(e) => set("name", e.target.value)}
                aria-invalid={!!errs.name}
              />
              <E k="name" />
            </div>

            <div className="field">
              <label htmlFor="cid">
                {curIdType.shortLabel} <span className="req">*</span>
              </label>
              <input
                id="cid"
                className={`input ${errs.card_id ? "has-error" : ""}`}
                placeholder={curIdType.placeholder}
                value={f.card_id}
                onChange={(e) => set("card_id", e.target.value)}
                aria-invalid={!!errs.card_id}
              />
              <E k="card_id" />
              <span className="hint">Must match document presented (Sample: {curIdType.sampleVal}).</span>
            </div>
          </div>

          <div className="grid g3">
            <div className="field">
              <label htmlFor="fid">
                Secondary ID / Family Ration Card <span className="muted">(Optional)</span>
              </label>
              <input
                id="fid"
                className="input"
                placeholder="e.g. RC-KA98214"
                value={f.family_id}
                onChange={(e) => set("family_id", e.target.value)}
              />
              <span className="hint">BPL / Antyodaya / Ration Card.</span>
            </div>

            <div className="field">
              <label htmlFor="dob">
                Date of Birth <span className="muted">(Optional)</span>
              </label>
              <input
                id="dob"
                className="input"
                type="date"
                max={new Date().toISOString().slice(0, 10)}
                value={f.dob}
                onChange={(e) => set("dob", e.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="caseid">
                Case Tracking ID <span className="req">*</span>
              </label>
              <input
                id="caseid"
                className={`input mono ${errs.case_id ? "has-error" : ""}`}
                value={f.case_id}
                onChange={(e) => set("case_id", e.target.value)}
                aria-invalid={!!errs.case_id}
              />
              <E k="case_id" />
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Hospital and Reason */}
      {step === 1 && (
        <div className="card card-pad stack">
          <div className="grid g2">
            <div className="field">
              <label htmlFor="h">
                Admitting Hospital <span className="req">*</span>
              </label>
              <select
                id="h"
                className={`input ${errs.hospital_id ? "has-error" : ""}`}
                value={f.hospital_id}
                onChange={(e) => set("hospital_id", e.target.value)}
                aria-invalid={!!errs.hospital_id}
              >
                <option value="">Select empanelled hospital…</option>
                {stateHospitals.length > 0 && (
                  <optgroup label={`Empanelled Hospitals in ${curScheme.state} (${stateHospitals.length} Facilities)`}>
                    {stateHospitals.map((h) => (
                      <option key={h.hospital_id} value={h.hospital_id}>
                        {h.name} ({h.type === "public" ? "Govt" : "Empanelled Private"} · {h.district})
                      </option>
                    ))}
                  </optgroup>
                )}
                {otherHospitals.length > 0 && (
                  <optgroup label="Other States & National Institutes (Cross-State Treatment / Portability)">
                    {otherHospitals.map((h) => (
                      <option key={h.hospital_id} value={h.hospital_id}>
                        [{h.state}] {h.name} ({h.type === "public" ? "Govt" : "Empanelled Private"} · {h.district})
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
              <E k="hospital_id" />
              {hospital && (
                <span className="hint">
                  {hospital.type === "public" ? "Government Facility" : "Empanelled Private Facility"} · {hospital.state} ({hospital.district}) · Specialities:{" "}
                  {hospital.specialties.join(", ")}
                </span>
              )}
            </div>

            <div className="field">
              <label htmlFor="p">
                Clinical Procedure / Package <span className="req">*</span>
              </label>
              <select
                id="p"
                className={`input ${errs.procedure_code ? "has-error" : ""}`}
                value={f.procedure_code}
                onChange={(e) => set("procedure_code", e.target.value)}
                aria-invalid={!!errs.procedure_code}
              >
                <option value="">Select clinical package…</option>
                {pk.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.name} · Tier {p.tier} ({p.code})
                  </option>
                ))}
              </select>
              <E k="procedure_code" />
              {pkg && (
                <span className="hint">
                  {pkg.specialty} · Tier {pkg.tier}
                  {pkg.reserved_for_public ? " · Reserved for government hospitals only" : ""}
                </span>
              )}
            </div>
          </div>

          <div className="field">
            <label htmlFor="r">
              Reason Hospital Gave (Desk Refusal Remark) <span className="req">*</span>
            </label>
            <textarea
              id="r"
              className={`input ${errs.reason ? "has-error" : ""}`}
              maxLength={2000}
              value={f.reason}
              onChange={(e) => set("reason", e.target.value)}
              aria-invalid={!!errs.reason}
              placeholder="e.g. “Secondary referral letter is missing for Tier-3A admission. Cashless denied.”"
            />
            <E k="reason" />
            <span className="hint">
              Enter the exact words given by the hospital admission desk. RELIEF checks this against codified guidelines.
            </span>
          </div>

          <div className="field">
            <span className="label">Beneficiary Identification System (BIS) Verification Status</span>
            <div className="seg" role="group">
              {(
                [
                  ["verified", "Verified (Active in BIS)"],
                  ["not_found", "Not Found in Portal"],
                  ["unknown", "Not Checked Yet"],
                ] as const
              ).map(([v, l]) => (
                <button key={v} type="button" aria-pressed={f.bis === v} onClick={() => set("bis", v)}>
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Referral, Payment & Timing */}
      {step === 2 && (
        <div className="card card-pad stack">
          <div className="grid g2">
            <div className="field">
              <span className="label">
                Official Referral Letter Present? <span className="req">*</span>
              </span>
              <div className="seg" role="group">
                {(
                  [
                    ["yes", "Yes, Letter Present"],
                    ["no", "No Referral Letter"],
                    ["unknown", "Unknown / Under Verification"],
                  ] as const
                ).map(([v, l]) => (
                  <button key={v} type="button" aria-pressed={f.ref_present === v} onClick={() => set("ref_present", v)}>
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label htmlFor="rd">Referral Letter Issue Date</label>
              <input
                id="rd"
                className="input"
                type="date"
                disabled={f.ref_present !== "yes"}
                value={f.ref_date}
                onChange={(e) => set("ref_date", e.target.value)}
              />
              <span className="hint">Online referral letters under WHO/NHA framework remain valid for 30 days.</span>
            </div>

            <div className="field">
              <label htmlFor="ad">
                Admission Date <span className="req">*</span>
              </label>
              <input
                id="ad"
                className={`input ${errs.admission ? "has-error" : ""}`}
                type="date"
                value={f.admission}
                onChange={(e) => set("admission", e.target.value)}
              />
              <E k="admission" />
            </div>

            <div className="field">
              <label htmlFor="pa">Pre-authorisation Submission Timestamp</label>
              <input
                id="pa"
                className="input"
                type="datetime-local"
                value={f.preauth_at}
                onChange={(e) => set("preauth_at", e.target.value)}
              />
              <span className="hint">Required to verify adherence to NHA 6-hour / 12-hour turnaround clock.</span>
            </div>
          </div>

          <label className="check" style={{ marginTop: 8 }}>
            <input type="checkbox" checked={f.pay} onChange={(e) => set("pay", e.target.checked)} />
            <span>
              <b>Hospital Demanded Out-of-Pocket Payment or Cash Deposit</b>
            </span>
          </label>

          {f.pay && (
            <div className="grid g2" style={{ background: "var(--orange-50)", padding: 18, borderRadius: 16 }}>
              <div className="field">
                <label htmlFor="am">
                  Amount Demanded (₹) <span className="req">*</span>
                </label>
                <input
                  id="am"
                  className={`input ${errs.amount ? "has-error" : ""}`}
                  type="number"
                  min={0}
                  placeholder="e.g. 85000"
                  value={f.amount}
                  onChange={(e) => set("amount", e.target.value)}
                  aria-invalid={!!errs.amount}
                />
                <E k="amount" />
              </div>
              <div className="field">
                <label htmlFor="pu">
                  Payment Purpose Stated <span className="req">*</span>
                </label>
                <input
                  id="pu"
                  className={`input ${errs.purpose ? "has-error" : ""}`}
                  value={f.purpose}
                  onChange={(e) => set("purpose", e.target.value)}
                  aria-invalid={!!errs.purpose}
                  placeholder="e.g. Cash admission deposit, implant cost, bed charge"
                />
                <E k="purpose" />
              </div>
              <div className="field">
                <span className="label">Family Wallet Balance Exhausted?</span>
                <div className="seg">
                  {["no", "yes", "unknown"].map((v) => (
                    <button key={v} type="button" aria-pressed={f.wallet === v} onClick={() => set("wallet", v)}>
                      {v.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
              <div className="field">
                <span className="label">Written Advance Disclosure Provided?</span>
                <div className="seg">
                  {["no", "yes", "unknown"].map((v) => (
                    <button key={v} type="button" aria-pressed={f.disclosed === v} onClick={() => set("disclosed", v)}>
                      {v.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Step 4: Documents and Review */}
      {step === 3 && (
        <>
          <div className="card card-pad stack">
            <div className="spread">
              <div>
                <h3>
                  Attach Case Documents <span className="req">*</span>
                </h3>
                <p className="hint">
                  Upload card photos, refusal slips, or diagnostic reports for OCR extraction and rule cross-checking.
                  {pkg && (
                    <>
                      {" "}
                      This clinical package mandates:{" "}
                      <b>{pkg.required_docs.map((k) => DOC_KINDS[k] ?? k).join(", ")}</b>.
                    </>
                  )}
                </p>
              </div>
              <button type="button" className="btn btn-primary btn-sm" onClick={addDoc}>
                <Plus size={15} /> Attach Document
              </button>
            </div>

            {errs.docs && (
              <Alert kind="err" title="Missing Documents">
                {errs.docs}
              </Alert>
            )}

            {f.docs.length === 0 && (
              <div
                className="drop"
                onClick={addDoc}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && addDoc()}
                style={{ borderColor: errs.docs ? "var(--red)" : undefined }}
              >
                <Upload size={32} color={errs.docs ? "var(--red)" : "var(--ink-3)"} />
                <p style={{ marginTop: 8, fontWeight: 700, color: "var(--ink)" }}>
                  No documents attached yet. Click here to attach patient files.
                </p>
                <span className="hint">Upload camera photo, PDF scan, or hospital refusal letter.</span>
              </div>
            )}

            {f.docs.map((d, i) => (
              <div className="doc-row" key={d.id}>
                <div className="stack" style={{ ["--gap" as string]: "8px" }}>
                  <select
                    className="input"
                    aria-label={`Document ${i + 1} type`}
                    value={d.kind}
                    onChange={(e) => upd(d.id, { kind: e.target.value })}
                  >
                    {Object.entries(DOC_KINDS).map(([k, l]) => (
                      <option key={k} value={k}>
                        {l}
                      </option>
                    ))}
                  </select>
                  <div className="seg">
                    <button
                      type="button"
                      aria-pressed={d.mode === "image"}
                      onClick={() => upd(d.id, { mode: "image" })}
                    >
                      <FileImage size={13} /> Photo / Scan
                    </button>
                    <button
                      type="button"
                      aria-pressed={d.mode === "text"}
                      onClick={() => upd(d.id, { mode: "text" })}
                    >
                      <FileText size={13} /> Text Extract
                    </button>
                  </div>
                </div>

                {d.mode === "image" ? (
                  <div className="field">
                    <input
                      className="input"
                      type="file"
                      accept="image/png,image/jpeg,image/tiff,image/bmp"
                      aria-label={`Document ${i + 1} file`}
                      onChange={(e) => upd(d.id, { file: e.target.files?.[0] })}
                    />
                    <span className="hint">Upload JPEG, PNG or BMP photo. Tesseract OCR reads document contents automatically.</span>
                  </div>
                ) : (
                  <textarea
                    className="input"
                    aria-label={`Document ${i + 1} text`}
                    value={d.text}
                    onChange={(e) => upd(d.id, { text: e.target.value })}
                    placeholder={"Name: …\nCard ID: …\nDOB: …"}
                  />
                )}

                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  aria-label={`Remove document ${i + 1}`}
                  onClick={() => set("docs", f.docs.filter((x) => x.id !== d.id))}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>

          <div className="card card-pad review">
            <h3 style={{ marginBottom: 14 }}>Intake Summary Before Verification</h3>
            <dl>
              <dt>Case ID</dt>
              <dd className="mono">{f.case_id}</dd>
              <dt>Patient</dt>
              <dd>
                <b>{f.name}</b> · Card {f.card_id}
              </dd>
              <dt>Hospital</dt>
              <dd>{hospital?.name ?? "—"}</dd>
              <dt>Procedure</dt>
              <dd>{pkg ? `${pkg.name} (Tier ${pkg.tier})` : "—"}</dd>
              <dt>Refusal Stated</dt>
              <dd>“{f.reason}”</dd>
              <dt>Referral Status</dt>
              <dd>{f.ref_present === "yes" ? `Issued on ${f.ref_date}` : "Not provided at admission"}</dd>
              <dt>Financial Demand</dt>
              <dd>{f.pay ? `₹${f.amount} demanded for ${f.purpose}` : "None (Cashless denied without cash demand)"}</dd>
              <dt>Attached Files</dt>
              <dd>
                <b>{f.docs.length}</b> verified document(s)
              </dd>
            </dl>
          </div>

          {fail && <Alert kind="err">{fail}</Alert>}
        </>
      )}

      {/* Navigation Buttons */}
      <div className="spread no-print">
        <button
          className="btn btn-ghost"
          disabled={step === 0 || busy}
          onClick={() => setStep(step - 1)}
        >
          <ArrowLeft size={16} /> Back
        </button>

        {step < 3 ? (
          <button className="btn btn-ink" onClick={next}>
            Next Step <ArrowRight size={16} />
          </button>
        ) : (
          <button
            className="btn btn-primary btn-lg"
            disabled={busy}
            onClick={submit}
            style={{ padding: "14px 28px", fontSize: "1.05rem" }}
          >
            {busy ? (
              <>
                <Spinner /> Cross-Checking 31 Guidelines…
              </>
            ) : (
              <>
                <Send size={18} /> Analyze & Prepare Clearance Memo →
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
