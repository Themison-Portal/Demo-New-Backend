"""
Collaboration AI routes (Phase 3 of LLM consolidation).

Replaces the five `invokeLLM` call sites in
`Demo-New-Frontend/server/collaborationRouter.ts`:
- generateAIResponse         (line 270)   -> POST /respond
- draftEmailWithAI           (line 589)   -> POST /draft-email
- threads.resolve (AI summary, line 1212) -> POST /summarize-thread
- triageEmail                (line 2042)  -> POST /triage-email
- suggestResolution          (line 2200)  -> POST /suggest-resolution

Each endpoint assembles the prompt server-side and forwards to the RAG
service via `RagClient.generate(...)`. The FE no longer holds prompts,
schemas, or any LLM credentials.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.clients.rag_client import get_rag_client
from app.contracts.collaboration_ai import (
    CollabRespondRequest,
    CollabRespondResponse,
    DraftEmailRequest,
    DraftEmailResponse,
    DraftEmailResult,
    ProtocolRef,
    SuggestResolutionRequest,
    SuggestResolutionResponse,
    SummarizeThreadRequest,
    SummarizeThreadResponse,
    TriageEmailRequest,
    TriageEmailResponse,
    TriageResult,
)
from app.dependencies.auth import get_current_member
from app.models.members import Member

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────


_TRIAGE_LABEL_VOCAB = [
    "urgent",
    "action_required",
    "fyi",
    "sponsor_query",
    "system_notification",
    "irb_correspondence",
    "lab_alert",
    "enrollment_update",
    "safety_report",
    "administrative",
]


def _relax_for_tool_use(schema: dict) -> dict:
    """Strip `additionalProperties: false` recursively — Anthropic's tool
    input_schema rejects it at some nested positions."""
    if not isinstance(schema, dict):
        return schema
    out = {k: v for k, v in schema.items() if k != "additionalProperties"}
    for key, val in list(out.items()):
        if isinstance(val, dict):
            out[key] = _relax_for_tool_use(val)
        elif isinstance(val, list):
            out[key] = [_relax_for_tool_use(item) if isinstance(item, dict) else item for item in val]
    return out


def _parse_json_content_or_500(raw: str, endpoint_label: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("%s: invalid JSON from model: %s", endpoint_label, raw[:300])
        raise HTTPException(status_code=502, detail=f"LLM returned non-JSON: {e}")


# ─────────────────────────────────────────
# 1. /respond — context-grounded answer for collab chat
# ─────────────────────────────────────────


@router.post("/respond", response_model=CollabRespondResponse)
async def respond(
    payload: CollabRespondRequest,
    member: Member = Depends(get_current_member),
) -> CollabRespondResponse:
    """Generate a Themison-AI reply for a collaboration message thread."""
    system_lines = [
        f"You are Themison AI for trial {payload.trial_name or payload.trial_id} "
        f"({payload.trial_protocol_number or 'N/A'}).",
        "Agents that prepare, humans approve: never imply autonomous execution.",
        "Use concise and practical language.",
        "Always include citations in format: [Source: Document, Section].",
        "If patient safety or clinical judgment is required, direct to PI/medical monitor.",
        f"Layer: {payload.layer}.",
        f"User: {payload.user_name or 'Unknown'} ({payload.user_role or 'user'}).",
    ]
    system_prompt = "\n".join(system_lines)

    context_message = (
        f"Retrieved protocol sources:\n{payload.source_context}"
        if payload.source_context
        else "No protocol chunks were retrieved; be explicit about uncertainty."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for m in payload.recent_messages:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": f"{context_message}\n\nQuestion: {payload.question}"})

    rag = get_rag_client()
    try:
        result = await rag.generate(
            messages=messages,
            model_hint="smart",
            max_tokens=800,
            feature_tag=f"collab.respond.member={member.id}",
        )
    except Exception as e:
        logger.exception("collab.respond: RAG generate failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    return CollabRespondResponse(
        text=result["content"].strip(),
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )


# ─────────────────────────────────────────
# 2. /draft-email — generate reply email JSON
# ─────────────────────────────────────────


_DRAFT_EMAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "body": {"type": "string"},
        "protocol_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section": {"type": ["string", "null"]},
                    "quoted_text": {"type": ["string", "null"]},
                },
            },
        },
    },
    "required": ["subject", "body"],
}


@router.post("/draft-email", response_model=DraftEmailResponse)
async def draft_email(
    payload: DraftEmailRequest,
    member: Member = Depends(get_current_member),
) -> DraftEmailResponse:
    """Draft a reply email for a clinical-trial inbox thread."""
    system_lines = [
        "Draft a professional reply email for clinical trial correspondence.",
        f"Incoming subject: {payload.subject}",
        f"From: {payload.from_name or 'Unknown'} <{payload.from_address or ''}>",
    ]
    if payload.ai_summary:
        system_lines.append(f"AI Summary: {payload.ai_summary}")
    if payload.instructions:
        system_lines.append(f"User instructions: {payload.instructions}")
    system_lines.append("Use concise language. Include protocol section references if used.")
    system_lines.append("Do not claim actions are completed unless explicitly stated.")
    system_lines.append("Return JSON with keys: subject, body, protocol_refs.")

    user_blocks = [f"Recent chain messages:\n{payload.recent_messages_formatted}"]
    if payload.protocol_context_formatted:
        user_blocks.append(f"Protocol context:\n{payload.protocol_context_formatted}")

    rag = get_rag_client()
    try:
        result = await rag.generate(
            messages=[
                {"role": "system", "content": "\n".join(system_lines)},
                {"role": "user", "content": "\n\n".join(user_blocks)},
            ],
            response_schema=_relax_for_tool_use(_DRAFT_EMAIL_SCHEMA),
            response_schema_name="email_draft",
            model_hint="smart",
            max_tokens=900,
            feature_tag=f"collab.draft-email.member={member.id}",
        )
    except Exception as e:
        logger.exception("collab.draft-email: RAG generate failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    parsed = _parse_json_content_or_500(result["content"], "collab.draft-email")
    refs_raw = parsed.get("protocol_refs") or []
    refs = [
        ProtocolRef(
            section=r.get("section"),
            quoted_text=r.get("quoted_text"),
        )
        for r in refs_raw
        if isinstance(r, dict)
    ]
    draft = DraftEmailResult(
        subject=parsed.get("subject") or f"Re: {payload.subject}",
        body=parsed.get("body") or "[VERIFY] Draft content unavailable.",
        protocol_refs=refs,
    )
    return DraftEmailResponse(
        draft=draft,
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )


# ─────────────────────────────────────────
# 3. /summarize-thread — 2-4 sentence resolution summary
# ─────────────────────────────────────────


@router.post("/summarize-thread", response_model=SummarizeThreadResponse)
async def summarize_thread(
    payload: SummarizeThreadRequest,
    member: Member = Depends(get_current_member),
) -> SummarizeThreadResponse:
    """Draft a concise resolution summary from a thread's message history."""
    rag = get_rag_client()
    try:
        result = await rag.generate(
            messages=[
                {
                    "role": "system",
                    "content": "Draft a concise 2-4 sentence thread resolution summary for clinical trial operations. Do not invent facts.",
                },
                {
                    "role": "user",
                    "content": payload.messages_formatted or "No messages available.",
                },
            ],
            model_hint="fast",
            max_tokens=260,
            feature_tag=f"collab.summarize-thread.member={member.id}",
        )
    except Exception as e:
        logger.exception("collab.summarize-thread: RAG generate failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    return SummarizeThreadResponse(
        summary=result["content"].strip(),
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )


