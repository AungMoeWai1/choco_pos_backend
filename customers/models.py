from django.db import models
from django.core.validators import MinValueValidator


class Customer(models.Model):
    full_name = models.CharField(max_length=200, db_index=True)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    address = models.TextField(blank=True)
    loyalty_points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customer"
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def total_purchases(self):
        return self.orders.filter(payment_status="paid").count()

    @property
    def total_spent(self):
        from django.db.models import Sum
        return self.orders.filter(payment_status="paid").aggregate(
            total=Sum("grand_total")
        )["total"] or 0


class LoyaltyTransaction(models.Model):
    class TransactionType(models.TextChoices):
        EARN = "earn", "Earn"
        REDEEM = "redeem", "Redeem"
        ADJUST = "adjust", "Adjust"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="loyalty_transactions")
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    points = models.IntegerField()
    balance_after = models.IntegerField()
    reference = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = "loyalty_transaction"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer} – {self.transaction_type} {self.points} pts"
