from django.db import models
from django.contrib.auth import get_user_model
from partners.models import Supplier, Customer
from django.utils import timezone

User = get_user_model()

class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='products'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None
    )
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    minimum_quantity = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'warehouse')

class Incoming(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='incomings'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    date = models.DateField(verbose_name="Sana")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.supplier or 'No Supplier'} - {self.date}"

    def save(self, *args, **kwargs):
        if self.total_amount and self.paid_amount:
            self.debt = self.total_amount - self.paid_amount
        super().save(*args, **kwargs)

class IncomingItem(models.Model):
    incoming = models.ForeignKey(Incoming, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    batch_number = models.CharField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.batch_number and self.product:
            self.batch_number = f"BATCH-{self.incoming.id}-{self.product.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product or 'No Product'} - {self.quantity}"

class Outgoing(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='outgoings'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    date = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    debt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.customer or 'No Customer'} - {self.date}"

class OutgoingItem(models.Model):
    outgoing = models.ForeignKey(Outgoing, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    batch_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.product or 'No Product'} - {self.quantity}"