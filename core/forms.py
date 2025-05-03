
from django import forms
from django.forms import inlineformset_factory
from .models import User, Permission

class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Parol"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Parolni tasdiqlash"
    )

    class Meta:
        model = User
        fields = ['username', 'role', 'is_staff', 'is_superuser', 'password', 'confirm_password']
        widgets = {
            'role': forms.Select(choices=User.ROLE_CHOICES),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and password != confirm_password:
            raise forms.ValidationError("Parollar mos kelmaydi.")
        return cleaned_data

class PermissionForm(forms.ModelForm):
    class Meta:
        model = Permission
        fields = ['menu', 'permission_type']
        widgets = {
            'menu': forms.Select(choices=Permission.MENU_CHOICES),
            'permission_type': forms.Select(choices=Permission.PERMISSION_TYPES),
        }

PermissionFormSet = inlineformset_factory(
    User, Permission, form=PermissionForm, extra=1, can_delete=True
)
