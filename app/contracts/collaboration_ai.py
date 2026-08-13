"""
Contracts for the collaboration AI endpoints.

Each endpoint mirrors a `invokeLLM` call site that used to live in
`Demo-New-Frontend/server/collaborationRouter.ts`. CamelCase aliases keep
the JSON shape compatible with what the FE was already sending/receiving.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def _camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class _CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_camel)


# ─────────────────────────────────────────
# /api/collaboration/ai/respond
# (replaces generateAIResponse — collaborationRouter.ts:270)
# ─────────────────────────────────────────


class CollabRecentMessage(_CamelModel):
    role: Literal["user", "assistant"]
    content: str


class CollabRespondRequest(_CamelModel):
    trial_id: str
    trial_name: Optional[str] = None
    trial_protocol_number: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    layer: str  # "messages" | "threads" | "inbox" etc — caller's domain
    question: str
    source_context: Optional[str] = None  # pre-formatted source citations block
    recent_messages: List[CollabRecentMessage] = Field(default_factory=list)


class CollabRespondResponse(_CamelModel):
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int


# ─────────────────────────────────────────
# /api/collaboration/ai/draft-email
# (replaces draftEmailWithAI — collaborationRouter.ts:589)
# ─────────────────────────────────────────


class DraftEmailRequest(_CamelModel):
    subject: str
    from_name: Optional[str] = None
    from_address: Optional[str] = None
    ai_summary: Optional[str] = None
    instructions: Optional[str] = None
    recent_messages_formatted: str  # caller pre-formats the chain history
    protocol_context_formatted: Optional[str] = None  # caller pre-formats chunks


class ProtocolRef(_CamelModel):
    section: Optional[str] = None
    quoted_text: Optional[str] = None


class DraftEmailResult(_CamelModel):
    subject: str
    body: str
    protocol_refs: List[ProtocolRef] = Field(default_factory=list)


class DraftEmailResponse(_CamelModel):
    draft: DraftEmailResult
    model: str
    prompt_tokens: int
    completion_tokens: int


# ─────────────────────────────────────────
# /api/collaboration/ai/summarize-thread
# (replaces threads.resolve LLM call — collaborationRouter.ts:1212)
# ─────────────────────────────────────────


class SummarizeThreadRequest(_CamelModel):
    # Pre-joined string: "Sender: content\nSender: content..."
    messages_formatted: str


class SummarizeThreadResponse(_CamelModel):
    summary: str
    model: str
    prompt_tokens: int
    completion_tokens: int


# ─────────────────────────────────────────
# /api/collaboration/ai/triage-email
# (replaces triageEmail — collaborationRouter.ts:2042)
# ─────────────────────────────────────────


class TriageEmailRequest(_CamelModel):
    subject: str
    from_name: Optional[str] = None
    from_address: Optional[str] = None
    body: str


class TriageResult(_CamelModel):
    labels: List[str] = Field(default_factory=list)
    priority: Literal["high", "medium", "low"]
    summary: str


class TriageEmailResponse(_CamelModel):
    triage: TriageResult
    model: str
    prompt_tokens: int
    completion_tokens: int


# ─────────────────────────────────────────
# /api/collaboration/ai/suggest-resolution
# (replaces suggestResolution — collaborationRouter.ts:2200)
# ─────────────────────────────────────────


class SuggestResolutionRequest(_CamelModel):
    messages_formatted: str


class SuggestResolutionResponse(_CamelModel):
    summary: str
    model: str
    prompt_tokens: int
    completion_tokens: int
