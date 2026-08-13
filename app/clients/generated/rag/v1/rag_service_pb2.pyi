from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class IngestStage(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    INGEST_STAGE_UNSPECIFIED: _ClassVar[IngestStage]
    INGEST_STAGE_DOWNLOADING: _ClassVar[IngestStage]
    INGEST_STAGE_PARSING: _ClassVar[IngestStage]
    INGEST_STAGE_CHUNKING: _ClassVar[IngestStage]
    INGEST_STAGE_EMBEDDING: _ClassVar[IngestStage]
    INGEST_STAGE_STORING: _ClassVar[IngestStage]
    INGEST_STAGE_COMPLETE: _ClassVar[IngestStage]
    INGEST_STAGE_ERROR: _ClassVar[IngestStage]

class Relevance(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RELEVANCE_UNSPECIFIED: _ClassVar[Relevance]
    RELEVANCE_HIGH: _ClassVar[Relevance]
    RELEVANCE_MEDIUM: _ClassVar[Relevance]
    RELEVANCE_LOW: _ClassVar[Relevance]

class ServiceStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SERVICE_STATUS_UNSPECIFIED: _ClassVar[ServiceStatus]
    SERVICE_STATUS_SERVING: _ClassVar[ServiceStatus]
    SERVICE_STATUS_NOT_SERVING: _ClassVar[ServiceStatus]
INGEST_STAGE_UNSPECIFIED: IngestStage
INGEST_STAGE_DOWNLOADING: IngestStage
INGEST_STAGE_PARSING: IngestStage
INGEST_STAGE_CHUNKING: IngestStage
INGEST_STAGE_EMBEDDING: IngestStage
INGEST_STAGE_STORING: IngestStage
INGEST_STAGE_COMPLETE: IngestStage
INGEST_STAGE_ERROR: IngestStage
RELEVANCE_UNSPECIFIED: Relevance
RELEVANCE_HIGH: Relevance
RELEVANCE_MEDIUM: Relevance
RELEVANCE_LOW: Relevance
SERVICE_STATUS_UNSPECIFIED: ServiceStatus
SERVICE_STATUS_SERVING: ServiceStatus
SERVICE_STATUS_NOT_SERVING: ServiceStatus

class IngestPdfRequest(_message.Message):
    __slots__ = ("document_url", "document_id", "chunk_size")
    DOCUMENT_URL_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    CHUNK_SIZE_FIELD_NUMBER: _ClassVar[int]
    document_url: str
    document_id: str
    chunk_size: int
    def __init__(self, document_url: _Optional[str] = ..., document_id: _Optional[str] = ..., chunk_size: _Optional[int] = ...) -> None: ...

class IngestPdfProgress(_message.Message):
    __slots__ = ("stage", "progress_percent", "message", "result")
    STAGE_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_PERCENT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    stage: IngestStage
    progress_percent: int
    message: str
    result: IngestResult
    def __init__(self, stage: _Optional[_Union[IngestStage, str]] = ..., progress_percent: _Optional[int] = ..., message: _Optional[str] = ..., result: _Optional[_Union[IngestResult, _Mapping]] = ...) -> None: ...

class IngestResult(_message.Message):
    __slots__ = ("success", "document_id", "status", "chunks_count", "created_at", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_COUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    document_id: str
    status: str
    chunks_count: int
    created_at: str
    error: str
    def __init__(self, success: bool = ..., document_id: _Optional[str] = ..., status: _Optional[str] = ..., chunks_count: _Optional[int] = ..., created_at: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class QueryRequest(_message.Message):
    __slots__ = ("query", "document_id", "document_name", "top_k", "min_score")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_NAME_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    MIN_SCORE_FIELD_NUMBER: _ClassVar[int]
    query: str
    document_id: str
    document_name: str
    top_k: int
    min_score: float
    def __init__(self, query: _Optional[str] = ..., document_id: _Optional[str] = ..., document_name: _Optional[str] = ..., top_k: _Optional[int] = ..., min_score: _Optional[float] = ...) -> None: ...

class QueryResponse(_message.Message):
    __slots__ = ("answer", "timing", "cache_info")
    ANSWER_FIELD_NUMBER: _ClassVar[int]
    TIMING_FIELD_NUMBER: _ClassVar[int]
    CACHE_INFO_FIELD_NUMBER: _ClassVar[int]
    answer: RagAnswer
    timing: QueryTiming
    cache_info: CacheInfo
    def __init__(self, answer: _Optional[_Union[RagAnswer, _Mapping]] = ..., timing: _Optional[_Union[QueryTiming, _Mapping]] = ..., cache_info: _Optional[_Union[CacheInfo, _Mapping]] = ...) -> None: ...

class RagAnswer(_message.Message):
    __slots__ = ("response", "sources")
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    response: str
    sources: _containers.RepeatedCompositeFieldContainer[RagSource]
    def __init__(self, response: _Optional[str] = ..., sources: _Optional[_Iterable[_Union[RagSource, _Mapping]]] = ...) -> None: ...

class RagSource(_message.Message):
    __slots__ = ("name", "page", "section", "exact_text", "bboxes", "relevance")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    SECTION_FIELD_NUMBER: _ClassVar[int]
    EXACT_TEXT_FIELD_NUMBER: _ClassVar[int]
    BBOXES_FIELD_NUMBER: _ClassVar[int]
    RELEVANCE_FIELD_NUMBER: _ClassVar[int]
    name: str
    page: int
    section: str
    exact_text: str
    bboxes: _containers.RepeatedCompositeFieldContainer[BBox]
    relevance: Relevance
    def __init__(self, name: _Optional[str] = ..., page: _Optional[int] = ..., section: _Optional[str] = ..., exact_text: _Optional[str] = ..., bboxes: _Optional[_Iterable[_Union[BBox, _Mapping]]] = ..., relevance: _Optional[_Union[Relevance, str]] = ...) -> None: ...

class BBox(_message.Message):
    __slots__ = ("x0", "y0", "x1", "y1")
    X0_FIELD_NUMBER: _ClassVar[int]
    Y0_FIELD_NUMBER: _ClassVar[int]
    X1_FIELD_NUMBER: _ClassVar[int]
    Y1_FIELD_NUMBER: _ClassVar[int]
    x0: float
    y0: float
    x1: float
    y1: float
    def __init__(self, x0: _Optional[float] = ..., y0: _Optional[float] = ..., x1: _Optional[float] = ..., y1: _Optional[float] = ...) -> None: ...

class QueryTiming(_message.Message):
    __slots__ = ("embedding_ms", "retrieval_ms", "generation_ms", "total_ms", "chunks_retrieved", "chunks_compressed")
    EMBEDDING_MS_FIELD_NUMBER: _ClassVar[int]
    RETRIEVAL_MS_FIELD_NUMBER: _ClassVar[int]
    GENERATION_MS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_MS_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_RETRIEVED_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_COMPRESSED_FIELD_NUMBER: _ClassVar[int]
    embedding_ms: float
    retrieval_ms: float
    generation_ms: float
    total_ms: float
    chunks_retrieved: int
    chunks_compressed: int
    def __init__(self, embedding_ms: _Optional[float] = ..., retrieval_ms: _Optional[float] = ..., generation_ms: _Optional[float] = ..., total_ms: _Optional[float] = ..., chunks_retrieved: _Optional[int] = ..., chunks_compressed: _Optional[int] = ...) -> None: ...

class CacheInfo(_message.Message):
    __slots__ = ("embedding_cache_hit", "semantic_cache_hit", "chunk_cache_hit", "response_cache_hit", "semantic_similarity")
    EMBEDDING_CACHE_HIT_FIELD_NUMBER: _ClassVar[int]
    SEMANTIC_CACHE_HIT_FIELD_NUMBER: _ClassVar[int]
    CHUNK_CACHE_HIT_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_CACHE_HIT_FIELD_NUMBER: _ClassVar[int]
    SEMANTIC_SIMILARITY_FIELD_NUMBER: _ClassVar[int]
    embedding_cache_hit: bool
    semantic_cache_hit: bool
    chunk_cache_hit: bool
    response_cache_hit: bool
    semantic_similarity: float
    def __init__(self, embedding_cache_hit: bool = ..., semantic_cache_hit: bool = ..., chunk_cache_hit: bool = ..., response_cache_hit: bool = ..., semantic_similarity: _Optional[float] = ...) -> None: ...

class GetHighlightedPdfRequest(_message.Message):
    __slots__ = ("document_url", "page", "bboxes")
    DOCUMENT_URL_FIELD_NUMBER: _ClassVar[int]
    PAGE_FIELD_NUMBER: _ClassVar[int]
    BBOXES_FIELD_NUMBER: _ClassVar[int]
    document_url: str
    page: int
    bboxes: _containers.RepeatedCompositeFieldContainer[BBox]
    def __init__(self, document_url: _Optional[str] = ..., page: _Optional[int] = ..., bboxes: _Optional[_Iterable[_Union[BBox, _Mapping]]] = ...) -> None: ...

class HighlightedPdfResponse(_message.Message):
    __slots__ = ("pdf_content", "content_type")
    PDF_CONTENT_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    pdf_content: bytes
    content_type: str
    def __init__(self, pdf_content: _Optional[bytes] = ..., content_type: _Optional[str] = ...) -> None: ...

class InvalidateDocumentRequest(_message.Message):
    __slots__ = ("document_id",)
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    def __init__(self, document_id: _Optional[str] = ...) -> None: ...

class InvalidateDocumentResponse(_message.Message):
    __slots__ = ("success", "chunks_deleted", "cache_entries_deleted")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_DELETED_FIELD_NUMBER: _ClassVar[int]
    CACHE_ENTRIES_DELETED_FIELD_NUMBER: _ClassVar[int]
    success: bool
    chunks_deleted: int
    cache_entries_deleted: int
    def __init__(self, success: bool = ..., chunks_deleted: _Optional[int] = ..., cache_entries_deleted: _Optional[int] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("status", "version", "components")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    COMPONENTS_FIELD_NUMBER: _ClassVar[int]
    status: ServiceStatus
    version: str
    components: _containers.RepeatedCompositeFieldContainer[ComponentHealth]
    def __init__(self, status: _Optional[_Union[ServiceStatus, str]] = ..., version: _Optional[str] = ..., components: _Optional[_Iterable[_Union[ComponentHealth, _Mapping]]] = ...) -> None: ...

class ComponentHealth(_message.Message):
    __slots__ = ("name", "healthy", "message")
    NAME_FIELD_NUMBER: _ClassVar[int]
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    name: str
    healthy: bool
    message: str
    def __init__(self, name: _Optional[str] = ..., healthy: bool = ..., message: _Optional[str] = ...) -> None: ...

class GenerateRequest(_message.Message):
    __slots__ = ("messages", "model_hint", "temperature", "max_tokens", "feature_tag", "response_schema_json", "response_schema_name")
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    MODEL_HINT_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    FEATURE_TAG_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_SCHEMA_JSON_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_SCHEMA_NAME_FIELD_NUMBER: _ClassVar[int]
    messages: _containers.RepeatedCompositeFieldContainer[GenerateMessage]
    model_hint: str
    temperature: float
    max_tokens: int
    feature_tag: str
    response_schema_json: str
    response_schema_name: str
    def __init__(self, messages: _Optional[_Iterable[_Union[GenerateMessage, _Mapping]]] = ..., model_hint: _Optional[str] = ..., temperature: _Optional[float] = ..., max_tokens: _Optional[int] = ..., feature_tag: _Optional[str] = ..., response_schema_json: _Optional[str] = ..., response_schema_name: _Optional[str] = ...) -> None: ...

class GenerateMessage(_message.Message):
    __slots__ = ("role", "content")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    role: str
    content: str
    def __init__(self, role: _Optional[str] = ..., content: _Optional[str] = ...) -> None: ...

class GenerateResponse(_message.Message):
    __slots__ = ("content", "model", "prompt_tokens", "completion_tokens")
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    def __init__(self, content: _Optional[str] = ..., model: _Optional[str] = ..., prompt_tokens: _Optional[int] = ..., completion_tokens: _Optional[int] = ...) -> None: ...
