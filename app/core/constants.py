# core/constants.py
import re

# Password Policy Regex
# At least 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)

# Roles
ROLE_GUEST = "Guest"
ROLE_USER = "User"
ROLE_PREMIUM = "Premium User"
ROLE_ADMIN = "Admin"
ROLE_SUPER_ADMIN = "Super Admin"

# Common status
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
STATUS_LOCKED = "locked"
STATUS_PENDING = "pending"
