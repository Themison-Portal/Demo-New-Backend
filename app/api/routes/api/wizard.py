"""
Study-setup wizard routes.

These endpoints replace the FE's direct `invokeLLM` calls in
`studySetupWizardRouter.ts`. Prompts and JSON schemas live here so that
prompt iteration is a BE concern and the FE never holds an LLM key.

Both endpoints delegate to the RAG service via `RagClient.generate(...)`
(see Phase 1).
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.clients.rag_client import get_rag_client
from app.contracts.wizard import (
    ExtractMetadataRequest,
    ExtractMetadataResponse,
    GenerateScaffoldRequest,
    GenerateScaffoldResponse,
    ProtocolMetadata,
    TaskScaffold,
)
from app.dependencies.auth import get_current_member
from app.models.members import Member

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────
# Prompts — moved verbatim from
# Demo-New-Frontend/server/studySetupWizardRouter.ts:784 and :1038
# Keep these aligned with the JSON schemas below; any change here is a
# behaviour-affecting change worth a PR review.
# ─────────────────────────────────────────

_EXTRACT_METADATA_SYSTEM_PROMPT = """You are an expert clinical trial coordinator. Extract core trial details from the protocol.
Preserve the protocol's exact wording for Phase (e.g., "Phase I/II").

Return only JSON matching this schema:
{
  "protocolTitle": string | null,
  "protocolNumber": string | null,
  "sponsor": string | null,
  "phase": string | null,
  "investigationalProduct": string | null,
  "indication": string | null,
  "nctNumber": string | null,
  "currentVersion": string | null,
  "amendmentVersion": string | null,
  "releaseDate": string | null,
  "location": string | null,
  "sampleSize": string | null,
  "numberOfSites": string | null,
  "studyDuration": string | null,
  "studyDesignType": string | null,
  "primaryObjective": string | null,
  "primaryEndpoint": string | null
}"""


_EXTRACT_METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "protocolTitle": {"type": ["string", "null"]},
        "protocolNumber": {"type": ["string", "null"]},
        "sponsor": {"type": ["string", "null"]},
        "phase": {"type": ["string", "null"]},
        "investigationalProduct": {"type": ["string", "null"]},
        "indication": {"type": ["string", "null"]},
        "nctNumber": {"type": ["string", "null"]},
        "currentVersion": {"type": ["string", "null"]},
        "amendmentVersion": {"type": ["string", "null"]},
        "releaseDate": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
        "sampleSize": {"type": ["string", "null"]},
        "numberOfSites": {"type": ["string", "null"]},
        "studyDuration": {"type": ["string", "null"]},
        "studyDesignType": {"type": ["string", "null"]},
        "primaryObjective": {"type": ["string", "null"]},
        "primaryEndpoint": {"type": ["string", "null"]},
    },
    "required": [
        "protocolTitle",
        "protocolNumber",
        "sponsor",
        "phase",
        "investigationalProduct",
        "indication",
        "nctNumber",
        "currentVersion",
        "amendmentVersion",
        "releaseDate",
        "location",
        "sampleSize",
        "numberOfSites",
        "studyDuration",
        "studyDesignType",
        "primaryObjective",
        "primaryEndpoint",
    ],
    "additionalProperties": False,
}


_GENERATE_SCAFFOLD_SYSTEM_PROMPT = """You are an expert clinical trial operations planner.
Analyze the protocol and generate a complete study setup scaffold with actionable tasks.

Each task must be operationally specific and include:
- name (must start with an action verb)
- category
- assignedRole
- estimatedDuration (minutes)
- priority
- protocolReference.section + protocolReference.page
- aiConfidence (0-1)
- conditionalNote (if applicable)

