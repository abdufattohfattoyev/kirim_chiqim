
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import SupplierPayment

@receiver(post_save, sender=SupplierPayment)
def send_payment_notification(sender, instance, created, **kwargs):
    if created:
        subject = f"Yangi to'lov: {instance.supplier.name}"
        message = f"{instance.supplier.name} uchun {instance.amount} miqdorida to'lov qo'shildi.\nSana: {instance.date}\nTo'lov turi: {instance.get_payment_type_display()}"
        send_mail(
            subject,
            message,
            'from@example.com',
            ['to@example.com'],
            fail_silently=False,
        )
