"""
Contracts for trial-patient enrollment.
"""

from datetime import date, datetime
from typing import Any, Dict, Optional
from uuid import UUID

from .base import BaseContract, TimestampedContract


class TrialPatientBase(BaseContract):
    trial_id: UUID
    patient_id: UUID
    enrollment_date: Optional[date] = None
    status: Optional[str] = "enrolled"
    randomization_code: Optional[str] = None
    notes: Optional[str] = None
    cost_data: Optional[Dict[str, Any]] = None
    patient_data: Optional[Dict[str, Any]] = None


class TrialPatientCreate(TrialPatientBase):
    pass


class TrialPatientUpdate(BaseContract):
    status: Optional[str] = None
    randomization_code: Optional[str] = None
    notes: Optional[str] = None
    cost_data: Optional[Dict[str, Any]] = None
    patient_data: Optional[Dict[str, Any]] = None


class TrialPatientResponse(TrialPatientBase, TimestampedContract):
    id: UUID
    assigned_by: Optional[UUID] = None
    # Joined patient fields
    patient_code: Optional[str] = None
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
