from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOperator(BasePermission):
    """Grants access only to staff/instructor/admin accounts. Used to gate
    the Solution endpoint and lab-authoring mutations — this is checked
    server-side; it is never enforced only by hiding a button in the UI.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_operator)


class IsAdminOperatorOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_operator)
