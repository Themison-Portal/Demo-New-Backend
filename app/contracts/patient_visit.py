"""
Contracts for patient visits.
"""

from datetime import date, datetime, time
from typing import Any, Dict, Optional
from uuid import UUID

from .base import BaseContract, TimestampedContract


class PatientVisitBase(BaseContract):
    patient_id: UUID
    trial_id: UUID
    doctor_id: UUID
    visit_date: date
    visit_time: Optional[time] = None
    visit_type: str = "follow_up"
    status: str = "scheduled"
    duration_minutes: Optional[int] = None
    visit_number: Optional[int] = None
    notes: Optional[str] = None
    next_visit_date: Optional[date] = None
    location: Optional[str] = None
    actual_date: Optional[date] = None
    cost_data: Optional[Dict[str, Any]] = None


class PatientVisitCreate(PatientVisitBase):
    pass


class PatientVisitResponse(PatientVisitBase, TimestampedContract):
    id: UUID
    created_by: Optional[UUID] = None
    # Joined fields
    doctor_name: Optional[str] = None
