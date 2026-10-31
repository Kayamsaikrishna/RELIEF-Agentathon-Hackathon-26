"""Document completeness against the package's required list."""
from __future__ import annotations

from relief.contracts.schemas import CaseInput, DocCompleteness, DocKind, HospitalCheck, ReferralCheck
from relief.tools.registry import Registry


def check_documents(case: CaseInput, hospital: HospitalCheck, referral: ReferralCheck, registry: Registry) -> DocCompleteness:
    pkg = registry.package(case.procedure_code)
    if pkg is None:
        return DocCompleteness(status="unknown")
    required: list[DocKind] = []
    for k in pkg.required_docs:
        try:
            required.append(DocKind(k))
        except ValueError:
            continue
    if referral.required == "yes" and DocKind.REFERRAL_LETTER not in required:
        required.append(DocKind.REFERRAL_LETTER)
    provided = list(dict.fromkeys(d.kind for d in case.documents))
    missing = [k for k in required if k not in provided]
    return DocCompleteness(required=required, provided=provided, missing=missing, status="incomplete" if missing else "complete")
