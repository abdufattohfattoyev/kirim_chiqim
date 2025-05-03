from django import forms
from django.core.validators import RegexValidator

from .models import Supplier, Customer, SupplierPayment, CustomerPayment


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone_number', 'initial_debt']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': '+998901234567'}),  # 13 ta belgi
            'initial_debt': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if not phone_number.startswith('+') or len(phone_number) != 13:  # + dan tashqari 12 ta belgi
            raise forms.ValidationError("Telefon raqami + bilan boshlanishi va undan keyin 12 ta raqamdan iborat bo'lishi kerak (umumiy 13 ta belgi).")
        return phone_number


class CustomerForm(forms.ModelForm):
    phone_number = forms.CharField(
        max_length=13,
        validators=[
            RegexValidator(
                regex=r'^\+\d{12}$',
                message="Telefon raqami + bilan boshlanishi va undan keyin 12 ta raqamdan iborat bo'lishi kerak (masalan: +998901234567)"
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998901234567',
            'pattern': '^\+\d{12}$'
        })
    )

    initial_debt = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )

    class Meta:
        model = Customer
        fields = ['name', 'phone_number', 'initial_debt', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Xaridor ismi',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Izohlar...',
                'maxlength': '500'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        phone_number = cleaned_data.get('phone_number')

        # Check for duplicate phone number (except current instance)
        if phone_number:
            queryset = Customer.objects.filter(phone_number=phone_number)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                self.add_error('phone_number', 'Bu telefon raqami allaqachon ro\'yxatdan o\'tgan.')

        return cleaned_data

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError("Ism kamida 2 ta belgidan iborat bo'lishi kerak.")
        return name

    def clean_notes(self):
        notes = self.cleaned_data.get('notes', '').strip()
        if notes and len(notes) > 500:
            raise forms.ValidationError("Izoh 500 belgidan oshmasligi kerak.")
        return notes


class SupplierPaymentForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Sana")

    class Meta:
        model = SupplierPayment
        fields = ['date', 'supplier', 'amount', 'payment_type', 'note']
        widgets = {
            'payment_type': forms.Select(choices=(('cash', 'Naqd'), ('card', 'Karta'))),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
            'note': forms.Textarea(attrs={'rows': 4}),
        }


class CustomerPaymentForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Sana")

    class Meta:
        model = CustomerPayment
        fields = ['date', 'customer', 'amount', 'payment_type', 'note']
        widgets = {
            'payment_type': forms.Select(choices=(('cash', 'Naqd'), ('card', 'Karta'))),
            'amount': forms.NumberInput(attrs={'step': '0.01'}),
            'note': forms.Textarea(attrs={'rows': 4}),
        }
