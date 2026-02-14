"""W3C PROV-O compatible provenance tracking.

Implements the core PROV data model concepts:
    Entity   - a physical, digital, or conceptual thing
    Activity - something that occurs over a period of time
    Agent    - something that bears responsibility for an activity

Plus the relations:
    wasGeneratedBy, used, wasAttributedTo, wasDerivedFrom, wasAssociatedWith
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from maris.provenance.storage import InMemoryStorage

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceEntity:
    """A PROV entity - a thing with provenance."""

    entity_id: str
    entity_type: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    generated_by: str | None = None
    derived_from: list[str] = field(default_factory=list)
    attributed_to: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "attributes": self.attributes,
            "generated_by": self.generated_by,
            "derived_from": self.derived_from,
            "attributed_to": self.attributed_to,
            "created_at": self.created_at,
        }


@dataclass
class ProvenanceActivity:
    """A PROV activity - an action that transforms or generates entities."""

    activity_id: str
    activity_type: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str | None = None
    used: list[str] = field(default_factory=list)
    generated: list[str] = field(default_factory=list)
    associated_with: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "activity_type": self.activity_type,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "used": self.used,
            "generated": self.generated,
            "associated_with": self.associated_with,
            "attributes": self.attributes,
        }


@dataclass
class ProvenanceAgent:
    """A PROV agent - responsible for an activity."""

    agent_id: str
    agent_type: str = ""
    name: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "attributes": self.attributes,
        }


class ProvenanceManager:
    """High-level provenance tracking manager.

    Wraps InMemoryStorage with PROV-O semantics. Records entities, activities,
    and agents along with their relationships. Thread-safe through the
    underlying InMemoryStorage.
    """

    def __init__(self, storage: InMemoryStorage | None = None) -> None:
        self._storage = storage or InMemoryStorage()

    @property
    def storage(self) -> InMemoryStorage:
        return self._storage

    # -- Agent management -----------------------------------------------------

    def register_agent(self, agent: ProvenanceAgent) -> None:
        """Register a provenance agent."""
        self._storage.put("agent", agent.agent_id, agent.to_dict())

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        return self._storage.get("agent", agent_id)

    # -- Entity management ----------------------------------------------------

    def track_entity(
        self,
        entity_id: str,
        entity_type: str = "",
        attributes: dict[str, Any] | None = None,
        generated_by: str | None = None,
        derived_from: list[str] | None = None,
        attributed_to: str | None = None,
    ) -> ProvenanceEntity:
        """Create and store a provenance entity."""
        entity = ProvenanceEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            attributes=attributes or {},
            generated_by=generated_by,
            derived_from=derived_from or [],
            attributed_to=attributed_to,
        )
        self._storage.put("entity", entity_id, entity.to_dict())
        return entity

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        return self._storage.get("entity", entity_id)

    # -- Activity management --------------------------------------------------

    def record_activity(
        self,
        activity_type: str = "",
        used: list[str] | None = None,
        generated: list[str] | None = None,
        associated_with: str | None = None,
        attributes: dict[str, Any] | None = None,
        activity_id: str | None = None,
    ) -> ProvenanceActivity:
        """Record a provenance activity."""
        aid = activity_id or f"activity:{uuid.uuid4().hex[:12]}"
        activity = ProvenanceActivity(
            activity_id=aid,
            activity_type=activity_type,
            used=used or [],
            generated=generated or [],
            associated_with=associated_with,
            attributes=attributes or {},
        )
        self._storage.put("activity", aid, activity.to_dict())
        return activity

    def get_activity(self, activity_id: str) -> dict[str, Any] | None:
        return self._storage.get("activity", activity_id)

    # -- Lineage queries ------------------------------------------------------

    def get_lineage(self, entity_id: str, max_depth: int = 10) -> list[dict[str, Any]]:
        """Walk the derivation chain for an entity.

        Returns the entity itself plus all ancestors reachable via
        derived_from links, up to max_depth hops.
        """
        visited: set[str] = set()
        chain: list[dict[str, Any]] = []
        queue = [entity_id]
        depth = 0

        while queue and depth < max_depth:
            next_queue: list[str] = []
            for eid in queue:
                if eid in visited:
                    continue
                visited.add(eid)
                record = self._storage.get("entity", eid)
                if record is not None:
                    chain.append(record)
                    for parent_id in record.get("derived_from", []):
                        if parent_id not in visited:
                            next_queue.append(parent_id)
            queue = next_queue
            depth += 1

        return chain

    def get_entities_by_type(self, entity_type: str) -> list[dict[str, Any]]:
        """Return all entities of a given type."""
        return self._storage.find("entity", entity_type=entity_type)

    def get_activities_for_entity(self, entity_id: str) -> list[dict[str, Any]]:
        """Return all activities that used or generated an entity."""
        all_activities = self._storage.list_by_type("activity")
        return [
            a for a in all_activities
            if entity_id in a.get("used", []) or entity_id in a.get("generated", [])
        ]

    # -- Summary --------------------------------------------------------------

    def summary(self) -> dict[str, int]:
        """Return counts of entities, activities, and agents."""
        return {
            "entities": self._storage.count("entity"),
            "activities": self._storage.count("activity"),
            "agents": self._storage.count("agent"),
        }
