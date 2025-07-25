from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Ombor nomi")
    address = models.TextField(blank=True, null=True, verbose_name="Manzil")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")

    class Meta:
        verbose_name = "Ombor"
        verbose_name_plural = "Omborlar"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kategoriya nomi")
    image = models.ImageField(upload_to='category_images/', null=True, blank=True, verbose_name="Rasm")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="Mahsulot nomi")
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Ombor"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Kategoriya"
    )
    image = models.ImageField(upload_to='product_images/', null=True, blank=True, verbose_name="Rasm")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Miqdor")
    initial_quantity = models.PositiveIntegerField(default=0, verbose_name="Boshlang'ich miqdor",
                                                   help_text="Mahsulot qo'shilganda avtomatik qo'shiladi")
    minimum_quantity = models.PositiveIntegerField(default=10, verbose_name="Minimal miqdor")
    unit = models.CharField(max_length=20, default="dona", verbose_name="O'lchov birligi")
    barcode = models.CharField(max_length=50, blank=True, null=True, verbose_name="Shtrix kod")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")

    class Meta:
        unique_together = ('name', 'warehouse')
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

    def save(self, *args, **kwargs):
        # Boshlang'ich miqdor bilan quantity ni yangilash
        if self.pk is None:  # Faqat yangi mahsulot uchun
            if self.initial_quantity > 0:
                self.quantity = self.initial_quantity
        elif hasattr(self, '_initial_state') and self.initial_quantity != self._initial_state.get('initial_quantity',
                                                                                                  0):
            diff = self.initial_quantity - self._initial_state.get('initial_quantity', 0)
            if diff > 0:
                self.quantity += diff

        super().save(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_state = self._get_initial_state()

    def _get_initial_state(self):
        if self.pk:
            return {field.name: getattr(self, field.name) for field in self._meta.fields}
        return {}

    def __str__(self):
        return f"{self.name} ({self.warehouse.name})"

    @property
    def is_low_stock(self):
        """Minimal miqdordan kam ekanligini tekshiradi"""
        return self.quantity <= self.minimum_quantity


class Incoming(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='incomings',
        verbose_name="Ombor"
    )
    supplier = models.ForeignKey(
        'partners.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ta'minotchi"
    )
    date = models.DateField(verbose_name="Sana")
    invoice_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Faktura raqami")
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Umumiy summa")
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="To'langan summa")
    debt = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Qarz")
    note = models.TextField(blank=True, verbose_name="Izoh")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Kirim"
        verbose_name_plural = "Kirimlar"
        ordering = ['-date', '-created_at']

    def delete(self, *args, **kwargs):
        """Kirim o'chirilganda barcha mahsulot miqdorlarini qaytarish"""
        # Avval barcha itemlar miqdorini mahsulotlardan ayirish
        for item in self.items.all():
            if item.product:
                item.product.quantity -= item.quantity
                item.product.save()

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Kirim #{self.id} - {self.supplier or 'Noma`lum ta`minotchi'} - {self.date}"

    def save(self, *args, **kwargs):
        # Qarzni avtomatik hisoblash
        if self.total_amount is not None and self.paid_amount is not None:
            self.debt = self.total_amount - self.paid_amount
        super().save(*args, **kwargs)

    def clean(self):
        # To'langan summa umumiy summadan katta bo'lmasligini tekshirish
        if self.paid_amount and self.total_amount and self.paid_amount > self.total_amount:
            raise ValidationError("To'langan summa umumiy summadan katta bo'la olmaydi")


