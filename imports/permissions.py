# imports/permissions.py
ALLOWED_ROLES = {"logistics", "procurement", "Other Employee"}

STATUS_CHOICES = ["PLANNED", "PICKED_UP", "IN_TRANSIT", "AT_CUSTOMS", "DELIVERED", "CANCELLED"]
METHOD_CHOICES = ["AIR", "SEA", "ROAD", "COURIER", "OTHER"]


def has_imports_access(user):
    if getattr(user, "is_superuser", False):
        return True
    role = getattr(user, "role", None)
    return role in ALLOWED_ROLES
