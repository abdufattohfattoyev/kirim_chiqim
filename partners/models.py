from django.db import models
from django.core.validators import RegexValidator
from django.db.models import Sum
from django.utils import timezone
from core.models import User


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
        help_text="+998901234567"
    )
    initial_debt = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Boshlang'ich qarzdorlik"
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")

    class Meta:
        verbose_name = "Ta'minotchi"
        verbose_name_plural = "Ta'minotchilar"

    def __str__(self):
        return self.name

    @property
    def balance(self):
        incoming_debt = self.incoming_set.aggregate(total_debt=models.Sum('debt'))['total_debt'] or 0
        payments = self.supplierpayment_set.aggregate(total_paid=models.Sum('amount'))['total_paid'] or 0
        return self.initial_debt + incoming_debt - payments


class Customer(models.Model):
    name = models.CharField(max_length=200, verbose_name="Xaridor nomi")  # Xaridorning ismi
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
    initial_debt = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Boshlang'ich qarzdorlik"  # Dastlabki qarz miqdori
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")  # Izoh maydoni
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")  # Xaridorni kim qo‘shgani

    class Meta:
        verbose_name = "Xaridor"
        verbose_name_plural = "Xaridorlar"

    def __str__(self):
        return self.name

    @property
    def balance(self):
        # Xaridorning umumiy balansini hisoblash
        outgoing_debt = self.outgoing_set.aggregate(total_debt=Sum('debt'))['total_debt'] or 0
        payments = self.customerpayment_set.aggregate(total_paid=Sum('amount'))['total_paid'] or 0
        return self.initial_debt + outgoing_debt - payments


class SupplierPayment(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Ta'minotchi")
    date = models.DateField(default=timezone.now, verbose_name="Sana")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="To'lov summasi")
    payment_type = models.CharField(
        max_length=20, choices=(('cash', 'Naqd'), ('card', 'Karta')), verbose_name="To'lov turi"
    )
    note = models.TextField(blank=True, verbose_name="Izoh")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")

    class Meta:
        verbose_name = "Ta'minotchi to'lovi"
        verbose_name_plural = "Ta'minotchi to'lovlari"

    def __str__(self):
        return f"{self.supplier} - {self.amount}"


class CustomerPayment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Xaridor")
    date = models.DateField(default=timezone.now, verbose_name="Sana")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="To'lov summasi")
    payment_type = models.CharField(
        max_length=20, choices=(('cash', 'Naqd'), ('card', 'Karta')), verbose_name="To'lov turi"
    )
    note = models.TextField(blank=True, verbose_name="Izoh")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratdi")

    class Meta:
        verbose_name = "Xaridor to'lovi"
        verbose_name_plural = "Xaridor to'lovlari"

    def __str__(self):
        return f"{self.customer} - {self.amount}"
