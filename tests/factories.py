from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from email_sequences.models import Campaign, Sequence


class CampaignFactory(DjangoModelFactory):
    name = Faker("word")
    delete_sequences = Faker("pybool")

    class Meta:
        model = Campaign


class SequenceFactory(DjangoModelFactory):
    name = Faker("sentences", nb=3)
    campaign = SubFactory(CampaignFactory)

    class Meta:
        model = Sequence
        django_get_or_create = ("name",)
