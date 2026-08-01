from app.database.base import Base
from app.models.user import User
from app.models.role import Role, Permission, UserRole, RolePermission
from app.models.session import Session
from app.models.device import Device
from app.models.audit import AuditLog
from app.models.otp import OTPCode
from app.models.profile import UserProfile

# This file is used by Alembic to import all models and discover metadata.
from app.models.master import *