# ─────────────────────────────────────────
# 4. /triage-email — labels + priority + summary
# ─────────────────────────────────────────


_TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {"type": "string", "enum": _TRIAGE_LABEL_VOCAB},
        },
        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
        "summary": {"type": "string"},
    },
    "required": ["labels", "priority", "summary"],
}


@router.post("/triage-email", response_model=TriageEmailResponse)
async def triage_email(
    payload: TriageEmailRequest,
    member: Member = Depends(get_current_member),
) -> TriageEmailResponse:
    """Classify an inbox email into labels + priority + short summary."""
    system_prompt = (
        "Classify trial email into JSON {labels:string[],priority:'high'|'medium'|'low',summary:string}. "
        f"Use labels from: {','.join(_TRIAGE_LABEL_VOCAB)}."
    )
    user_text = (
        f"From: {payload.from_name or 'Unknown'} <{payload.from_address or ''}>\n"
        f"Subject: {payload.subject}\n"
        f"Body: {payload.body}"
    )

    rag = get_rag_client()
    try:
        result = await rag.generate(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            response_schema=_relax_for_tool_use(_TRIAGE_SCHEMA),
            response_schema_name="email_triage",
            model_hint="fast",
            max_tokens=340,
            feature_tag=f"collab.triage-email.member={member.id}",
        )
    except Exception as e:
        logger.exception("collab.triage-email: RAG generate failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    parsed = _parse_json_content_or_500(result["content"], "collab.triage-email")
    labels_raw = parsed.get("labels") or []
    labels = [str(label).strip() for label in labels_raw if isinstance(label, str) and label.strip()]

    priority = parsed.get("priority")
    if priority not in ("high", "medium", "low"):
        if "urgent" in labels or "action_required" in labels:
            priority = "high"
        elif "fyi" in labels:
            priority = "low"
        else:
            priority = "medium"

    summary = parsed.get("summary") or "Triage summary unavailable."
    triage = TriageResult(labels=labels, priority=priority, summary=summary)
    return TriageEmailResponse(
        triage=triage,
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )


# ─────────────────────────────────────────
# 5. /suggest-resolution — approval-ready summary
# ─────────────────────────────────────────


@router.post("/suggest-resolution", response_model=SuggestResolutionResponse)
async def suggest_resolution(
    payload: SuggestResolutionRequest,
    member: Member = Depends(get_current_member),
) -> SuggestResolutionResponse:
    """Draft an approval-ready resolution summary for a thread."""
    rag = get_rag_client()
    try:
        result = await rag.generate(
            messages=[
                {
                    "role": "system",
                    "content": "Draft a resolution summary for a clinical trial thread. Keep it concise, factual, and approval-ready.",
                },
                {"role": "user", "content": payload.messages_formatted or "No messages available."},
            ],
            model_hint="fast",
            max_tokens=260,
            feature_tag=f"collab.suggest-resolution.member={member.id}",
        )
    except Exception as e:
        logger.exception("collab.suggest-resolution: RAG generate failed")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    return SuggestResolutionResponse(
        summary=result["content"].strip(),
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
    )
