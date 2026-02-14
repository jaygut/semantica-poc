"""Pydantic v2 models for multi-site characterization pipeline."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CharacterizationTier(str, Enum):
    """Depth tier for site characterization.

    Bronze: governance metadata only (MPA node in graph).
    Silver: governance + species + habitats + ecosystem services.
    Gold: full case-study-level characterization with trophic network.
    """
    bronze = "bronze"
    silver = "silver"
    gold = "gold"


class CoordinatePair(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class SpeciesRecord(BaseModel):
    scientific_name: str
    common_name: str = ""
    worms_aphia_id: int | None = None
    trophic_level: float | None = None
    functional_group: str = ""
    conservation_status: str = ""


class HabitatInfo(BaseModel):
    habitat_id: str
    name: str = ""
    extent_km2: float | None = None
    confidence: float = 0.0


class EcosystemServiceEstimate(BaseModel):
    service_type: str
    service_name: str = ""
    annual_value_usd: float | None = None
    valuation_method: str = ""
    axiom_ids_used: list[str] = Field(default_factory=list)
    ci_low: float | None = None
    ci_high: float | None = None


class SiteCharacterization(BaseModel):
    """Full characterization of an MPA site at a given tier."""

    canonical_name: str
    tier: CharacterizationTier = CharacterizationTier.bronze
    country: str = ""
    area_km2: float | None = None
    designation_year: int | None = None
    coordinates: CoordinatePair | None = None
    iucn_category: str = ""
    mrgid: int | None = None

    # NEOLI assessment
    neoli_score: int | None = None
    neoli_criteria: dict[str, bool] = Field(default_factory=dict)
    asset_rating: str = ""

    # Silver+ fields
    species: list[SpeciesRecord] = Field(default_factory=list)
    habitats: list[HabitatInfo] = Field(default_factory=list)
    ecosystem_services: list[EcosystemServiceEstimate] = Field(default_factory=list)

    # ESV
    estimated_esv_usd: float | None = None
    esv_confidence: dict[str, Any] = Field(default_factory=dict)

    # Provenance
    case_study_path: str | None = None
    data_sources: list[str] = Field(default_factory=list)

    # Validation
    validated: bool = False
    validation_date: date | None = None

    @field_validator("neoli_score")
    @classmethod
    def validate_neoli(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 5):
            raise ValueError("NEOLI score must be between 0 and 5")
        return v

    @field_validator("area_km2")
    @classmethod
    def validate_area(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("Area must be positive")
        return v

    def to_population_dict(self) -> dict[str, Any]:
        """Convert to the dict format expected by population.py for Neo4j MERGE."""
        result: dict[str, Any] = {
            "name": self.canonical_name,
            "country": self.country,
            "area_km2": self.area_km2,
            "designation_year": self.designation_year,
        }
        if self.coordinates:
            result["lat"] = self.coordinates.latitude
            result["lon"] = self.coordinates.longitude
        if self.neoli_score is not None:
            result["neoli_score"] = self.neoli_score
        if self.asset_rating:
            result["asset_rating"] = self.asset_rating
        if self.estimated_esv_usd is not None:
            result["total_esv_usd"] = self.estimated_esv_usd
        if self.iucn_category:
            result["iucn_category"] = self.iucn_category
        return result
