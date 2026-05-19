from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class VisitTemplateVisit(BaseModel):
    order: int
    name: str
    is_day_zero: bool = False
    activity_ids: List[str] = []


class VisitScheduleTemplate(BaseModel):
    visits: List[VisitTemplateVisit] = Field(default_factory=list)
    assignees: Dict[str, List[str]] = Field(default_factory=dict)
