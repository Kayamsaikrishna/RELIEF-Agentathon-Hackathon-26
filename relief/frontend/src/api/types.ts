export type Role = "admin" | "facilitator";
export interface User { id: number; email: string; name: string; role: Role; active: boolean; created_at?: string; last_login?: string | null }

export type Blocker = "REFERRAL" | "ENTITLEMENT" | "LINKAGE" | "IMPROPER_CHARGE" | "EMPANELMENT" | "FORMS" | "ESCALATION_ONLY" | "INSUFFICIENT_EVIDENCE";
export type CaseStatus = "running" | "awaiting_approval" | "handover" | "approved" | "rejected" | "completed" | "error";
export type Confidence = "low" | "medium" | "high";
export type Tri = "yes" | "no" | "unknown";

export interface Finding { blocker: Blocker; confidence: Confidence; evidence_ids: string[]; rule_ids: string[]; wording: string; source: "rules" | "model" }
export interface ChecklistItem { key: string | null; text: string; required: boolean; rule_id: string | null }
export interface Plan { checklist: ChecklistItem[]; alt_hospitals: string[]; letter_text: string | null; drafts: Record<string, string>; actions: { kind: string; payload: Record<string, unknown> }[]; summary: string }
export interface Verification { citations_ok: boolean; fields_ok: boolean; safety_ok: boolean; forbidden_phrases: string[]; issues: string[]; attempts: number }
export interface Evidence { evidence_id: string; tool: string; summary: string; data: Record<string, unknown>; rule_ids: string[] }
export interface RulePassage { rule_id: string; source_id: string; source_title: string; issuer: string; date: string; url: string; section: string; page: string | null; quote: string; text: string; quote_checked: boolean }
export interface TraceEvent { ts: string; node: string; tool: string | null; kind: "tool" | "model" | "code" | "gate" | "fallback" | "safety" | "error"; input_summary: string; output_summary: string }
export interface Decision { action: "approve" | "edit" | "reject"; note: string; decided_by: string; ts: string }

export interface CaseInputView {
  case_id: string; card: { name: string; card_id: string; family_id?: string | null; dob?: string | null; scheme_name?: string | null; id_type?: string | null; state?: string | null };
  hospital_id: string; procedure_code: string; refusal_reason: string; bis_status: string; synthetic: boolean;
  referral: { present: Tri; issued_on?: string | null }; payment_request?: { amount_inr: number; purpose: string; wallet_exhausted: Tri; disclosed_in_advance: Tri } | null;
  admission_date?: string | null; preauth_submitted_at?: string | null; documents: { doc_id: string; kind: string }[];
}
export interface CaseResult {
  case_id: string; status: CaseStatus; findings: Finding[]; plan: Plan | null; verification: Verification | null;
  handover_missing: string[]; handover_reason: string; emergency_notice: string | null; evidence: Evidence[]; rules_cited: RulePassage[];
  trace: TraceEvent[]; decisions: Decision[]; llm_used: boolean; model: string | null; synthetic: boolean; error: string | null;
  meta: { created_by: string | null; created_at: string; case: CaseInputView };
}
export interface CaseRow { case_id: string; created_at: string; status: CaseStatus; main_blocker: Blocker | null; synthetic: number; created_by: string | null; error: string | null }
export interface Stats { total: number; by_status: Record<string, number>; by_blocker: Record<string, number>; daily: { day: string; n: number }[]; reminders_due: number }
export interface Reminder { id: number; case_id: string; due_at: string; message: string; state: "pending" | "due" | "done" }
export interface Hospital { hospital_id: string; name: string; type: string; district: string; state: string; specialties: string[]; empanelment_active: boolean }
export interface Pkg { code: string; name: string; specialty: string; tier: string; reserved_for_public: boolean; required_docs: string[] }
export interface SystemInfo { version: string; python: string; model: string; model_ok: boolean; model_message: string; embedder: string; embedder_ok: boolean; embedder_message: string; rules: number; rules_checked: number; registry_version: string; registry_synthetic: boolean; hospitals: number; packages: number; users: number }
export interface AuditRow { id: number; ts: string; actor: string; action: string; case_id: string | null; detail: string }
