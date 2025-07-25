from django.db import models
from django.core.validators import RegexValidator
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name="Ta'minotchi nomi")
    phone_regex = RegexValidator(
        regex=r'^\+\d{12}$',  # + dan keyin 12 ta raqam
        message="Telefon raqami + bilan boshlanishi va undan keyin 12 ta raqamdan iborat bo'lishi kerak (umumiy 13 ta belgi)."
    )
    phone_number = models.CharField(
        max_length=13,  # + (1) + 12 ta raqam = 13
        validators=[phone_regex],
        verbose_name="Telefon raqami",
        help_text="+998901234567",
        unique=True  # Telefon raqami takrorlanmasligi uchun
    )
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    address = models.TextField(blank=True, null=True, verbose_name="Manzil")
    company_name = models.CharField(max_length=300, blank=True, null=True, verbose_name="Kompaniya nomi")
    inn = models.CharField(max_length=20, blank=True, null=True, verbose_name="INN")
    initial_debt = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Boshlang'ich qarzdorlik"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Ta'minotchi"
        verbose_name_plural = "Ta'minotchilar"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def balance(self):
        """Ta'minotchining joriy balansini hisoblash"""
        # Kirimlar orqali qarzlar
        incoming_debt = 0
        try:
            from warehouse.models import Incoming
            incoming_debt = Incoming.objects.filter(supplier=self).aggregate(
                total_debt=Sum('debt')
            )['total_debt'] or 0
        except ImportError:
            pass

        # To'lovlar
        payments = self.supplierpayment_set.aggregate(
            total_paid=Sum('amount')
        )['total_paid'] or 0

        return self.initial_debt + incoming_debt - payments

    @property
    def total_purchases(self):
        """Umumiy xaridlar summasi"""
        try:
            from warehouse.models import Incoming
            return Incoming.objects.filter(supplier=self).aggregate(
                total=Sum('total_amount')
            )['total'] or 0
        except ImportError:
            return 0


class Customer(models.Model):
    name = models.CharField(max_length=200, verbose_name="Xaridor nomi")
    phone_regex = RegexValidator(
        regex=r'^\+\d{12}$',  # Telefon raqami formati: + va 12 ta raqam
        message="Telefon raqami + bilan boshlanishi va undan keyin 12 ta raqamdan iborat bo'lishi kerak (umumiy 13 ta belgi)."
    )
    phone_number = models.CharField(
        max_length=13,  # + (1) + 12 ta raqam = 13
        validators=[phone_regex],
        verbose_name="Telefon raqami",
        help_text="+998901234567",
        unique=True  # Telefon raqami takrorlanmasligi uchun
    )
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    address = models.TextField(blank=True, null=True, verbose_name="Manzil")
    company_name = models.CharField(max_length=300, blank=True, null=True, verbose_name="Kompaniya nomi")
    inn = models.CharField(max_length=20, blank=True, null=True, verbose_name="INN")
    initial_debt = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Boshlang'ich qarzdorlik"
    )
    credit_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Kredit limiti"
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="Chegirma foizi"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Xaridor"
        verbose_name_plural = "Xaridorlar"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def balance(self):
        """Xaridorning joriy balansini hisoblash"""
        # Chiqimlar orqali qarzlar
        outgoing_debt = 0
        try:
            from warehouse.models import Outgoing
            outgoing_debt = Outgoing.objects.filter(customer=self).aggregate(
                total_debt=Sum('debt')
            )['total_debt'] or 0
        except ImportError:
            pass

        # To'lovlar
        payments = self.customerpayment_set.aggregate(
            total_paid=Sum('amount')
        )['total_paid'] or 0

        return self.initial_debt + outgoing_debt - payments

    @property
    def total_purchases(self):
        """Umumiy xaridlar summasi"""
        try:
            from warehouse.models import Outgoing
            return Outgoing.objects.filter(customer=self).aggregate(
                total=Sum('total_amount')
            )['total'] or 0
        except ImportError:
            return 0

    def clean(self):
        """Validatsiya qoidalari"""
        # Chegirma foizi 0-100 oralig'ida bo'lishi kerak
        if self.discount_percent and (self.discount_percent < 0 or self.discount_percent > 100):
            raise ValidationError("Chegirma foizi 0 dan 100 gacha bo'lishi kerak")


class SupplierPayment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Naqd'),
        ('card', 'Karta'),
        ('transfer', 'O\'tkazma'),
        ('check', 'Chek'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Ta'minotchi")
    date = models.DateField(default=timezone.now, verbose_name="Sana")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="To'lov summasi")
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        verbose_name="To'lov turi"
    )
    reference_number = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Hujjat raqami"
    )
    note = models.TextField(blank=True, verbose_name="Izoh")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Ta'minotchi to'lovi"
        verbose_name_plural = "Ta'minotchi to'lovlari"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.supplier.name} - {self.amount:,.2f} so'm - {self.date}"

    def clean(self):
        """Validatsiya qoidalari"""
        # To'lov summasi musbat bo'lishi kerak
        if self.amount <= 0:
            raise ValidationError("To'lov summasi musbat bo'lishi kerak")


class CustomerPayment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Naqd'),
        ('card', 'Karta'),
        ('transfer', 'O\'tkazma'),
        ('check', 'Chek'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Xaridor")
    date = models.DateField(default=timezone.now, verbose_name="Sana")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="To'lov summasi")
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        verbose_name="To'lov turi"
    )
    reference_number = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Hujjat raqami"
    )
    note = models.TextField(blank=True, verbose_name="Izoh")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Xaridor to'lovi"
        verbose_name_plural = "Xaridor to'lovlari"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.customer.name} - {self.amount:,.2f} so'm - {self.date}"

    def clean(self):
        """Validatsiya qoidalari"""
        # To'lov summasi musbat bo'lishi kerak
        if self.amount <= 0:
            raise ValidationError("To'lov summasi musbat bo'lishi kerak")