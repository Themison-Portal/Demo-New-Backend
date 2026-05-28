"""
Alembic environment configuration.
Reads DATABASE_URL from environment variables automatically.
"""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─────────────────────────────────────────
# Import all models
# Add new model imports here when you create new model files
# ─────────────────────────────────────────
from app.models.base import Base
from app.models.profiles import Profile
from app.models.members import Member
from app.models.organizations import Organization
from app.models.trials import Trial
from app.models.trial_members import TrialMember
from app.models.trial_members_pending import TrialMemberPending
from app.models.invitations import Invitation
from app.models.roles import Role
from app.models.patients import Patient
from app.models.patient_visits import PatientVisit
from app.models.patient_documents import PatientDocument
from app.models.trial_patients import TrialPatient
from app.models.tasks import Task
from app.models.chat_sessions import ChatSession
from app.models.chat_messages import ChatMessage
from app.models.chat_threads import ChatThread
from app.models.thread_participants import ThreadParticipant
from app.models.documents import Document
from app.models.chunks_docling import DocumentChunkDocling
from app.models.qa_repository import QARepositoryItem
from app.models.semantic_cache import SemanticCacheResponse
from app.models.saved_response import SavedResponse
from app.models.archive_folder import ArchiveFolder
from app.models.activity_types import ActivityType
from app.models.trial_activity_types import TrialActivityType
from app.models.visit_activities import VisitActivity
from app.models.visit_documents import VisitDocument
from app.models.chat_document_links import ChatDocumentLink
from app.models.themison_admins import ThemisonAdmin
from app.models.user import User
from app.models.enums import (
    OrganizationMemberType,
    DocumentTypeEnum,
    PatientDocumentTypeEnum,
    PermissionLevel,
    VisitStatusEnum,
    VisitTypeEnum,
    VisitDocumentTypeEnum,
)

# new collaboration hub models
from app.models.inbox_messages import InboxMessage
from app.models.direct_messages import DirectMessage
from app.models.collaboration_threads import (
    CollaborationThread,
    CollaborationThreadMessage,
)

target_metadata = Base.metadata


def get_url():
    url = os.getenv("DATABASE_URL", "")
    # Alembic needs sync driver — replace asyncpg with psycopg2
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
