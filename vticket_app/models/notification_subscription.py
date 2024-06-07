from django.db import models

class NotificationSubscription(models.Model):
    class Meta:
        db_table = "notification_subscriptions"

    email = models.EmailField(primary_key=True)
    create_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True)

    def unsubscript(self):
        self.deleted_at = None
        self.save()