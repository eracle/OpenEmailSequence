from django.core.management.base import BaseCommand

from email_sequences.models import Sequence


class Command(BaseCommand):
    def handle(self, *args, **options):
        for sequence in Sequence.objects.filter(enabled=True):
            sequence.sequence.run()
