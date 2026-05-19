"""
This module contains the contracts for the application.
"""

from .base import BaseContract, TimestampedContract
from .chat import (
    ChatMessageBase,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionBase,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from .document import DocumentBase, DocumentCreate, DocumentResponse, DocumentUpdate
from .query import QueryBase, QueryCreate, QueryResponse

# New contracts
from .organization import OrganizationResponse, OrganizationUpdate, OrganizationMetrics
from .member import MemberResponse, MemberUpdate, MemberTrialAssignment
from .role import RoleResponse, RoleCreate
from .invitation import (
    InvitationResponse,
    InvitationBatchCreate,
    InvitationBatchItem,
    InvitationCountResponse,
)
from .trial import (
    TrialResponse,
    TrialCreate,
    TrialUpdate,
    TrialWithAssignmentsCreate,
    TrialMemberAssignment,
    TrialPendingMemberAssignment,
)
from .trial_member import (
    TrialMemberResponse,
    TrialMemberCreate,
    PendingMemberResponse,
    PendingMemberCreate,
)
from .patient import PatientResponse, PatientCreate, PatientUpdate
from .trial_patient import TrialPatientResponse, TrialPatientCreate, TrialPatientUpdate
from .patient_visit import PatientVisitResponse, PatientVisitCreate
from .patient_document import PatientDocumentResponse, PatientDocumentCreate, PatientDocumentUpdate
from .qa_repository import QAItemResponse, QAItemCreate, QAItemUpdate
from .storage import UploadResponse, DownloadUrlResponse
