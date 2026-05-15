from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to="store/logos/", blank=True, null=True)
    currency = models.CharField(max_length=10, default="MMK")
    currency_symbol = models.CharField(max_length=5, default="K")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    receipt_footer = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "store"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Terminal(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="terminals")
    name = models.CharField(max_length=100)
    terminal_id = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "terminal"

    def __str__(self):
        return f"{self.store.name} – {self.name}"


class Shift(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE, related_name="shifts")
    cashier = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="shifts"
    )
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cash_difference = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "shift"
        ordering = ["-opened_at"]
        indexes = [models.Index(fields=["status", "opened_at"])]

    def __str__(self):
        return f"Shift {self.pk} – {self.status}"
