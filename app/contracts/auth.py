"""
Contracts for authentication and signup.
"""
from typing import Optional
from .base import BaseContract

class SignupCompleteRequest(BaseContract):
    token: str
    password: str
    # Optional fields to override invitation data
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class SignupCompleteResponse(BaseContract):
    success: bool
    message: str
    user_id: str # Profile ID
