# imports/permissions.py
ALLOWED_ROLES = {"logistic"}

STATUS_CHOICES = ["PLANNED", "PICKED_UP", "IN_TRANSIT", "AT_CUSTOMS", "DELIVERED", "CANCELLED"]
METHOD_CHOICES = ["AIR", "SEA", "ROAD", "COURIER", "OTHER"]


def has_imports_access(user):
    if user.is_superuser:
        return True
    return getattr(user, "role", None) in ALLOWED_ROLES