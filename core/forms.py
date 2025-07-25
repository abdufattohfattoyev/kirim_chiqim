from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Permission


class UserForm(forms.ModelForm):
    """
    Enhanced User form with better validation and styling
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parolni kiriting'
        }),
        required=False,
        label="Parol",
        help_text="Yangi parol kiriting (bo'sh qoldiring agar parolni o'zgartirmoqchi bo'lmasangiz)"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parolni takrorlang'
        }),
        required=False,
        label="Parolni tasdiqlash"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Foydalanuvchi nomini kiriting'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ismni kiriting'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Familiyani kiriting'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email manzilini kiriting'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'username': 'Foydalanuvchi nomi',
            'first_name': 'Ism',
            'last_name': 'Familiya',
            'email': 'Email',
            'role': 'Rol',
            'is_staff': 'Xodim',
            'is_active': 'Faol',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make username required
        self.fields['username'].required = True

        # Set password as required for new users
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True

    def clean_username(self):
        """
        Validate username uniqueness
        """
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('Foydalanuvchi nomi kiritilishi shart.')

        # Check uniqueness (excluding current instance)
        qs = User.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError('Bu foydalanuvchi nomi allaqachon mavjud.')

        return username

    def clean_email(self):
        """
        Validate email uniqueness if provided
        """
        email = self.cleaned_data.get('email')
        if email:
            # Check uniqueness (excluding current instance)
            qs = User.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise ValidationError('Bu email manzil allaqachon mavjud.')

        return email

    def clean_password(self):
        """
        Validate password strength
        """
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password)
            except ValidationError as error:
                raise ValidationError(error.messages)
        return password

    def clean(self):
        """
        Cross-field validation
        """
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        role = cleaned_data.get('role')

        # Password confirmation
        if password and password != confirm_password:
            raise ValidationError('Parollar mos kelmaydi.')

        # Role-based validation
        if role == 'super_admin':
            cleaned_data['is_staff'] = True
            cleaned_data['is_superuser'] = True

        return cleaned_data


class PermissionForm(forms.ModelForm):
    """
    Enhanced Permission form
    """

    class Meta:
        model = Permission
        fields = ['menu', 'permission_type']
        widgets = {
            'menu': forms.Select(attrs={
                'class': 'form-control form-control-sm'
            }),
            'permission_type': forms.Select(attrs={
                'class': 'form-control form-control-sm'
            }),
        }
        labels = {
            'menu': 'Menyu',
            'permission_type': 'Ruxsat turi',
        }

    def clean(self):
        """
        Validate permission
        """
        cleaned_data = super().clean()
        menu = cleaned_data.get('menu')
        permission_type = cleaned_data.get('permission_type')

        if menu and permission_type:
            # Check if this permission already exists for the user
            if hasattr(self, 'instance') and self.instance.user:
                existing = Permission.objects.filter(
                    user=self.instance.user,
                    menu=menu,
                    permission_type=permission_type
                )

                if self.instance.pk:
                    existing = existing.exclude(pk=self.instance.pk)

                if existing.exists():
                    raise ValidationError(f'Bu ruxsat allaqachon mavjud.')

        return cleaned_data


# Create formset for permissions
PermissionFormSet = inlineformset_factory(
    User,
    Permission,
    form=PermissionForm,
    extra=3,  # Show 3 empty forms by default
    can_delete=True,
    fk_name='user'
)


class LoginForm(forms.Form):
    """
    Enhanced login form
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Foydalanuvchi nomini kiriting',
            'autofocus': True,
            'autocomplete': 'username'
        }),
        label='Foydalanuvchi nomi'
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parolni kiriting',
            'autocomplete': 'current-password'
        }),
        label='Parol'
    )

    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Meni eslab qol'
    )

    def clean_username(self):
        """
        Clean and validate username
        """
        username = self.cleaned_data.get('username')
        if username:
            username = username.strip()
        return username


class UserSearchForm(forms.Form):
    """
    Form for searching users
    """
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Foydalanuvchi nomini kiriting...'
        }),
        label='Qidiruv'
    )

    role = forms.ChoiceField(
        choices=[('', 'Barcha rollar')] + list(User.ROLE_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Rol'
    )

    is_active = forms.ChoiceField(
        choices=[
            ('', 'Barchasi'),
            ('true', 'Faol'),
            ('false', 'Nofaol')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Holat'
    )


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for users to update their own profile
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ismingizni kiriting'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Familiyangizni kiriting'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email manzilingizni kiriting'
            }),
        }
        labels = {
            'first_name': 'Ism',
            'last_name': 'Familiya',
            'email': 'Email',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Bu email manzili boshqa foydalanuvchi tomonidan ishlatilgan.")
        return email