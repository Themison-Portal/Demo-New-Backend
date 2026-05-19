"""
Main application file
"""

import os
import sys
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.query import router as query_router
from app.api.routes.upload import router as upload_router

# Storage routes
from app.api.routes.storage.storage import router as storage_router
from app.api.routes.local_files import router as local_files_router

# Business API routes
from app.api.routes.api.organizations import router as organizations_router
from app.api.routes.api.members import router as members_router
from app.api.routes.api.roles import router as roles_router
from app.api.routes.api.invitations import router as invitations_router
from app.api.routes.api.trials import router as trials_router
from app.api.routes.api.trial_members import router as trial_members_router
from app.api.routes.api.trial_documents import router as trial_documents_router
from app.api.routes.api.patients import router as patients_router
from app.api.routes.api.trial_patients import router as trial_patients_router
from app.api.routes.api.patient_visits import router as patient_visits_router
from app.api.routes.api.patient_documents import router as patient_documents_router
from app.api.routes.api.chat_sessions import router as chat_sessions_router
from app.api.routes.api.chat_messages import router as chat_messages_router
from app.api.routes.api.qa_repository import router as qa_repository_router
from app.api.routes.api.archive import router as archive_router

from app.api.routes.api.tasks import router as tasks_router
from app.api.routes.api.activities import router as trial_activities_router
from app.api.routes.api.complete_visit import router as complete_visit_router
from app.api.routes.api.visit_activities import router as visit_activities_router

from contextlib import asynccontextmanager
from redis.asyncio import Redis
import logging

# Load environment variables from .env file
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Application state for storing loaded models
app_state = {}


# --- Lifespan handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = None

    try:
        logging.info("Initializing Redis…")

        # --- 1) Connect to Redis ---
        try:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                redis_client = Redis.from_url(redis_url, decode_responses=False)
                await redis_client.ping()
                app.state.redis_client = redis_client
                logging.info("Redis connection successful.")
            else:
                logging.warning("REDIS_URL not set, skipping Redis initialization.")
                app.state.redis_client = None
        except Exception as e:
            logging.error(f"Redis connection failed: {e}")
            app.state.redis_client = None

        # --- 2) Self-Healing: Run missing migrations ---
        try:
            from sqlalchemy import text
            from app.db.session import engine
            
            async with engine.connect() as conn:
                # Helper to check if column exists
                async def column_exists(table, column):
                    # Check in public schema explicitly to be safe
                    res = await conn.execute(text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = :t AND column_name = :c"
                    ), {"t": table, "c": column})
                    return res.scalar() is not None

                # Ensure uuid-ossp extension exists for UUID generation
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
                    await conn.commit()
                except Exception as e:
                    logging.warning(f"Could not create uuid-ossp extension: {e}")

                # Ensure themison_admins table exists for JIT provisioning
                try:
                    await conn.execute(text(
                        "CREATE TABLE IF NOT EXISTS themison_admins ("
                        "id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),"
                        "email TEXT NOT NULL UNIQUE,"
                        "name TEXT,"
                        "active BOOLEAN DEFAULT TRUE,"
                        "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,"
                        "created_by UUID"
                        ");"
                    ))
                    await conn.commit()
                except Exception as e:
                    logging.warning(f"Could not ensure themison_admins table: {e}")

                # Ensure organization_member_type ENUM exists
                try:
                    await conn.execute(text("SELECT 'admin'::organization_member_type;"))
                except Exception:
                    logging.info("Creating ENUM organization_member_type...")
                    await conn.execute(text("CREATE TYPE organization_member_type AS ENUM ('admin', 'staff');"))
                    await conn.commit()

                # Profiles
                if not await column_exists('profiles', 'is_active'):
                    logging.info("Adding profiles.is_active...")
                    await conn.execute(text("ALTER TABLE profiles ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"))
                    await conn.commit()

                # Members
                if not await column_exists('members', 'is_active'):
                    logging.info("Adding members.is_active...")
                    await conn.execute(text("ALTER TABLE members ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"))
                    await conn.commit()

                # Invitations
                if not await column_exists('invitations', 'token'):
                    logging.info("Adding and populating invitations.token...")
                    await conn.execute(text("ALTER TABLE invitations ADD COLUMN token TEXT;"))
                    # Populate NULL tokens with unique values
                    await conn.execute(text("UPDATE invitations SET token = MD5(random()::text) WHERE token IS NULL;"))
                    await conn.execute(text("ALTER TABLE invitations ALTER COLUMN token SET NOT NULL;"))
                    await conn.commit()
                
                if not await column_exists('invitations', 'status'):
                    logging.info("Adding invitations.status...")
                    await conn.execute(text("ALTER TABLE invitations ADD COLUMN status TEXT DEFAULT 'pending';"))
                    await conn.commit()
                
                if not await column_exists('invitations', 'invited_at'):
                    logging.info("Adding invitations.invited_at...")
                    await conn.execute(text("ALTER TABLE invitations ADD COLUMN invited_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
                    await conn.commit()

                if not await column_exists('invitations', 'expires_at'):
                    logging.info("Adding invitations.expires_at...")
                    await conn.execute(text("ALTER TABLE invitations ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;"))
                    await conn.commit()

                if not await column_exists('invitations', 'accepted_at'):
                    logging.info("Adding invitations.accepted_at...")
                    await conn.execute(text("ALTER TABLE invitations ADD COLUMN accepted_at TIMESTAMP WITH TIME ZONE;"))
                    await conn.commit()

                # Trials (New stability columns)
                if not await column_exists('trials', 'visit_schedule_template'):
                    logging.info("Adding trials.visit_schedule_template...")
                    await conn.execute(text("ALTER TABLE trials ADD COLUMN visit_schedule_template JSONB DEFAULT '{}';"))
                    await conn.commit()

                if not await column_exists('trials', 'budget_data'):
                    logging.info("Adding trials.budget_data...")
                    await conn.execute(text("ALTER TABLE trials ADD COLUMN budget_data JSONB DEFAULT '{}';"))
                    await conn.commit()

                # Patient Visits
                if not await column_exists('patient_visits', 'cost_data'):
                    logging.info("Adding patient_visits.cost_data...")
                    await conn.execute(text("ALTER TABLE patient_visits ADD COLUMN cost_data JSONB DEFAULT '{}';"))
                    await conn.commit()

                # Trial Members
                if not await column_exists('trial_members', 'settings'):
                    logging.info("Adding trial_members.settings...")
                    await conn.execute(text("ALTER TABLE trial_members ADD COLUMN settings JSONB DEFAULT '{}';"))
                    await conn.commit()

                # Self-healing: Check and update ENUM type if needed
                try:
                    # 1. Expand the ENUM with missing roles
                    for role in ["superadmin", "editor", "viewer", "reader"]:
                        try:
                            await conn.execute(text(f"ALTER TYPE organization_member_type ADD VALUE IF NOT EXISTS '{role}'"))
                            await conn.commit()
                        except Exception as e:
                            logging.warning(f"Failed to add role {role} (likely exists): {e}")

                    # 2. Hard-force make name nullable in invitations table
                    try:
                        await conn.execute(text("ALTER TABLE invitations ALTER COLUMN name DROP NOT NULL"))
                        await conn.commit()
                    except Exception as e:
                        logging.warning(f"Failed to force nullable name column: {e}")
                except Exception as e:
                    logging.error(f"Database self-healing failed: {e}")

                # Tasks
                if not await column_exists('tasks', 'category'):
                    logging.info("Adding tasks.category...")
                    await conn.execute(text("ALTER TABLE tasks ADD COLUMN category TEXT;"))
                    await conn.commit()

                # Trial Documents (RAG ingestion tracking)
                if not await column_exists('trial_documents', 'ingestion_status'):
                    logging.info("Adding trial_documents.ingestion_status...")
                    await conn.execute(text(
                        "ALTER TABLE trial_documents ADD COLUMN ingestion_status TEXT;"
                    ))
                    # Backfill: documents that already have chunks are 'ready'
                    await conn.execute(text(
                        "UPDATE trial_documents td "
                        "SET ingestion_status = 'ready' "
                        "WHERE EXISTS ("
                        "  SELECT 1 FROM document_chunks_docling dcd "
                        "  WHERE dcd.document_id = td.id"
                        ");"
                    ))
                    await conn.commit()

                # Chat Sessions (New columns and Foreign Key)
                if not await column_exists('chat_sessions', 'trial_id'):
                    logging.info("Adding chat_sessions.trial_id...")
                    await conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN trial_id UUID REFERENCES trials(id) ON DELETE SET NULL;"))
                    await conn.commit()

                if not await column_exists('chat_sessions', 'document_id'):
                    logging.info("Adding chat_sessions.document_id with correct FK...")
                    await conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN document_id UUID;"))
                    # Note: Table name is trial_documents, NOT documents
                    try:
                        await conn.execute(text("ALTER TABLE chat_sessions ADD CONSTRAINT fk_chat_sessions_document FOREIGN KEY (document_id) REFERENCES trial_documents(id) ON DELETE SET NULL;"))
                    except Exception as e:
                        logging.warning(f"Could not add FK to document_id (likely exists or table mapping error): {e}")
                    await conn.commit()

                if not await column_exists('chat_sessions', 'document_name'):
                    logging.info("Adding chat_sessions.document_name...")
                    await conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN document_name TEXT;"))
                    await conn.commit()

            logging.info("Self-healing: Migration check completed.")
        except Exception as e:
            logging.error(f"Self-healing migrations failed: {e}")

        yield

    finally:
        # --- 3) Shutdown cleanup ---
        if redis_client:
            try:
                await redis_client.close()
                logging.info("Redis connection closed.")
            except Exception as e:
                logging.error(f"Error closing Redis connection: {e}")


app = FastAPI(lifespan=lifespan)
# app = FastAPI()

# Trust proxy headers (X-Forwarded-For, X-Forwarded-Proto) from Cloud Run load balancer
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Configure CORS Origins
frontend_url_env = os.getenv("FRONTEND_URL", "")
allowed_origins = [origin.strip().rstrip("/") for origin in frontend_url_env.split(",") if origin.strip()]

# Add default development origins
dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "https://themison-frontend-eu-768873408671.europe-west1.run.app"]
for origin in dev_origins:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

# Define regex for custom themison domains (supports any subdomain)
themison_regex = r"https?://([a-z0-9-]+\.)?themison\.(app|com|io|org|run\.app)"

allow_all = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"

if allow_all:
    # Custom Middleware to mirror Origin header for CORS
    # This allows credentials with ANY origin, which is what ALLOW_ALL_ORIGINS implies
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response

    class DynamicCORSMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if request.method == "OPTIONS":
                response = Response()
            else:
                response = await call_next(request)
            
            origin = request.headers.get("Origin")
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-API-KEY, X-Job-ID, X-Document-ID"
                response.headers["Access-Control-Expose-Headers"] = "Content-Length, X-Job-ID, X-Document-ID"
            
            return response

    app.add_middleware(DynamicCORSMiddleware)
    logging.info("Dynamic CORS initialized (Allow All Origins enabled).")
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=themison_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-API-KEY", "X-Job-ID", "X-Document-ID"],
        expose_headers=["Content-Length", "X-Job-ID", "X-Document-ID"],
        max_age=600,
    )
    logging.info(f"CORS initialized with allowed origins and dynamic regex for Themison domains.")



