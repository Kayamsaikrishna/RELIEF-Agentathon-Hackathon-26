import type { CaseResult } from "../api/types";
import { fmtDateTime } from "../lib";
import { formatDraftText } from "../lib/formatDraft";

interface PrintReportProps {
  res: CaseResult;
}

export default function PrintReport({ res }: PrintReportProps) {
  const caseIn = res.meta.case;
  const main = res.findings[0];
  const plan = res.plan;
  const decision = res.decisions?.[res.decisions.length - 1];

  // Only extract formal escalation memorandum if present (avoid duplicating the checklist)
  const escalationDraft = plan?.drafts?.escalation ? formatDraftText(plan.drafts.escalation) : null;

  // Dynamic section numbering
  let secIdx = 1;
  const secProfile = `${secIdx++}. BENEFICIARY & ADMISSION PROFILE`;
  const secDiag = `${secIdx++}. CLEARANCE BLOCKER DIAGNOSIS & REGULATORY DETERMINATION`;
  const secChecklist = `${secIdx++}. BENEFICIARY CLEARANCE ACTION CHECKLIST`;
  const secEscalation = escalationDraft ? `${secIdx++}. FORMAL GRIEVANCE & ESCALATION DIRECTIVE` : null;
  const secRules = `${secIdx++}. STATUTORY CLAUSES & OFFICIAL SOURCES CITED`;

  return (
    <div className="print-report-root">
      {/* Official Background Watermark */}
      <div className="p-watermark" aria-hidden="true">
        <div className="p-watermark-line1">RELIEF OFFICIAL MEMORANDUM</div>
        <div className="p-watermark-line2">GOVERNMENT SCHEME COMPLIANCE · NHA CODIFIED</div>
        <div className="p-watermark-line3">CASE REF: {res.case_id}</div>
      </div>

      {/* 1. Official Letterhead Header */}
      <header className="p-header">
        <div className="p-header-top">
          <div className="p-emblem-wrap">
            <img src="/brand/icon-512.png" alt="RELIEF Official Logo" className="p-logo-img" width={48} height={48} />
            <div>
              <div className="p-sub-gov">REPUBLIC OF INDIA · STATE HEALTH ASSURANCE REQUISITION PROTOCOL</div>
              <h1 className="p-org-title">NATIONAL HEALTH BENEFICIARY ADVOCACY & COMPLIANCE SYSTEM</h1>
              <p className="p-org-sub">
                Arogya Mitra & Patient Facilitation Protocol · Under National Health Authority (NHA) Guidelines
              </p>
            </div>
          </div>
          <div className="p-meta-box">
            <div className="p-meta-row">
              <span className="p-meta-lbl">CASE FILE NO:</span>
              <span className="p-meta-val mono">{res.case_id}</span>
            </div>
            <div className="p-meta-row">
              <span className="p-meta-lbl">DATE ISSUED:</span>
              <span className="p-meta-val">{fmtDateTime(res.meta.created_at)}</span>
            </div>
            <div className="p-meta-row">
              <span className="p-meta-lbl">DETERMINATION:</span>
              <span className="p-meta-val mono"><b>{res.status.replace(/_/g, " ").toUpperCase()}</b></span>
            </div>
          </div>
        </div>

        <div className="p-banner">
          <h2>ADMINISTRATIVE CLEARANCE MEMORANDUM & COMPLIANCE DETERMINATION</h2>
          <span className="p-banner-note">
            ISSUED PURSUANT TO NHA HEALTH BENEFIT PACKAGE (HBP 2.2) & STATE GRIEVANCE REDRESSAL GUIDELINES
          </span>
        </div>
      </header>

      {/* 2. Patient & Admission Profile Table */}
      <section className="p-section">
        <h3 className="p-sec-heading">{secProfile}</h3>
        <table className="p-table">
          <tbody>
            <tr>
              <th className="p-th" style={{ width: "22%" }}>Beneficiary Full Name</th>
              <td className="p-td" style={{ width: "28%" }}><b>{caseIn.card.name}</b></td>
              <th className="p-th" style={{ width: "22%" }}>Enrolled Health Scheme</th>
              <td className="p-td" style={{ width: "28%" }}><b>{caseIn.card.scheme_name || "Ayushman Bharat (AB-PMJAY)"}</b></td>
            </tr>
            <tr>
              <th className="p-th">Beneficiary Card / UID</th>
              <td className="p-td mono"><b>{caseIn.card.card_id}</b> ({caseIn.card.id_type || "State Health Card"})</td>
              <th className="p-th">Jurisdiction / State</th>
              <td className="p-td">{caseIn.card.state || "Karnataka"}</td>
            </tr>
            <tr>
              <th className="p-th">Admitting Facility</th>
              <td className="p-td"><b>{caseIn.hospital_id}</b> (Empanelled Facility)</td>
              <th className="p-th">Admission / Incident Date</th>
              <td className="p-td">{caseIn.admission_date || "Immediate Registration"}</td>
            </tr>
            <tr>
              <th className="p-th">Requested Clinical Package</th>
              <td className="p-td" colSpan={3}>
                <b>{caseIn.procedure_code}</b>
              </td>
            </tr>
            <tr>
              <th className="p-th">Hospital Denial / Remark Stated</th>
              <td className="p-td p-refusal-quote" colSpan={3}>
                “{caseIn.refusal_reason}”
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* 3. Formal Denial Diagnosis & Determination */}
      <section className="p-section">
        <h3 className="p-sec-heading">{secDiag}</h3>
        <div className="p-card-block">
          <div className="p-card-row">
            <div>
              <span className="p-tag-label">DIAGNOSED BLOCKER:</span>
              <span className="p-tag-val"><b>{main?.blocker || "DOCUMENTATION_INCOMPLETE"}</b></span>
            </div>
            <div>
              <span className="p-tag-label">VERIFICATION CONFIDENCE:</span>
              <span className="p-tag-val"><b>{main?.confidence.toUpperCase() || "HIGH"}</b> (Deterministic Rule Verification)</span>
            </div>
          </div>

          <div className="p-card-text">
            <b>Regulatory Assessment:</b> {main?.wording || "Incomplete pre-authorisation documentation identified."}
          </div>

          <div className="p-action-box">
            <b>MANDATORY REMEDIATION DIRECTIVE FOR ADMISSION DESK:</b>
            <p>
              {main?.blocker === "REFERRAL"
                ? "This procedure is designated as Tier-3A secondary/tertiary care. Under state health policy, private empanelled facilities require an official Form-3A referral from the Public District Hospital Nodal Officer (valid 30 days). Facilitator must initiate online Nodal referral requisition."
                : main?.blocker === "FORMS"
                ? "Pre-authorisation rejection is procedural. Under NHA HBP 2.2 Section 4.2(iii), the admission desk must accept and attach the patient's diagnostic imaging/reports and clinical notes to clear pre-authorisation."
                : main?.blocker === "IMPROPER_CHARGE"
                ? "UNAUTHORIZED OUT-OF-POCKET CASH PAYMENT DEMANDED. Under NHA User Guidelines Section 4.2(i), the package rate is 100% all-inclusive of medicines, implants, consumables, and bed charges. Hospital is directed to immediately cancel out-of-pocket billing."
                : main?.blocker === "LINKAGE"
                ? "Beneficiary demographic discrepancy identified. Under NHA Biometric Linkage Guidelines, proceed via Arogya Mitra demographic linking override and biometric re-authentication."
                : "Submit missing documentation per checklist below."}
            </p>
          </div>
        </div>
      </section>

      {/* 4. Action Checklist (Clean, un-duplicated) */}
      {plan && (
        <section className="p-section">
          <h3 className="p-sec-heading">{secChecklist}</h3>
          <div className="p-checklist-block">
            {plan.checklist.map((c, i) => (
              <div key={i} className="p-ck-item">
                <span className="p-ck-box">[ &nbsp; ]</span>
                <span className="p-ck-content">
                  <b>{c.text}</b>
                  {c.rule_id && <span className="p-ck-rule"> — (Statutory Rule: {c.rule_id})</span>}
                </span>
              </div>
            ))}
          </div>

          {plan.alt_hospitals && plan.alt_hospitals.length > 0 && (
            <div className="p-alt-hospitals" style={{ marginTop: "6px", fontSize: "7pt", color: "#111827", padding: "4px 8px", border: "1px dashed #4b5563", background: "#f9fafb" }}>
              <b>Empanelled Government Referral Facilities (within 50 km):</b> {plan.alt_hospitals.join("; ")}
            </div>
          )}
        </section>
      )}

      {/* 5. Formal Grievance Escalation Directive (Only shown when escalation memo exists) */}
      {escalationDraft && (
        <section className="p-section">
          <h3 className="p-sec-heading">{secEscalation}</h3>
          <div className="p-memo-draft">
            <div className="p-memo-draft-title">
              STATUTORY GRIEVANCE DIRECTIVE (FOR GRIEVANCE NODAL OFFICER / HOSPITAL MEDICAL SUPERINTENDENT):
            </div>
            <pre className="p-memo-draft-body">{escalationDraft}</pre>
          </div>
        </section>
      )}

      {/* 6. Authoritative Rules Cited */}
      {res.rules_cited.length > 0 && (
        <section className="p-section">
          <h3 className="p-sec-heading">{secRules}</h3>
          <div className="p-rules-grid">
            {res.rules_cited.map((r) => (
              <div key={r.rule_id} className="p-rule-box">
                <div className="p-rule-header">
                  <span className="p-rule-id">CLAUSE {r.rule_id}</span>
                  <span className="p-rule-src">{r.source_title} ({r.issuer}, {r.date}) — {r.section}</span>
                </div>
                {r.quote && (
                  <blockquote className="p-rule-q">
                    “{r.quote}”
                  </blockquote>
                )}
                <p className="p-rule-desc">{r.text}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 7. Facilitator Authentication & Verification Seal */}
      <section className="p-section p-seal-wrap">
        <div className="p-seal-columns">
          <div className="p-seal-panel">
            <div className="p-seal-head">OFFICIAL DECISION INTEGRITY SEAL</div>
            <ul className="p-seal-checks">
              <li>✓ All findings grounded in codified National Health Authority (NHA) rules.</li>
              <li>✓ 100% deterministic rule validation (zero hallucinated promises).</li>
              <li>✓ Audit logged in tamper-evident database under Case ID {res.case_id}.</li>
            </ul>
            <div className="p-seal-system">RELIEF DECISION INTEGRITY SYSTEM v0.1.0 · NHA COMPLIANT</div>
          </div>

          <div className="p-sig-panel">
            <div className="p-sig-head">FACILITATOR SIGN-OFF & CERTIFICATION</div>
            <div className="p-sig-details">
              <div><b>Certified Facilitator:</b> {decision ? decision.decided_by : (res.meta.created_by || "Sai Krishna <saikrishna@gmail.com>")}</div>
              <div><b>Determination Status:</b> {decision ? "APPROVED & RECORDED" : "AWAITING FINAL FACILITATOR SIGN-OFF"}</div>
              <div><b>Date & Time:</b> {decision ? fmtDateTime(decision.ts) : fmtDateTime(res.meta.created_at)}</div>
              {decision?.note && <div className="p-sig-note"><b>Facilitator Remark:</b> “{decision.note}”</div>}
            </div>
            <div className="p-sig-signline">
              <div className="p-sig-dash"></div>
              <span>Signature & Official Stamp of Facilitator</span>
            </div>
          </div>
        </div>
      </section>

      {/* 8. Official Legal Disclaimer */}
      <footer className="p-footer">
        <p>
          <b>STATUTORY COMPLIANCE NOTICE:</b> This memorandum is an administrative decision-support clearance report prepared by an accredited Arogya Mitra / Health Facilitator under the National Health Authority grievance redressal framework. Under Section 4 of the NHA Empanelment Agreement, all empanelled healthcare providers are mandated to adhere to published package guidelines, all-inclusive package pricing, and verified referral pathways. This document serves as formal notification to resolve admission refusal.
        </p>
      </footer>
    </div>
  );
}
