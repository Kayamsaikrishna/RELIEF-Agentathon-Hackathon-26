import type { Blocker, CaseStatus } from "./api/types";

export const BLOCKERS: Record<Blocker, { label: string; letter: string; blurb: string; tone: string }> = {
  REFERRAL: { label: "Referral", letter: "R", blurb: "A needed referral is missing, expired or issued late.", tone: "orange" },
  ENTITLEMENT: { label: "Entitlement", letter: "E", blurb: "The beneficiary lookup did not confirm the card.", tone: "ink" },
  LINKAGE: { label: "Linkage", letter: "L", blurb: "Names, dates or ids disagree between documents.", tone: "orange" },
  IMPROPER_CHARGE: { label: "Improper charge", letter: "I", blurb: "Money was asked for under a cashless scheme.", tone: "red" },
  EMPANELMENT: { label: "Empanelment", letter: "E", blurb: "The hospital is not listed for this procedure.", tone: "ink" },
  FORMS: { label: "Forms", letter: "F", blurb: "A required document is missing from the file.", tone: "orange" },
  ESCALATION_ONLY: { label: "Delay — escalate", letter: "!", blurb: "All checks look consistent but a decision is overdue.", tone: "red" },
  INSUFFICIENT_EVIDENCE: { label: "Needs a person", letter: "?", blurb: "Not enough evidence to name a blocker.", tone: "muted" },
};

export const STATUS: Record<CaseStatus, { label: string; tone: string }> = {
  running: { label: "Analysing", tone: "blue" },
  awaiting_approval: { label: "Needs approval", tone: "orange" },
  handover: { label: "Handed to a person", tone: "muted" },
  approved: { label: "Approved", tone: "green" },
  rejected: { label: "Rejected", tone: "red" },
  completed: { label: "Completed", tone: "green" },
  error: { label: "Error", tone: "red" },
};

export const DOC_KINDS: Record<string, string> = {
  card: "Health card", id_proof: "ID proof", referral_letter: "Referral letter", preauth_form: "Pre-authorisation form",
  refusal_note: "Refusal note", clinical_notes: "Clinical notes", diagnostic_report: "Diagnostic report", bill: "Bill", discharge_summary: "Discharge summary",
};

export const fmtDate = (s?: string | null) => (s ? new Date(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—");
export const fmtDateTime = (s?: string | null) => (s ? new Date(s).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");
export const ago = (s: string) => {
  const m = Math.round((Date.now() - new Date(s).getTime()) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
};
export const initials = (n: string) => n.split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
