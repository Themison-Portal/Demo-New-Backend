"""
Contracts for patients.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import field_validator

from .base import BaseContract, TimestampedContract


VALID_GENDERS = {"male", "female", "other", "prefer_not_to_say"}
VALID_BLOOD_TYPES = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "unknown"}


class PatientBase(BaseContract):
    patient_code: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "United States"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    height_cm: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    blood_type: Optional[str] = None
    medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    known_allergies: Optional[str] = None
    primary_physician_name: Optional[str] = None
    primary_physician_phone: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    consent_signed: Optional[bool] = False
    consent_date: Optional[date] = None
    screening_notes: Optional[str] = None
    is_active: Optional[bool] = True

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_GENDERS:
            raise ValueError(f"gender must be one of {VALID_GENDERS}")
        return v

    @field_validator("blood_type")
    @classmethod
    def validate_blood_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_BLOOD_TYPES:
            raise ValueError(f"blood_type must be one of {VALID_BLOOD_TYPES}")
        return v


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseContract):
    patient_code: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    height_cm: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    blood_type: Optional[str] = None
    medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    known_allergies: Optional[str] = None
    primary_physician_name: Optional[str] = None
    primary_physician_phone: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    consent_signed: Optional[bool] = None
    consent_date: Optional[date] = None
    screening_notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_GENDERS:
            raise ValueError(f"gender must be one of {VALID_GENDERS}")
        return v

    @field_validator("blood_type")
    @classmethod
    def validate_blood_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_BLOOD_TYPES:
            raise ValueError(f"blood_type must be one of {VALID_BLOOD_TYPES}")
        return v


class PatientResponse(PatientBase, TimestampedContract):
    id: UUID
    organization_id: UUID
