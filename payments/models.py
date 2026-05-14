from django.db import models
from django.core.validators import MinValueValidator


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        KBZPAY = "kbzpay", "KBZPay"
        WAVEPAY = "wavepay", "WavePay"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIAL_REFUND = "partial_refund", "Partial Refund"

    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="payments"
    )
    payment_method = models.CharField(max_length=20, choices=Method.choices, db_index=True)
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transaction_id = models.CharField(max_length=200, blank=True, db_index=True)
    reference_number = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = "payment"
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["payment_method", "payment_date"]),
        ]

    def __str__(self):
        return f"Payment {self.pk} – {self.payment_method} – {self.paid_amount}"


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    reason = models.TextField()
    transaction_id = models.CharField(max_length=200, blank=True)
    processed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "refund"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.pk} – {self.amount}"
