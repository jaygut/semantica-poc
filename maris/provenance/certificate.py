"""Provenance certificate generation - JSON and Markdown output."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from maris.provenance.core import ProvenanceManager
from maris.provenance.integrity import IntegrityVerifier


class ProvenanceCertificate:
    """Generate provenance certificates for entity lineage chains.

    A certificate includes:
    - Entity metadata and lineage
    - All activities that produced or consumed the entity
    - Source DOIs and evidence chain
    - SHA-256 checksum for integrity verification
    """

    def __init__(self, provenance_manager: ProvenanceManager) -> None:
        self._pm = provenance_manager

    def generate(self, entity_id: str) -> dict[str, Any]:
        """Generate a JSON provenance certificate for an entity.

        Returns a dict with entity details, lineage, activities,
        and an integrity checksum.
        """
        entity = self._pm.get_entity(entity_id)
        if entity is None:
            return {
                "error": f"Entity '{entity_id}' not found",
                "entity_id": entity_id,
            }

        lineage = self._pm.get_lineage(entity_id)
        activities = self._pm.get_activities_for_entity(entity_id)

        # Collect all DOIs from lineage
        dois: list[str] = []
        for record in lineage:
            doi = record.get("attributes", {}).get("doi")
            if doi:
                dois.append(doi)

        certificate_data: dict[str, Any] = {
            "entity_id": entity_id,
            "entity_type": entity.get("entity_type", ""),
            "attributes": entity.get("attributes", {}),
            "lineage": lineage,
            "activities": activities,
            "source_dois": dois,
            "lineage_depth": len(lineage),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Add checksum
        certificate_data["checksum"] = IntegrityVerifier.compute_checksum(certificate_data)

        return certificate_data

    def generate_markdown(self, entity_id: str) -> str:
        """Generate a Markdown-formatted provenance certificate."""
        cert = self.generate(entity_id)

        if "error" in cert:
            return f"# Provenance Certificate\n\n**Error:** {cert['error']}\n"

        lines = [
            "# Provenance Certificate",
            "",
            f"**Entity:** {cert['entity_id']}",
            f"**Type:** {cert['entity_type']}",
            f"**Generated:** {cert['generated_at']}",
            f"**Checksum:** `{cert['checksum']}`",
            "",
        ]

        # Attributes
        attrs = cert.get("attributes", {})
        if attrs:
            lines.append("## Attributes")
            lines.append("")
            for key, val in attrs.items():
                lines.append(f"- **{key}:** {val}")
            lines.append("")

        # Source DOIs
        dois = cert.get("source_dois", [])
        if dois:
            lines.append("## Evidence Sources")
            lines.append("")
            for doi in dois:
                lines.append(f"- DOI: [{doi}](https://doi.org/{doi})")
            lines.append("")

        # Lineage chain
        lineage = cert.get("lineage", [])
        if len(lineage) > 1:
            lines.append("## Lineage Chain")
            lines.append("")
            for i, record in enumerate(lineage):
                prefix = "  " * i
                eid = record.get("entity_id", "?")
                etype = record.get("entity_type", "")
                lines.append(f"{prefix}- {eid} ({etype})")
            lines.append("")

        # Activities
        activities = cert.get("activities", [])
        if activities:
            lines.append("## Activities")
            lines.append("")
            for act in activities:
                lines.append(f"- **{act.get('activity_type', 'activity')}** ({act.get('activity_id', '?')})")
                used = act.get("used", [])
                if used:
                    lines.append(f"  - Used: {', '.join(used)}")
                generated = act.get("generated", [])
                if generated:
                    lines.append(f"  - Generated: {', '.join(generated)}")
            lines.append("")

        return "\n".join(lines)

    def verify(self, certificate: dict[str, Any]) -> bool:
        """Verify the integrity of a provenance certificate.

        Recomputes the checksum excluding the stored checksum field
        and compares it to the stored value.
        """
        stored_checksum = certificate.get("checksum")
        if not stored_checksum:
            return False

        # Recompute without the checksum field
        data_without_checksum = {
            k: v for k, v in certificate.items() if k != "checksum"
        }
        return IntegrityVerifier.verify(data_without_checksum, stored_checksum)
