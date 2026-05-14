from rest_framework import generics, status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view

from config.permissions import IsAdmin, IsManagerOrAdmin
from .models import AuditLog
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserListSerializer,
    UserDetailSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    AuditLogSerializer,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(summary="Obtain JWT access + refresh tokens")
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            _log_action(request, "login", user_email=request.data.get("email"))
        return response


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(summary="Blacklist refresh token (logout)")
    def post(self, request):
        try:
            token = RefreshToken(request.data["refresh"])
            token.blacklist()
        except Exception:
            pass
        _log_action(request, "logout")
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List users"),
    create=extend_schema(summary="Create user"),
    retrieve=extend_schema(summary="Retrieve user"),
    update=extend_schema(summary="Update user"),
    partial_update=extend_schema(summary="Partial update user"),
    destroy=extend_schema(summary="Delete user"),
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("store").all()
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filterset_fields = ["role", "is_active", "store"]
    search_fields = ["email", "username", "first_name", "last_name", "phone"]
    ordering_fields = ["date_joined", "email", "role"]

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserDetailSerializer

    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def me(self, request):
        if request.method == "PATCH":
            serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(UserDetailSerializer(request.user).data)
        return Response(UserDetailSerializer(request.user).data)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed successfully."})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filterset_fields = ["action", "model_name", "user"]
    search_fields = ["description", "user__email"]
    ordering_fields = ["timestamp"]


def _log_action(request, action, user_email=None):
    user = request.user if request.user.is_authenticated else None
    AuditLog.objects.create(
        user=user,
        action=action,
        description=f"{action.capitalize()} by {user_email or getattr(user, 'email', 'anonymous')}",
        ip_address=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )


def _get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded.split(",")[0].strip() if x_forwarded else request.META.get("REMOTE_ADDR")
