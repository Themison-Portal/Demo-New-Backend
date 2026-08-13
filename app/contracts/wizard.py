"""
Contracts for the study-setup wizard endpoints.

Field names use Python snake_case but are exposed to the FE as camelCase via
pydantic aliases — this preserves the JSON shape the FE is already wired for
(it consumed identical keys when calling OpenAI directly).
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class _CamelModel(BaseModel):
    """Base for wizard contracts: serialize/parse with camelCase JSON keys."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=_camel,
    )


# ─────────────────────────────────────────
# /api/wizard/extract-metadata
# ─────────────────────────────────────────


class ExtractMetadataRequest(_CamelModel):
    protocol_filename: str
    protocol_content: str  # Pre-extracted text from the PDF (FE does pdf-parse).


class ProtocolMetadata(_CamelModel):
    protocol_title: Optional[str] = None
    protocol_number: Optional[str] = None
    sponsor: Optional[str] = None
    phase: Optional[str] = None
    investigational_product: Optional[str] = None
    indication: Optional[str] = None
    nct_number: Optional[str] = None
    current_version: Optional[str] = None
    amendment_version: Optional[str] = None
    release_date: Optional[str] = None
    location: Optional[str] = None
    sample_size: Optional[str] = None
    number_of_sites: Optional[str] = None
    study_duration: Optional[str] = None
    study_design_type: Optional[str] = None
    primary_objective: Optional[str] = None
    primary_endpoint: Optional[str] = None


class ExtractMetadataResponse(_CamelModel):
    extracted: ProtocolMetadata
    model: str
    prompt_tokens: int
    completion_tokens: int


# ─────────────────────────────────────────
# /api/wizard/generate-scaffold
# ─────────────────────────────────────────


class GenerateScaffoldRequest(_CamelModel):
    protocol_filename: str
    protocol_content: str
    # Optional pre-formatted context block (the FE produces this from its
    # protocolContext chunker today; can be empty/None).
    context_chunks_text: Optional[str] = None


class ProtocolReference(_CamelModel):
    section: str
    page: Optional[int] = None
    extracted_text: Optional[str] = None


class ScaffoldTask(_CamelModel):
    name: str
    suggested_date: Optional[str] = None
    estimated_duration: Optional[float] = None
    category: str
    assigned_role: Optional[str] = None
    priority: str
    protocol_reference: ProtocolReference
    ai_confidence: Optional[float] = None
    conditional_note: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)


class ScaffoldTransition(_CamelModel):
    to_phase: str
    condition: Optional[str] = None


class ScaffoldPhase(_CamelModel):
    name: str
    color: str
    tasks: List[ScaffoldTask] = Field(default_factory=list)
    transitions: List[ScaffoldTransition] = Field(default_factory=list)


class ProtocolSectionChild(_CamelModel):
    name: str
    date_reference: Optional[str] = None
    page_reference: Optional[str] = None


class ProtocolSection(_CamelModel):
    name: str
    date_reference: Optional[str] = None
    page_reference: Optional[str] = None
    children: List[ProtocolSectionChild] = Field(default_factory=list)


class TaskScaffold(_CamelModel):
    protocol_sections: List[ProtocolSection] = Field(default_factory=list)
    phases: List[ScaffoldPhase] = Field(default_factory=list)


class GenerateScaffoldResponse(_CamelModel):
    scaffold: TaskScaffold
    model: str
    prompt_tokens: int
    completion_tokens: int
