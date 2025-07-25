from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):
    """
    Custom user manager for User model
    """

    def create_user(self, username, password=None, **extra_fields):
        """
        Create and save a User with the given username and password.
        """
        if not username:
            raise ValueError('Username kiritilishi shart')

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given username and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'super_admin')
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    ROLE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('user', 'Foydalanuvchi'),
    )

    # Custom fields
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name='Rol',
        help_text='Foydalanuvchi roli'
    )

    # Use custom manager
    objects = UserManager()

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'
        db_table = 'custom_user'
        ordering = ['username']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def clean(self):
        """
        Custom validation for User model
        """
        super().clean()
        if self.role == 'super_admin' and not self.is_superuser:
            self.is_superuser = True
            self.is_staff = True

    def save(self, *args, **kwargs):
        """
        Override save method to ensure consistency
        """
        self.clean()
        super().save(*args, **kwargs)

    def has_permission(self, menu, permission_type):
        """
        Check if user has specific permission for a menu
        """
        if self.is_superuser:
            return True

        return self.permissions.filter(
            menu=menu,
            permission_type=permission_type
        ).exists()

    def get_user_menus(self):
        """
        Get all menus user has access to
        """
        if self.is_superuser:
            return [choice[0] for choice in Permission.MENU_CHOICES]

        return list(self.permissions.values_list('menu', flat=True).distinct())


class Permission(models.Model):
    """
    Permission model for managing user access to different menus
    """
    PERMISSION_TYPES = (
        ('view', 'Ko\'rish'),
        ('add', 'Qo\'shish'),
        ('change', 'Tahrirlash'),
        ('delete', 'O\'chirish'),
    )

    MENU_CHOICES = (
        ('kirim', 'Kirim'),
        ('chiqim', 'Chiqim'),
        ('ombor', 'Ombor'),
        ('taminotchilar', 'Ta\'minotchilar'),
        ('taminotchi_tolov', 'Ta\'minotchi To\'lov'),
        ('xaridorlar', 'Xaridorlar'),
        ('xaridor_tolov', 'Xaridor To\'lov'),
        ('hisobot', 'Hisobot'),
        ('foydalanuvchilar', 'Foydalanuvchilar'),
        ('sozlamalar', 'Sozlamalar'),
    )

    # Fields
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='permissions',
        verbose_name='Foydalanuvchi'
    )
    menu = models.CharField(
        max_length=50,
        choices=MENU_CHOICES,
        verbose_name='Menyu'
    )
    permission_type = models.CharField(
        max_length=20,
        choices=PERMISSION_TYPES,
        verbose_name='Ruxsat turi'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqt')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Yangilangan vaqt')

    class Meta:
        unique_together = ('user', 'menu', 'permission_type')
        verbose_name = 'Ruxsat'
        verbose_name_plural = 'Ruxsatlar'
        db_table = 'user_permission'
        ordering = ['user__username', 'menu', 'permission_type']

    def __str__(self):
        return f"{self.user.username} - {self.get_menu_display()} - {self.get_permission_type_display()}"

    def clean(self):
        """
        Custom validation for Permission model
        """
        super().clean()
        # Super admin doesn't need explicit permissions
        if self.user.is_superuser:
            raise ValidationError('Super admin foydalanuvchilarga ruxsat berilmaydi.')

    def save(self, *args, **kwargs):
        """
        Override save method with validation
        """
        self.clean()
        super().save(*args, **kwargs)


class UserSession(models.Model):
    """
    Track user sessions for security purposes
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='Foydalanuvchi'
    )
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(verbose_name='IP manzil')
    user_agent = models.TextField(verbose_name='Brauzer ma\'lumoti')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Kirish vaqti')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='So\'nggi faollik')
    is_active = models.BooleanField(default=True, verbose_name='Faol')

    class Meta:
        verbose_name = 'Foydalanuvchi sessiyasi'
        verbose_name_plural = 'Foydalanuvchi sessiyalari'
        db_table = 'user_session'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ActivityLog(models.Model):
    """
    Foydalanuvchi harakatlarini yozib borish uchun model
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        verbose_name='Foydalanuvchi'
    )
    action = models.CharField(
        max_length=255,
        verbose_name='Harakat'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Vaqti'
    )

    class Meta:
        verbose_name = 'Harakat jurnali'
        verbose_name_plural = 'Harakat jurnallari'
        db_table = 'activity_log'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"