import uuid
from django.db import models
from django.core.validators import MinValueValidator


def generate_order_number():
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


class Order(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PARTIAL = "partial", "Partial"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"

    class OrderStatus(models.TextChoices):
        OPEN = "open", "Open"
        SUSPENDED = "suspended", "Suspended"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        RETURNED = "returned", "Returned"

    order_number = models.CharField(max_length=20, unique=True, default=generate_order_number, db_index=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    cashier = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
    )
    shift = models.ForeignKey(
        "store_settings.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    store = models.ForeignKey(
        "store_settings.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    terminal = models.ForeignKey(
        "store_settings.Terminal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True
    )
    order_status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.OPEN, db_index=True
    )

    # Loyalty
    loyalty_points_earned = models.IntegerField(default=0)
    loyalty_points_redeemed = models.IntegerField(default=0)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["payment_status", "created_at"]),
            models.Index(fields=["order_status", "created_at"]),
            models.Index(fields=["cashier", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.order_number

    def recalculate_totals(self):
        from django.db.models import Sum, F, ExpressionWrapper, DecimalField
        result = self.items.aggregate(
            subtotal=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField(),
                )
            ),
            tax=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price") * F("tax_rate") / 100,
                    output_field=DecimalField(),
                )
            ),
        )
        self.subtotal = result["subtotal"] or 0
        self.tax_amount = result["tax"] or 0
        disc = self.subtotal * self.discount_percent / 100 if self.discount_percent else self.discount_amount
        self.discount_amount = disc
        self.grand_total = self.subtotal + self.tax_amount - self.discount_amount
        if self.grand_total < 0:
            self.grand_total = 0


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product", on_delete=models.PROTECT, related_name="order_items"
    )
    product_name = models.CharField(max_length=200)  # snapshot at time of sale
    sku = models.CharField(max_length=100)            # snapshot
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "order_item"
        indexes = [models.Index(fields=["order", "product"])]

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.line_total = (self.unit_price * self.quantity) - self.discount_amount
        super().save(*args, **kwargs)


class ReturnOrder(models.Model):
    class ReturnStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    original_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    cashier = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="returns"
    )
    reason = models.TextField()
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=ReturnStatus.choices, default=ReturnStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "return_order"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Return for {self.original_order.order_number}"


class ReturnItem(models.Model):
    return_order = models.ForeignKey(ReturnOrder, on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "return_item"
