# openoutreach/emails/apps.py
from django.apps import AppConfig


class EmailsConfig(AppConfig):
    name = "openoutreach.emails"
    label = "emails"
    default_auto_field = "django.db.models.BigAutoField"
