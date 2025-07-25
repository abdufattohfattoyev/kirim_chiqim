from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from .models import Product, Category, Incoming, Outgoing, Warehouse, IncomingItem, OutgoingItem


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ombor nomini kiriting'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        existing_warehouse = Warehouse.objects.filter(name=name).exclude(id=self.instance.id if self.instance else None)
        if existing_warehouse.exists():
            raise forms.ValidationError("Bu nomdagi ombor allaqachon mavjud.")
        return name


class ProductForm(forms.ModelForm):
    new_category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Yangi kategoriya nomini kiriting'})
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = Product
        fields = ['name', 'warehouse', 'category', 'image', 'quantity', 'minimum_quantity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mahsulot nomini kiriting'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Miqdor'}),
            'minimum_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimal miqdor'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        warehouse = self.cleaned_data.get('warehouse')
        if warehouse and Product.objects.filter(name=name, warehouse=warehouse).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Bu nomdagi mahsulot ushbu omborda allaqachon mavjud. Iltimos, boshqa nom kiriting.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        new_category = cleaned_data.get('new_category')
        quantity = cleaned_data.get('quantity')

        if not category and new_category:
            try:
                category, created = Category.objects.get_or_create(name=new_category)
                cleaned_data['category'] = category
            except Exception as e:
                raise ValidationError(f"Kategoriya yaratishda xatolik: {str(e)}")
        elif not category and not new_category:
            raise ValidationError("Iltimos, kategoriya tanlang yoki yangi kategoriya nomini kiriting.")

        if quantity is None or quantity < 0:
            raise ValidationError("Miqdor 0 yoki undan katta bo'lishi kerak.")

        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kategoriya nomini kiriting'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if Category.objects.filter(name=name).exists():
            raise forms.ValidationError("Bu nomdagi kategoriya allaqachon mavjud.")
        return name


class IncomingForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_warehouse'}),
        required=True
    )

    class Meta:
        model = Incoming
        fields = ['warehouse', 'supplier', 'date', 'total_amount', 'paid_amount', 'debt', 'note']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'debt': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class IncomingItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        warehouse = kwargs.pop('warehouse', None)
        super().__init__(*args, **kwargs)
        if warehouse:
            self.fields['product'].queryset = Product.objects.filter(warehouse=warehouse)

    class Meta:
        model = IncomingItem
        fields = ['product', 'quantity', 'price', 'total']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }


class IncomingItemFormSet(forms.models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.warehouse = kwargs.pop('warehouse', None)
        super().__init__(*args, **kwargs)
        for form in self.forms:
            form.warehouse = self.warehouse

    def clean(self):
        super().clean()
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                if not form.cleaned_data.get('product'):
                    raise forms.ValidationError("Mahsulot tanlanmagan.")
                if not form.cleaned_data.get('quantity') or form.cleaned_data['quantity'] <= 0:
                    raise forms.ValidationError("Miqdor 0 dan katta bo'lishi kerak.")

                # Agar self.instance hali saqlanmagan bo'lsa, warehouse ni formdan olish
                if self.instance and not self.instance.pk:
                    warehouse = self.warehouse
                else:
                    warehouse = self.instance.warehouse

                product = form.cleaned_data.get('product')
                if product and warehouse and product.warehouse != warehouse:
                    raise forms.ValidationError(f"{product.name} ushbu omborga tegishli emas.")


IncomingItemFormSetFactory = inlineformset_factory(
    Incoming,
    IncomingItem,
    form=IncomingItemForm,
    formset=IncomingItemFormSet,
    fields=['product', 'quantity', 'price', 'total'],
    extra=1,
    can_delete=True
)


class OutgoingForm(forms.ModelForm):
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = Outgoing
        fields = ['warehouse', 'customer', 'date', 'total_amount', 'paid_amount', 'note']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class OutgoingItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.warehouse = kwargs.pop('warehouse', None)
        super().__init__(*args, **kwargs)
        if self.warehouse:
            self.fields['product'].queryset = Product.objects.filter(warehouse=self.warehouse)

    class Meta:
        model = OutgoingItem
        fields = ['product', 'quantity', 'price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class BaseOutgoingItemFormSet(forms.models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.warehouse = kwargs.pop('warehouse', None)
        super().__init__(*args, **kwargs)
        # Har bir form uchun warehouse ni o'rnatish
        for form in self.forms:
            if hasattr(form, 'fields'):
                if self.warehouse:
                    form.fields['product'].queryset = Product.objects.filter(warehouse=self.warehouse)

    def _construct_form(self, i, **kwargs):
        # Yangi form yaratilganda warehouse ni uzatish
        kwargs['warehouse'] = self.warehouse
        return super()._construct_form(i, **kwargs)

    def clean(self):
        super().clean()

        if not self.is_valid():
            return

        # Kamida bitta form bo'lishini tekshirish
        valid_forms_count = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                valid_forms_count += 1

                product = form.cleaned_data.get('product')
                quantity = form.cleaned_data.get('quantity')

                if not product:
                    raise forms.ValidationError("Mahsulot tanlanmagan.")

                if not quantity or quantity <= 0:
                    raise forms.ValidationError("Miqdor 0 dan katta bo'lishi kerak.")

                # Ombordagi mavjud miqdorni tekshirish
                if product and quantity > product.quantity:
                    raise forms.ValidationError(
                        f"{product.name} uchun yetarli miqdor mavjud emas. "
                        f"Mavjud: {product.quantity}, so'ralgan: {quantity}"
                    )

        if valid_forms_count == 0:
            raise forms.ValidationError("Kamida bitta mahsulot kiritilishi kerak.")


# Inline formset yaratish
OutgoingItemFormSet = inlineformset_factory(
    Outgoing,
    OutgoingItem,
    form=OutgoingItemForm,
    formset=BaseOutgoingItemFormSet,
    extra=1,
    can_delete=True,
    min_num=0,  # min_num ni 0 ga o'zgartiramiz
    validate_min=False  # validate_min ni False qilamiz
)