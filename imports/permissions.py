# imports/permissions.py

STATUS_CHOICES = ["PLANNED", "PICKED_UP", "IN_TRANSIT", "AT_CUSTOMS", "DELIVERED", "CANCELLED"]
METHOD_CHOICES = ["AIR", "SEA", "ROAD", "COURIER", "OTHER"]


def has_imports_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return str(getattr(user, "role", "")).strip().lower() in ({"logistic"})