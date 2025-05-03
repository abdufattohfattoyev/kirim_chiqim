
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product
from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.mail import send_mail
from django.conf import settings


@receiver(post_save, sender=Product)
def check_minimum_quantity(sender, instance, **kwargs):
    if instance.quantity < instance.minimum_quantity:
        # Interfeysda bildirishnoma
        request = getattr(messages, '_request', None)
        if request:
            storage = get_messages(request)
            message = f'{instance.name} mahsuloti omborda {instance.minimum_quantity} tadan kam qoldi!'
            if not any(msg.message == message for msg in storage):
                messages.warning(request, message)

        # Email bildirishnomasi
        try:
            send_mail(
                subject=f'Ogohlantirish: {instance.name} miqdori kamaydi',
                message=f'{instance.name} mahsuloti omborda {instance.quantity} ta qoldi (minimum: {instance.minimum_quantity}).',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],  # O‘zingizning email manzilingiz
                fail_silently=False,
            )
        except Exception as e:
            # Email yuborishda xato yuzaga kelsa, log qilish mumkin
            print(f"Email yuborishda xato: {e}")


