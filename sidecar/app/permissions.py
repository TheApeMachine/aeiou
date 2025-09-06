from __future__ import annotations

import time
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass


class PermissionLevel(Enum):
    DENY = "deny"
    ASK = "ask"
    ALLOW = "allow"


@dataclass
class ToolPermission:
    """Permission settings for a specific tool"""
    tool_name: str
    permission: PermissionLevel
    risk_level: str = "low"
    description: str = ""
    last_used: Optional[float] = None
    use_count: int = 0


@dataclass
class SessionElevation:
    """Temporary permission elevation for a session"""
    session_id: str
    elevated_tools: List[str]
    granted_by: str
    granted_at: float
    expires_at: float
    reason: str


class PermissionManager:
    """Manages tool permissions and session elevations"""

    def __init__(self):
        self.tool_permissions: Dict[str, ToolPermission] = {}
        self.session_elevations: Dict[str, SessionElevation] = {}
        self._load_default_permissions()

    def _load_default_permissions(self):
        """Load default tool permissions"""
        default_permissions = [
            ToolPermission(
                tool_name="file_read",
                permission=PermissionLevel.ALLOW,
                risk_level="low",
                description="Read file contents"
            ),
            ToolPermission(
                tool_name="file_write",
                permission=PermissionLevel.ASK,
                risk_level="medium",
                description="Modify file contents"
            ),
            ToolPermission(
                tool_name="file_delete",
                permission=PermissionLevel.DENY,
                risk_level="high",
                description="Delete files"
            ),
            ToolPermission(
                tool_name="run_command",
                permission=PermissionLevel.ASK,
                risk_level="high",
                description="Execute system commands"
            ),
            ToolPermission(
                tool_name="network_request",
                permission=PermissionLevel.ALLOW,
                risk_level="low",
                description="Make network requests"
            ),
            ToolPermission(
                tool_name="code_generation",
                permission=PermissionLevel.ALLOW,
                risk_level="medium",
                description="Generate code using AI"
            ),
            ToolPermission(
                tool_name="refactor_code",
                permission=PermissionLevel.ASK,
                risk_level="medium",
                description="Refactor existing code"
            ),
            ToolPermission(
                tool_name="run_tests",
                permission=PermissionLevel.ALLOW,
                risk_level="low",
                description="Execute test suites"
            )
        ]

        for perm in default_permissions:
            self.tool_permissions[perm.tool_name] = perm

    def check_permission(self, tool_name: str, session_id: Optional[str] = None) -> PermissionLevel:
        """Check permission for a tool, considering session elevations"""
        base_permission = self.tool_permissions.get(tool_name, ToolPermission(
            tool_name=tool_name,
            permission=PermissionLevel.ASK,
            risk_level="medium"
        ))

        # Check for session elevation
        if session_id and session_id in self.session_elevations:
            elevation = self.session_elevations[session_id]
            if time.time() < elevation.expires_at and tool_name in elevation.elevated_tools:
                return PermissionLevel.ALLOW

        return base_permission.permission

    def request_permission(self, tool_name: str, reason: str, session_id: str) -> Dict[str, Any]:
        """Request permission for a tool that requires approval"""
        permission = self.check_permission(tool_name, session_id)

        if permission == PermissionLevel.ALLOW:
            self._record_tool_usage(tool_name)
            return {"granted": True, "reason": "Auto-approved"}

        if permission == PermissionLevel.DENY:
            return {"granted": False, "reason": "Permission denied by policy"}

        # ASK permission - requires user approval
        tool_perm = self.tool_permissions.get(tool_name)
        risk_level = tool_perm.risk_level if tool_perm else "medium"

        return {
            "granted": False,
            "requires_approval": True,
            "tool_name": tool_name,
            "reason": reason,
            "risk_level": risk_level,
            "description": tool_perm.description if tool_perm else ""
        }

    def grant_elevation(self, session_id: str, tools: List[str], duration_minutes: int = 30,
                       reason: str = "", granted_by: str = "system") -> SessionElevation:
        """Grant temporary elevation for specific tools"""
        elevation = SessionElevation(
            session_id=session_id,
            elevated_tools=tools,
            granted_by=granted_by,
            granted_at=time.time(),
            expires_at=time.time() + (duration_minutes * 60),
            reason=reason
        )

        self.session_elevations[session_id] = elevation
        return elevation

    def revoke_elevation(self, session_id: str):
        """Revoke session elevation"""
        if session_id in self.session_elevations:
            del self.session_elevations[session_id]

    def set_tool_permission(self, tool_name: str, permission: PermissionLevel,
                           risk_level: str = "medium", description: str = ""):
        """Set permission for a specific tool"""
        self.tool_permissions[tool_name] = ToolPermission(
            tool_name=tool_name,
            permission=permission,
            risk_level=risk_level,
            description=description
        )

    def _record_tool_usage(self, tool_name: str):
        """Record tool usage for analytics"""
        if tool_name in self.tool_permissions:
            perm = self.tool_permissions[tool_name]
            perm.last_used = time.time()
            perm.use_count += 1

    def get_permission_stats(self) -> Dict[str, Any]:
        """Get permission and usage statistics"""
        stats = {
            "tools": {},
            "elevations": len(self.session_elevations),
            "total_requests": 0
        }

        for tool_name, perm in self.tool_permissions.items():
            stats["tools"][tool_name] = {
                "permission": perm.permission.value,
                "risk_level": perm.risk_level,
                "use_count": perm.use_count,
                "last_used": perm.last_used
            }
            stats["total_requests"] += perm.use_count

        return stats

    def cleanup_expired_elevations(self):
        """Remove expired session elevations"""
        current_time = time.time()
        expired_sessions = []

        for session_id, elevation in self.session_elevations.items():
            if current_time >= elevation.expires_at:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.session_elevations[session_id]

        return len(expired_sessions)

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get list of tools waiting for approval (for UI display)"""
        # In a real implementation, this would track pending approval requests
        return []


# Global permission manager instance
permission_manager = PermissionManager()