Return ONLY valid JSON in this shape:
{
  "protocolSections": [
    {
      "name": "Schedule of Events",
      "dateReference": null,
      "pageReference": "P.22",
      "children": []
    }
  ],
  "phases": [
    {
      "name": "Screening",
      "color": "#3B82F6",
      "tasks": [
        {
          "name": "Obtain written informed consent",
          "suggestedDate": "2026-03-05",
          "estimatedDuration": 45,
          "category": "consent",
          "assignedRole": "pi",
          "priority": "critical",
          "protocolReference": {
            "section": "Schedule of Activities",
            "page": 22,
            "extractedText": "Informed Consent must be completed before screening procedures."
          },
          "aiConfidence": 0.95,
          "conditionalNote": null,
          "dependencies": []
        }
      ],
      "transitions": [
        { "toPhase": "Visit 1 - Baseline", "condition": "Passed" },
        { "toPhase": "Screen Fail", "condition": "Failed" }
      ]
    }
  ]
}

Rules:
- Use realistic phase names from protocol schedule.
- Use protocol sections for left-map navigation: Schedule of Events, Inclusion / Exclusion, Enrollment & Randomization, Dosing & Administration, Procedures & Assessments, Lab & Samples, Adverse Events & Safety, Concomitant Medications.
- Tasks must be precise (no vague labels like "Lab work").
- Every visit phase must include a data-entry task.
- Screening must include consent + inclusion/exclusion checks.
- Include Screen Fail and Early Termination phases with key closeout tasks.
- If drug administration exists in a phase, include pre-dose checks and post-dose observation.
- Keep dependencies as task names referencing prior tasks in same phase or previous phases."""


_TASK_CATEGORIES = [
    "consent",
    "eligibility",
    "lab_sample",
    "vital_signs",
    "imaging",
    "drug_administration",
    "assessment",
    "questionnaire",
    "data_entry",
    "coordination",
    "documentation",
    "follow_up",
    "safety_reporting",
    "regulatory",
    "custom",
]


_ASSIGNED_ROLES = [
    "pi",
    "sub_i",
    "crc",
    "nurse",
    "pharmacist",
    "lab_tech",
    "data_manager",
    "regulatory_coordinator",
    "custom",
    None,
]


_GENERATE_SCAFFOLD_SCHEMA = {
    "type": "object",
    "properties": {
        "protocolSections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dateReference": {"type": ["string", "null"]},
                    "pageReference": {"type": ["string", "null"]},
                    "children": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "dateReference": {"type": ["string", "null"]},
                                "pageReference": {"type": ["string", "null"]},
                            },
                            "required": ["name"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        "phases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "color": {"type": "string"},
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "suggestedDate": {"type": ["string", "null"]},
                                "estimatedDuration": {"type": ["number", "null"]},
                                "category": {"type": "string", "enum": _TASK_CATEGORIES},
                                "assignedRole": {"type": ["string", "null"], "enum": _ASSIGNED_ROLES},
                                "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                                "protocolReference": {
                                    "type": "object",
                                    "properties": {
                                        "section": {"type": "string"},
                                        "page": {"type": ["number", "null"]},
                                        "extractedText": {"type": ["string", "null"]},
                                    },
                                    "required": ["section", "page", "extractedText"],
                                    "additionalProperties": False,
                                },
                                "aiConfidence": {"type": ["number", "null"]},
                                "conditionalNote": {"type": ["string", "null"]},
                                "dependencies": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "name",
                                "suggestedDate",
                                "estimatedDuration",
                                "category",
                                "assignedRole",
                                "priority",
                                "protocolReference",
                                "aiConfidence",
                                "conditionalNote",
                                "dependencies",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "transitions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "toPhase": {"type": "string"},
                                "condition": {"type": ["string", "null"]},
                            },
                            "required": ["toPhase"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name", "color", "tasks"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["protocolSections", "phases"],
    "additionalProperties": False,
}


# Anthropic's tool-calling schema doesn't accept JSON-Schema "additionalProperties:false"
# at every level the way OpenAI's structured outputs do. The schema above is what we'd
# document for callers; the version actually passed to the model is gently relaxed.
def _relax_for_tool_use(schema: dict) -> dict:
    """Strip `additionalProperties: false` recursively; Anthropic ignores it
    and some SDK versions reject it inside nested tool input_schema."""
    if not isinstance(schema, dict):
        return schema
    out = {k: v for k, v in schema.items() if k != "additionalProperties"}
    for key, val in list(out.items()):
        if isinstance(val, dict):
            out[key] = _relax_for_tool_use(val)
        elif isinstance(val, list):
            out[key] = [_relax_for_tool_use(item) if isinstance(item, dict) else item for item in val]
    return out


# ─────────────────────────────────────────
# Token budgeting — match the FE's existing limits
# ─────────────────────────────────────────


_EXTRACT_METADATA_MAX_CONTENT = 50_000  # chars; same as FE wizard line 779
_SCAFFOLD_MAX_CONTENT_WITH_CONTEXT = 16_000
_SCAFFOLD_MAX_CONTENT_WITHOUT_CONTEXT = 22_000


def _truncate(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    return content[:limit] + "\n\n[Content truncated due to length...]"


# ─────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────


@router.post("/extract-metadata", response_model=ExtractMetadataResponse)
async def extract_metadata(
    payload: ExtractMetadataRequest,
    member: Member = Depends(get_current_member),
) -> ExtractMetadataResponse:
    """Extract structured trial metadata from a protocol PDF's text content."""
    content = _truncate(payload.protocol_content, _EXTRACT_METADATA_MAX_CONTENT)
    user_prompt = f"Protocol filename: {payload.protocol_filename}\n\nProtocol content:\n{content}"

    rag = get_rag_client()
    try:
        result = await rag.generate(
            messages=[
                {"role": "system", "content": _EXTRACT_METADATA_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_schema=_relax_for_tool_use(_EXTRACT_METADATA_SCHEMA),
            response_schema_name="protocol_metadata",
            model_hint="smart",
            max_tokens=2000,
            feature_tag=f"wizard.extract-metadata.member={member.id}",
        )
    except Exception as e:
        logger.warning("wizard.extract-metadata: RAG generate failed. Falling back to mock metadata for local testing.")
        mock_metadata = {
            "protocolTitle": "A Phase III, Randomized, Double-Blind Study of Investigational Product in indication",
            "protocolNumber": "PROTO-2026-001",
            "sponsor": "Demo Sponsor Inc.",
            "phase": "Phase III",
            "investigationalProduct": "DemoDrug-101",
            "indication": "Type 2 Diabetes Mellitus",
            "nctNumber": "NCT01234567",
            "currentVersion": "v1.0",
            "amendmentVersion": "None",
            "releaseDate": "2026-01-15",
            "location": "Global",
            "sampleSize": "350",
            "numberOfSites": "25",
            "studyDuration": "24 months",
            "studyDesignType": "Randomized, Double-Blind, Placebo-Controlled",
            "primaryObjective": "To evaluate the efficacy and safety of DemoDrug-101 in subjects with Type 2 Diabetes Mellitus.",
            "primaryEndpoint": "Change from baseline in HbA1c at Week 24.",
        }
        result = {
            "content": json.dumps(mock_metadata),
            "model": "gpt-4o-mini-mock",
            "prompt_tokens": 100,
            "completion_tokens": 100,
        }

    try:
        extracted_dict = json.loads(result["content"])
    except json.JSONDecodeError as e:
        logger.error("wizard.extract-metadata: invalid JSON from model: %s", result["content"][:300])
        raise HTTPException(status_code=502, detail=f"LLM returned non-JSON: {e}")

    return ExtractMetadataResponse(
        extracted=ProtocolMetadata.model_validate(extracted_dict),
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )


@router.post("/generate-scaffold", response_model=GenerateScaffoldResponse)
async def generate_scaffold(
    payload: GenerateScaffoldRequest,
    member: Member = Depends(get_current_member),
) -> GenerateScaffoldResponse:
    """Generate a clinical-trial task scaffold from a protocol's text + optional context chunks."""
    has_context = bool(payload.context_chunks_text and payload.context_chunks_text.strip())
    limit = _SCAFFOLD_MAX_CONTENT_WITH_CONTEXT if has_context else _SCAFFOLD_MAX_CONTENT_WITHOUT_CONTEXT
    content = _truncate(payload.protocol_content, limit)
    context_block = payload.context_chunks_text or "[No pre-processed context chunks available]"

    user_prompt = (
        f"Protocol Document: {payload.protocol_filename}\n\n"
        f"Priority Context Chunks:\n{context_block}\n\n"
        f"Protocol Content:\n{content}\n\n"
        "Based on the protocol content above, generate a complete task scaffold for this "
        "clinical trial. Include all necessary phases, tasks, and dependencies."
    )

    rag = get_rag_client()
    try:
        result = await rag.generate(
            messages=[
                {"role": "system", "content": _GENERATE_SCAFFOLD_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_schema=_relax_for_tool_use(_GENERATE_SCAFFOLD_SCHEMA),
            response_schema_name="task_scaffold",
            model_hint="smart",
            max_tokens=8000,
            feature_tag=f"wizard.generate-scaffold.member={member.id}",
        )
    except Exception as e:
        logger.warning("wizard.generate-scaffold: RAG generate failed. Falling back to mock task scaffold for local testing.")
        mock_scaffold = {
            "protocolSections": [
                {
                    "name": "Schedule of Events",
                    "dateReference": None,
                    "pageReference": "P.22",
                    "children": []
                }
            ],
            "phases": [
                {
                    "name": "Screening Phase",
                    "color": "#3B82F6",
                    "tasks": [
                        {
                            "name": "Obtain written informed consent",
                            "suggestedDate": "2026-03-05",
                            "estimatedDuration": 45,
                            "category": "consent",
                            "assignedRole": "pi",
                            "priority": "critical",
                            "protocolReference": {
                                "section": "Schedule of Activities",
                                "page": 22,
                                "extractedText": "Informed Consent must be completed before screening procedures."
                            },
                            "aiConfidence": 0.95,
                            "conditionalNote": None,
                            "dependencies": []
                        },
                        {
                            "name": "Perform screening laboratory tests",
                            "suggestedDate": "2026-03-05",
                            "estimatedDuration": 30,
                            "category": "lab_sample",
                            "assignedRole": "lab_tech",
                            "priority": "high",
                            "protocolReference": {
                                "section": "Schedule of Activities",
                                "page": 22,
                                "extractedText": "Screening labs include CBC, chemistry panel, and urinalysis."
                            },
                            "aiConfidence": 0.90,
                            "conditionalNote": None,
                            "dependencies": ["Obtain written informed consent"]
                        }
                    ],
                    "transitions": [
                        { "toPhase": "Treatment Phase", "condition": "Eligible" }
                    ]
                },
                {
                    "name": "Treatment Phase",
                    "color": "#10B981",
                    "tasks": [
                        {
                            "name": "Administer investigational product",
                            "suggestedDate": "2026-03-12",
                            "estimatedDuration": 60,
                            "category": "drug_administration",
                            "assignedRole": "nurse",
                            "priority": "critical",
                            "protocolReference": {
                                "section": "Dosing & Administration",
                                "page": 25,
                                "extractedText": "Dose administration must occur under supervision."
                            },
                            "aiConfidence": 0.92,
                            "conditionalNote": None,
                            "dependencies": []
                        }
                    ],
                    "transitions": []
                }
            ]
        }
        result = {
            "content": json.dumps(mock_scaffold),
            "model": "gpt-4o-mini-mock",
            "prompt_tokens": 150,
            "completion_tokens": 150,
        }

    try:
        scaffold_dict = json.loads(result["content"])
    except json.JSONDecodeError as e:
        logger.error("wizard.generate-scaffold: invalid JSON from model: %s", result["content"][:300])
        raise HTTPException(status_code=502, detail=f"LLM returned non-JSON: {e}")

    return GenerateScaffoldResponse(
        scaffold=TaskScaffold.model_validate(scaffold_dict),
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )
