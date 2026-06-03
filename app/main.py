"""
Main application file
"""

import os
import sys
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from redis.asyncio import Redis

# Load environment variables
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Auth routes
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
from app.api.routes.api.task_dependencies import router as task_dependencies_router
from app.api.routes.api.activities import router as trial_activities_router
from app.api.routes.api.complete_visit import router as complete_visit_router
from app.api.routes.api.visit_activities import router as visit_activities_router

# New Collaboration Hub routes
from app.api.routes.api.inbox import router as inbox_router
from app.api.routes.api.direct_messages import router as direct_messages_router
from app.api.routes.api.collaboration_threads import (
    router as collaboration_threads_router,
)


# ─────────────────────────────────────────
# Lifespan — Redis only, no self-healing
# DB migrations handled by Alembic
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = None
    try:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            redis_client = Redis.from_url(redis_url, decode_responses=False)
            await redis_client.ping()
            app.state.redis_client = redis_client
            logging.info("Redis connection successful.")
        else:
            app.state.redis_client = None
            logging.warning("REDIS_URL not set, skipping Redis initialization.")
    except Exception as e:
        logging.error(f"Redis connection failed: {e}")
        app.state.redis_client = None

    yield

    if redis_client:
        try:
            await redis_client.close()
            logging.info("Redis connection closed.")
        except Exception as e:
            logging.error(f"Error closing Redis connection: {e}")


app = FastAPI(lifespan=lifespan)

# Trust proxy headers from load balancer
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# ─────────────────────────────────────────
# CORS Configuration
# ─────────────────────────────────────────
frontend_url_env = os.getenv("FRONTEND_URL", "")
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in frontend_url_env.split(",")
    if origin.strip()
]

# Default development origins
dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
for origin in dev_origins:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

# Regex for themison domains
themison_regex = r"https?://([a-z0-9-]+\.)?themison\.(app|com|io|org|run\.app)"

allow_all = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"

if allow_all:
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
                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-API-KEY, X-Job-ID, X-Document-ID"
                )
                response.headers["Access-Control-Expose-Headers"] = (
                    "Content-Length, X-Job-ID, X-Document-ID"
                )
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
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
            "X-API-KEY",
            "X-Job-ID",
            "X-Document-ID",
        ],
        expose_headers=["Content-Length", "X-Job-ID", "X-Document-ID"],
        max_age=600,
    )
    logging.info("CORS initialized.")


# ─────────────────────────────────────────
# Health endpoints
# ─────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "version": "1.0.0", "message": "Themison New Platform API"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "new-platform-backend",
        "version": "1.0.0",
    }


# ─────────────────────────────────────────
# Routers
# ─────────────────────────────────────────

# Auth
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Upload & Query
app.include_router(upload_router, prefix="/upload", tags=["upload"])
app.include_router(query_router, prefix="/query", tags=["query"])

# Storage
app.include_router(storage_router, prefix="/storage", tags=["storage"])
app.include_router(local_files_router, prefix="/local-files", tags=["local-files"])

# Business API
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
    task_dependencies_router, prefix="/api/task-dependencies", tags=["task-dependencies"]
)
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
app.include_router(archive_router, prefix="/api/archive", tags=["archive"])

# Collaboration Hub
app.include_router(inbox_router, prefix="/api/inbox", tags=["inbox"])
app.include_router(
    direct_messages_router, prefix="/api/direct-messages", tags=["direct-messages"]
)
app.include_router(
    collaboration_threads_router,
    prefix="/api/collaboration-threads",
    tags=["collaboration-threads"],
)
