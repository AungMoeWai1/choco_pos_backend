from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from config.permissions import IsAdmin, IsManagerOrAdmin
from .models import Store, Terminal, Shift
from .serializers import StoreSerializer, TerminalSerializer, ShiftSerializer, ShiftCloseSerializer


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [IsAuthenticated(), IsAdmin()]
        return super().get_permissions()


class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.select_related("store").all()
    serializer_class = TerminalSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filterset_fields = ["store", "is_active"]


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.select_related("terminal", "cashier").all()
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "terminal", "cashier"]
    ordering_fields = ["opened_at", "closed_at"]

    def perform_create(self, serializer):
        serializer.save(cashier=self.request.user)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        shift = self.get_object()
        if shift.status == Shift.Status.CLOSED:
            return Response({"detail": "Shift already closed."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ShiftCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift.closing_cash = serializer.validated_data["closing_cash"]
        shift.notes = serializer.validated_data.get("notes", "")
        shift.status = Shift.Status.CLOSED
        shift.closed_at = timezone.now()
        shift.save()
        return Response(ShiftSerializer(shift).data)

    @action(detail=False, methods=["get"])
    def current(self, request):
        shift = (
            Shift.objects.filter(cashier=request.user, status=Shift.Status.OPEN)
            .select_related("terminal")
            .first()
        )
        if not shift:
            return Response({"detail": "No open shift."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShiftSerializer(shift).data)