@app.get("/")
def root():
    return {"status": "ok", "version": "4.1.1-AUTH-CORS-FIX", "message": "Themison Backend API"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "core-backend-eu",
        "version": "1.1.0",
    }


@app.get("/debug-config")
async def debug_config():
    """Comprehensive diagnostic endpoint for env vars, connection health, and DB stats."""
    from sqlalchemy import text, select, func
    from app.db.session import engine
    from app.dependencies.db import get_db
    from app.models.profiles import Profile
    from app.models.members import Member
    from app.models.organizations import Organization
    
    # 1. Check ENUM roles in DB
    enum_labels = []
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname = 'organization_member_type'"))
            enum_labels = [row[0] for row in result.all()]
    except Exception as e:
        enum_labels = [f"Error: {e}"]

    # 2. Check DB Stats (Counts)
    p_count, m_count, o_count = -1, -1, -1
    try:
        db_gen = get_db()
        db = await db_gen.__anext__()
        p_count = (await db.execute(select(func.count()).select_from(Profile))).scalar()
        m_count = (await db.execute(select(func.count()).select_from(Member))).scalar()
        o_count = (await db.execute(select(func.count()).select_from(Organization))).scalar()
    except Exception as e:
        logging.error(f"Debug stats failed: {e}")

    return {
        "status": "online",
        "environment": {
            "FRONTEND_URL": os.getenv("FRONTEND_URL"),
            "AUTH0_DOMAIN": os.getenv("AUTH0_DOMAIN"),
            "RAG_ADDRESS": os.getenv("RAG_SERVICE_ADDRESS"),
            "SENDGRID_CONFIGURED": bool(os.getenv("SENDGRID_API_KEY"))
        },
        "database": {
            "ROLES_IN_SCHEMA": enum_labels,
            "STATS": {
                "profiles": p_count,
                "members": m_count,
                "organizations": o_count
            }
        },
        "config_details": {
            "VERSION": "4.0.3-GCS-CORS-FIX",
            "USE_GRPC": os.getenv("USE_GRPC_RAG", "false").lower() == "true",
            "ALLOW_ALL_ORIGINS": os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"
        }
    }


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(archive_router, prefix="/api/archive", tags=["archive"])

