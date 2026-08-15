import random
from typing import Any, List

import pytest

from email_sequences.models import Campaign, Sequence
from tests.factories import CampaignFactory, SequenceFactory

pytestmark = pytest.mark.django_db


def _sequences_generator(amount: int, **sequence_extra_args: Any) -> List[Campaign]:
    return SequenceFactory.create_batch(amount, **sequence_extra_args)


class TestCaseCampaign:
    def test_campaings_creation(self):
        campaign = CampaignFactory()
        sequence_count = random.randint(5, 15)
        _sequences_generator(sequence_count, campaign=campaign)

        assert len(campaign.sequence_set.all()) == sequence_count

    @pytest.mark.parametrize(
        ("delete_sequences, sequence_count, sequence_count_after_delete"),
        (
            (True, 10, 0),
            (False, 10, 10),
        ),
    )
    def test_remove_campaings(
        self,
        delete_sequences: bool,
        sequence_count: int,
        sequence_count_after_delete: int,
    ):
        campaign = CampaignFactory(delete_sequences=delete_sequences)
        _sequences_generator(sequence_count, campaign=campaign)

        campaign.delete()

        assert Sequence.objects.count() == sequence_count_after_delete
