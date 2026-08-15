"""Test-only user profile, used to exercise related-field rules in querysets."""

import sys

from django.contrib.auth.models import User
from django.db import models

TESTING = "pytest" in sys.modules


class Profile(models.Model):
    """Tracks a per-user counter that the test suite filters sequences on."""

    user = models.OneToOneField(
        "auth.User",
        related_name="profile",
        on_delete=models.CASCADE,
    )
    credits = models.PositiveIntegerField(default=0)


def user_post_save(sender, instance, created, raw, **kwargs):
    # Use this table only when testing
    if created and TESTING:
        Profile.objects.create(user=instance)


models.signals.post_save.connect(user_post_save, sender=User)


class UUIDUser(models.Model):
    """Stand-in user model with a UUID primary key, for lookup-field tests."""

    id = models.UUIDField(primary_key=True)