app.include_router(
    upload_router,
    prefix="/upload",
    tags=["upload"],
)

app.include_router(
    query_router,
    prefix="/query",
    tags=["query"],
)

# --- Storage routes ---
app.include_router(storage_router, prefix="/storage", tags=["storage"])
app.include_router(local_files_router, prefix="/local-files", tags=["local-files"])

# --- Business API routes ---
app.include_router(
    organizations_router, prefix="/api/organizations", tags=["organizations"]
)
app.include_router(members_router, prefix="/api/members", tags=["members"])
app.include_router(roles_router, prefix="/api/roles", tags=["roles"])
app.include_router(invitations_router, prefix="/api/invitations", tags=["invitations"])
app.include_router(trials_router, prefix="/api/trials", tags=["trials"])
app.include_router(
    trial_members_router, prefix="/api/trial-members", tags=["trial-members"]
)

app.include_router(
    trial_activities_router,
    prefix="/api/trials/{trial_id}/activities",
    tags=["trial-activities"],
)
app.include_router(
    trial_documents_router, prefix="/api/trial-documents", tags=["trial-documents"]
)
app.include_router(patients_router, prefix="/api/patients", tags=["patients"])
app.include_router(
    trial_patients_router, prefix="/api/trial-patients", tags=["trial-patients"]
)
app.include_router(
    patient_visits_router, prefix="/api/patient-visits", tags=["patient-visits"]
)

app.include_router(
    complete_visit_router, prefix="/api/patient-visits", tags=["patient-visits"]
)
app.include_router(
    visit_activities_router, prefix="/api/patient-visits", tags=["patient-visits"]
)
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(
    patient_documents_router,
    prefix="/api/patient-documents",
    tags=["patient-documents"],
)
app.include_router(
    chat_sessions_router, prefix="/api/chat-sessions", tags=["chat-sessions"]
)
app.include_router(
    chat_messages_router, prefix="/api/chat-messages", tags=["chat-messages"]
)
app.include_router(
    qa_repository_router, prefix="/api/qa-repository", tags=["qa-repository"]
)
