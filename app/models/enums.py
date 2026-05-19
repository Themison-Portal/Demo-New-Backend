"""
Enum definitions matching PostgreSQL custom types in schema.sql.
Uses (str, Enum) pattern so values serialize correctly in Pydantic.
"""

from enum import Enum


class OrganizationMemberType(str, Enum):
    admin = "admin"
    staff = "staff"


class DocumentTypeEnum(str, Enum):
    protocol = "protocol"
    brochure = "brochure"
    consent_form = "consent_form"
    report = "report"
    manual = "manual"
    plan = "plan"
    amendment = "amendment"
    icf = "icf"
    case_report_form = "case_report_form"
    standard_operating_procedure = "standard_operating_procedure"
    other = "other"


class PatientDocumentTypeEnum(str, Enum):
    medical_record = "medical_record"
    lab_result = "lab_result"
    imaging = "imaging"
    consent_form = "consent_form"
    assessment = "assessment"
    questionnaire = "questionnaire"
    adverse_event_report = "adverse_event_report"
    medication_record = "medication_record"
    visit_note = "visit_note"
    discharge_summary = "discharge_summary"
    other = "other"


class PermissionLevel(str, Enum):
    read = "read"
    edit = "edit"
    admin = "admin"


class VisitStatusEnum(str, Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"
    rescheduled = "rescheduled"


class VisitTypeEnum(str, Enum):
    screening = "screening"
    baseline = "baseline"
    follow_up = "follow_up"
    treatment = "treatment"
    assessment = "assessment"
    monitoring = "monitoring"
    adverse_event = "adverse_event"
    unscheduled = "unscheduled"
    study_closeout = "study_closeout"
    withdrawal = "withdrawal"


class VisitDocumentTypeEnum(str, Enum):
    visit_note = "visit_note"
    lab_results = "lab_results"
    blood_test = "blood_test"
    vital_signs = "vital_signs"
    invoice = "invoice"
    billing_statement = "billing_statement"
    medication_log = "medication_log"
    adverse_event_form = "adverse_event_form"
    assessment_form = "assessment_form"
    imaging_report = "imaging_report"
    procedure_note = "procedure_note"
    data_export = "data_export"
    consent_form = "consent_form"
    insurance_document = "insurance_document"
    other = "other"
