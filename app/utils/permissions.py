"""
Permissions utility functions
"""

from typing import Optional

CRITICAL_ROLES = ["PI", "CRC"]  # Roles allowed to complete visits


def is_critical_trial_role(trial_role: Optional[str]) -> bool:
    if trial_role is None:
        return False
    return trial_role.upper() in CRITICAL_ROLES
