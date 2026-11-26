from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Customer, Notification, User

@receiver(post_save, sender=Customer)
def create_customer_notification(sender, instance, created, **kwargs):
    if created:
        # Notify all users/admins
        # For simplicity, we create one notification with recipient=None (meaning 'all')
        # or specific user if needed. Let's create for all users for now or use 'all' logic in view.
        # But 'recipient' is ForeignKey to User.
        # Let's just create key for the first admin or all admins.
        
        admins = User.objects.filter(is_superuser=True)
        if not admins.exists():
            admins = User.objects.all()
            
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title="New Customer Added",
                message=f"New customer {instance.name} (Code: {instance.code}) has been added.",
                notification_type='new_customer',
                related_id=instance.id,
                related_model='Customer'
            )