class IncomingItem(models.Model):
    incoming = models.ForeignKey(
        Incoming,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Kirim"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Mahsulot"
    )
    quantity = models.PositiveIntegerField(verbose_name="Miqdor")
    price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Narx")
    total = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Jami")
    batch_number = models.CharField(max_length=100, blank=True, verbose_name="Partiya raqami")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Yaroqlilik muddati")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Kirim elementi"
        verbose_name_plural = "Kirim elementlari"

    def save(self, *args, **kwargs):
        # Jami summani avtomatik hisoblash
        if self.quantity and self.price:
            self.total = self.quantity * self.price

        # Partiya raqamini avtomatik yaratish
        if not self.batch_number and self.product:
            self.batch_number = f"BATCH-{self.incoming.id}-{self.product.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        is_new = self.pk is None
        old_quantity = 0

        if not is_new:
            old_instance = IncomingItem.objects.get(pk=self.pk)
            old_quantity = old_instance.quantity

        super().save(*args, **kwargs)

        # Mahsulot miqdorini yangilash
        if is_new:
            self.product.quantity += self.quantity
        else:
            quantity_diff = self.quantity - old_quantity
            self.product.quantity += quantity_diff

        self.product.save()

    def delete(self, *args, **kwargs):
        # Element o'chirilganda mahsulot miqdorini kamaytirish
        if self.product:
            self.product.quantity -= self.quantity
            self.product.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit}"


class Outgoing(models.Model):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='outgoings',
        verbose_name="Ombor"
    )
    customer = models.ForeignKey(
        'partners.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Xaridor"
    )
    date = models.DateField(verbose_name="Sana")
    invoice_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Faktura raqami")
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Umumiy summa")
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="To'langan summa")
    debt = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Qarz")
    profit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Foyda")
    note = models.TextField(blank=True, verbose_name="Izoh")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Chiqim"
        verbose_name_plural = "Chiqimlar"
        ordering = ['-date', '-created_at']

    def delete(self, *args, **kwargs):
        """Chiqim o'chirilganda barcha mahsulot miqdorlarini qaytarish"""
        # Avval barcha itemlar miqdorini mahsulotlarga qaytarish
        for item in self.items.all():
            if item.product:
                item.product.quantity += item.quantity
                item.product.save()

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Chiqim #{self.id} - {self.customer or 'Noma`lum xaridor'} - {self.date}"

    def save(self, *args, **kwargs):
        # Qarzni avtomatik hisoblash
        if self.total_amount is not None and self.paid_amount is not None:
            self.debt = self.total_amount - self.paid_amount
        super().save(*args, **kwargs)

    def clean(self):
        # To'langan summa umumiy summadan katta bo'lmasligini tekshirish
        if self.paid_amount and self.total_amount and self.paid_amount > self.total_amount:
            raise ValidationError("To'langan summa umumiy summadan katta bo'la olmaydi")


class OutgoingItem(models.Model):
    outgoing = models.ForeignKey(
        Outgoing,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Chiqim"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Mahsulot",
        null=True,
        blank=True
    )
    quantity = models.PositiveIntegerField(verbose_name="Miqdor")
    price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Sotuv narxi")
    cost_price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Tan narxi")
    total = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Jami")
    profit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Foyda")
    batch_number = models.CharField(max_length=100, blank=True, verbose_name="Partiya raqami")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Chiqim elementi"
        verbose_name_plural = "Chiqim elementlari"

    def save(self, *args, **kwargs):
        # Jami summani avtomatik hisoblash
        if self.quantity and self.price:
            self.total = self.quantity * self.price

        # Foydani avtomatik hisoblash
        if self.quantity and self.price and self.cost_price:
            self.profit = (self.price - self.cost_price) * self.quantity

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Element o'chirilganda mahsulot miqdorini qaytarish
        if self.product:
            self.product.quantity += self.quantity
            self.product.save()
        super().delete(*args, **kwargs)

    def clean(self):
        # Chiqim vaqtida mahsulot miqdorini tekshirish
        if self.product and self.quantity:
            if self.product.quantity < self.quantity:
                raise ValidationError(f"{self.product.name} mahsulotidan yetarli miqdor yo'q")

    def __str__(self):
        if self.product:
            return f"{self.product.name} - {self.quantity} {self.product.unit}"
        return f"Mahsulot tanlanmagan - {self.quantity}"