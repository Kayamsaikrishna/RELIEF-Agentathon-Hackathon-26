"""Hospital and package registry.

The registry is a JSON file (see docs/REGISTRY_FORMAT.md). The file shipped in data/registry is a
SYNTHETIC registry for development and evaluation; point RELIEF_REGISTRY_PATH at an official
export in the same format for real use. Every answer says which registry version it came from.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from relief.contracts.schemas import HospitalCheck


class Package(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str
    specialty: str
    tier: str
    reserved_for_public: bool = False
    required_docs: list[str] = Field(default_factory=list)


class Hospital(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hospital_id: str
    name: str
    type: str
    state: str
    district: str
    specialties: list[str]
    empanelment_active: bool = True


class RegistryFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    synthetic: bool = False
    note: str = ""
    packages: list[Package]
    hospitals: list[Hospital]


class Registry:
    def __init__(self, data: RegistryFile):
        self.data = data
        self._packages = {p.code: p for p in data.packages}
        self._hospitals = {h.hospital_id: h for h in data.hospitals}

    @classmethod
    def load(cls, path: Path) -> "Registry":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(RegistryFile.model_validate(json.load(fh)))

    @property
    def version(self) -> str:
        return self.data.version

    @property
    def synthetic(self) -> bool:
        return self.data.synthetic

    def package(self, code: str) -> Optional[Package]:
        if code in self._packages:
            return self._packages[code]
        if code.startswith("SYN-"):
            return self._packages.get(code.replace("SYN-", "NHA-"))
        if code.startswith("NHA-"):
            return self._packages.get(code.replace("NHA-", "SYN-"))
        return None

    def hospital(self, hospital_id: str) -> Optional[Hospital]:
        return self._hospitals.get(hospital_id)

    def hospitals(self) -> list[Hospital]:
        return list(self.data.hospitals)

    def packages(self) -> list[Package]:
        return list(self.data.packages)

    # ------------------------------------------------------------------ tool
    def lookup_hospital(self, hospital_id: str, procedure_code: str) -> HospitalCheck:
        hosp = self.hospital(hospital_id)
        pkg = self.package(procedure_code)
        notes: list[str] = []
        if self.synthetic:
            notes.append(f"Registry {self.version} is synthetic, not an official list.")
        if pkg is None:
            notes.append(f"Procedure code {procedure_code} is not in the registry.")
        if hosp is None:
            notes.append(f"Hospital {hospital_id} is not in the registry.")
            return HospitalCheck(
                found=False, package_listed="yes" if pkg else "unknown", empanelled="unknown",
                specialty=pkg.specialty if pkg else None, procedure_name=pkg.name if pkg else None,
                tier=pkg.tier if pkg else None,  # type: ignore[arg-type]
                reserved_for_public=("yes" if pkg.reserved_for_public else "no") if pkg else "unknown",
                registry_version=self.version, notes=notes,
            )
        empanelled = "unknown"
        if pkg is not None:
            if not hosp.empanelment_active:
                empanelled = "no"
                notes.append("The registry shows this hospital's empanelment as not active.")
            elif pkg.specialty in hosp.specialties:
                empanelled = "yes"
            else:
                empanelled = "no"
                notes.append(f"The hospital is not listed for the specialty {pkg.specialty}.")
        return HospitalCheck(
            found=True, hospital_name=hosp.name,
            hospital_type=hosp.type if hosp.type in ("public", "private") else "unknown",  # type: ignore[arg-type]
            state=hosp.state, district=hosp.district, empanelled=empanelled,  # type: ignore[arg-type]
            package_listed="yes" if pkg else "unknown",
            specialty=pkg.specialty if pkg else None, procedure_name=pkg.name if pkg else None,
            tier=pkg.tier if pkg else None,  # type: ignore[arg-type]
            reserved_for_public=("yes" if pkg.reserved_for_public else "no") if pkg else "unknown",
            registry_version=self.version, notes=notes,
        )

    def alternatives(self, hospital_id: str, procedure_code: str, limit: int = 5) -> list[Hospital]:
        """Hospitals listed for the same specialty, same state, ranked: same district first, public first
        where the package is public-reserved or tier 2A. No distances are available in the registry."""
        pkg = self.package(procedure_code)
        origin = self.hospital(hospital_id)
        if pkg is None:
            return []
        public_only = pkg.reserved_for_public or pkg.tier == "2A"
        out = []
        for h in self.data.hospitals:
            if h.hospital_id == hospital_id or not h.empanelment_active or pkg.specialty not in h.specialties:
                continue
            if origin and h.state != origin.state:
                continue
            if public_only and h.type != "public":
                continue
            out.append(h)

        def rank(h: Hospital) -> tuple:
            same_district = 0 if origin and h.district == origin.district else 1
            public_first = 0 if h.type == "public" else 1
            return (same_district, public_first, h.name)

        return sorted(out, key=rank)[:limit]
