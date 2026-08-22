"""ORM 模型汇总。"""
from app.models.announcement import Announcement, ProjectProfile
from app.models.data_source import CollectorTaskLog, DataSource
from app.models.intel import (
    AppealHotspot,
    CompetitorTrack,
    LegacyProject,
    SalesLead,
    StrategicCustomer,
    UpdateOpportunity,
)
from app.models.knowledge import PolicyInfo, ProductKnowledge
from app.models.office import Office
from app.models.opportunity import (
    CompetitorRecord,
    FollowUpLog,
    Opportunity,
    PushRecord,
)
from app.models.sys import (
    AuditLog,
    SysConfig,
    SysPermission,
    SysRole,
    SysRolePermission,
    SysUser,
    SysUserRole,
)

__all__ = [
    "Announcement",
    "ProjectProfile",
    "DataSource",
    "CollectorTaskLog",
    "LegacyProject",
    "UpdateOpportunity",
    "StrategicCustomer",
    "SalesLead",
    "CompetitorTrack",
    "AppealHotspot",
    "ProductKnowledge",
    "PolicyInfo",
    "Office",
    "Opportunity",
    "FollowUpLog",
    "PushRecord",
    "CompetitorRecord",
    "SysUser",
    "SysRole",
    "SysPermission",
    "SysUserRole",
    "SysRolePermission",
    "SysConfig",
    "AuditLog",
]
