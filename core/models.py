
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Username kiritilishi shart')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'super_admin')
        return self.create_user(username, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('user', 'Foydalanuvchi'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    objects = UserManager()

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def __str__(self):
        return self.username

class Permission(models.Model):
    PERMISSION_TYPES = (
        ('view', 'Ko‘rish'),
        ('edit', 'Tahrirlash'),
        ('delete', 'O‘chirish'),
    )
    MENU_CHOICES = (
        ('kirim', 'Kirim'),
        ('chiqim', 'Chiqim'),
        ('ombor', 'Ombor'),
        ('taminotchilar', 'Ta‘minotchilar'),
        ('taminotchi_tolov', 'Ta‘minotchi To‘lov'),
        ('xaridorlar', 'Xaridorlar'),
        ('xaridor_tolov', 'Xaridor To‘lov'),
        ('hisobot', 'Hisobot'),
        ('foydalanuvchilar', 'Foydalanuvchilar'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permissions')
    menu = models.CharField(max_length=50, choices=MENU_CHOICES)
    permission_type = models.CharField(max_length=20, choices=PERMISSION_TYPES)

    class Meta:
        unique_together = ('user', 'menu', 'permission_type')
        verbose_name = 'Ruxsat'
        verbose_name_plural = 'Ruxsatlar'

    def __str__(self):
        return f"{self.user.username} - {self.menu} - {self.permission_type}"
