from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "manager")
        )


class IsManagerOrAdmin(IsManager):
    pass


class IsCashier(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
