from datetime import timedelta
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import resolve, reverse
from django.utils import timezone

from tests.testapp.models import Profile
from email_sequences.admin import SequenceAdmin, SequenceForm
from email_sequences.sequences import DEFAULT_SEQUENCE_MESSAGE_CLASS, SequenceBase, configured_message_classes, message_class_for
from email_sequences.models import Campaign, Sequence, QuerySetRule, SentEmail, UserUnsubscribe
from email_sequences.utils import get_user_model, unicode

pytestmark = pytest.mark.django_db


def get_user_model_mock():
    from tests.testapp.models import UUIDUser

    return UUIDUser


User = get_user_model()

DEFAULT_MESSAGE_CLASSES_LENGTH = len(configured_message_classes().items())


class SetupDataSequenceMixin:
    NUM_STRING = [
        "first",
        "second",
        "third",
        "fourth",
        "fifth",
        "sixth",
        "seventh",
        "eighth",
        "ninth",
        "tenth",
    ]

    def build_user_data(self):
        """
        Creates 20 users, half of which buy 25 credits a day,
        and the other half that does none.
        """
        start = timezone.now() - timedelta(hours=2)
        for i, name in enumerate(self.NUM_STRING):
            user = User.objects.create(
                username="{name}_25_credits_a_day".format(name=name),
                email="{name}@test.com".format(name=name),
            )
            User.objects.filter(id=user.id).update(
                date_joined=start - timedelta(days=i),
            )

            profile = Profile.objects.get(user=user)
            profile.credits = i * 25
            profile.save()

        for i, name in enumerate(self.NUM_STRING):
            user = User.objects.create(
                username="{name}_no_credits".format(name=name),
                email="{name}@test.com".format(name=name),
            )
            User.objects.filter(id=user.id).update(
                date_joined=start - timedelta(days=i),
            )

    def build_joined_date_sequence(self, shift_one: int = 7, shift_two: int = 8, build_campaign: bool = False):
        campaign = None
        if build_campaign:
            campaign = Campaign.objects.create(name="Custom campaign")
        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
            campaign=campaign,
        )
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="lt",
            field_value="now-{shift_one} days".format(shift_one=shift_one),
        )
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="gte",
            field_value="now-{shift_two} days".format(shift_two=shift_two),
        )
        return model_sequence


class TestCaseSequences(SetupDataSequenceMixin):
    def setup_method(self, test_method):
        self.build_user_data()

    def test_users_exists(self):
        assert 20 == User.objects.all().count()

    @pytest.mark.parametrize(
        "start_days, end_days, filter_dict, count_users",
        (
            (1, 0, {}, 2),  # test_day_zero_users
            (3, 2, {"profile__credits__gt": 0}, 1),  # test_day_two_users_active
            (3, 2, {"profile__credits": 0}, 1),  # test_day_two_users_inactive
            (8, 7, {"profile__credits__gt": 0}, 1),  # test_day_seven_users_active
            (8, 7, {"profile__credits": 0}, 1),  # test_day_seven_users_inactive
            (15, 14, {"profile__credits__gt": 0}, 0),  # test_day_fourteen_users_active
            (15, 14, {"profile__credits": 0}, 0),  # test_day_fourteen_users_inactive
        ),
    )
    def test_multiple_days_users_filter(
        self, start_days: int, end_days: int, filter_dict: Dict[str, Any], count_users: int
    ):
        start = timezone.now() - timedelta(days=start_days)
        end = timezone.now() - timedelta(days=end_days)
        assert (
            count_users
            == User.objects.filter(
                date_joined__range=(start, end),
                **filter_dict,
            ).count()
        )

    ########################
    #   RELATION SNAGGER   #
    ########################

    def test_get_simple_fields(self):
        from email_sequences.utils import get_simple_fields

        simple_fields = get_simple_fields(User)
        assert bool([sf for sf in simple_fields if "profile" in sf[0]])

    ##################
    #   TEST SEQUENCES   #
    ##################

    def test_backwards_sequence_class(self):
        for sequence in Sequence.objects.all():
            assert issubclass(sequence.sequence.__class__, SequenceBase)

    @pytest.mark.parametrize(
        "can_resend_sequence, expected_pruned_count",
        (
            (False, 0),  # No resend, default configuration
            (True, 2),  # Enable resend sequence.
        ),
    )
    def test_custom_sequence(self, can_resend_sequence: bool, expected_pruned_count: int):
        """
        Test a simple sequence with resend disabled and enabled
        """
        model_sequence = self.build_joined_date_sequence()
        model_sequence.can_resend_sequence = can_resend_sequence
        model_sequence.save()

        sequence = model_sequence.sequence

        # ensure we are starting from a blank slate
        # 2 people meet the criteria
        assert 2 == sequence.get_queryset().count()
        sequence.prune()
        # no one is pruned, never sent before
        assert 2 == sequence.get_queryset().count()
        # confirm nothing sent before
        assert 0 == SentEmail.objects.count()

        # send the sequence
        sequence.send()
        assert 2 == SentEmail.objects.count()  # got sent

        for sent in SentEmail.objects.all():
            assert "HELLO" in sent.subject
            assert "KETTEHS ROCK" in sent.body

        # subsequent runs reflect previous activity
        sequence = Sequence.objects.get(id=model_sequence.id).sequence
        # 2 people meet the criteria
        assert 2 == sequence.get_queryset().count()
        sequence.prune()
        assert expected_pruned_count == sequence.get_queryset().count()  # Check who many users are pruned

    def test_custom_sequence_exclude_unsubscribed(self):
        """
        Test a simple sequence with resend disabled and enabled (Sequence)
        """
        model_sequence = self.build_joined_date_sequence()
        sequence = model_sequence.sequence

        # Disable unsubscribe users
        setattr(
            settings,
            "SEQUENCE_UNSUBSCRIBE_USERS",
            False,
        )

        # create unsubscribed user model
        some_user = sequence.get_queryset().first()
        model_sequence.unsubscribed_users.add(some_user.pk)

        # User in queryset. It is not excluded even if the user is unsubscribed
        sequence.prune()
        assert some_user in sequence.get_queryset()

        # Enable unsubscribe users
        setattr(
            settings,
            "SEQUENCE_UNSUBSCRIBE_USERS",
            True,
        )

        # User not in queryset. It is excluded.
        sequence.prune()
        assert some_user not in sequence.get_queryset()

    def test_custom_sequence_exclude_unsubscribed_campaign(self):
        """
        Test a simple sequence with resend disabled and enabled (Campaign)
        """
        model_sequence = self.build_joined_date_sequence(build_campaign=True)
        sequence = model_sequence.sequence
        campaign = model_sequence.campaign

        # Disable unsubscribe users
        setattr(
            settings,
            "SEQUENCE_UNSUBSCRIBE_USERS",
            False,
        )

        # create unsubscribed user model
        some_user = sequence.get_queryset().first()
        campaign.unsubscribed_users.add(some_user.pk)

        # User in queryset. It is not excluded even if the user is unsubscribed
        sequence.prune()
        assert some_user in sequence.get_queryset()

        # Enable unsubscribe users
        setattr(
            settings,
            "SEQUENCE_UNSUBSCRIBE_USERS",
            True,
        )

        # User not in queryset. It is excluded.
        sequence.prune()
        assert some_user not in sequence.get_queryset()

    def test_custom_sequence_exclude_unsubscribed_app(self):
        """
        Test a simple sequence with resend disabled and enabled (General)
        """
        model_sequence = self.build_joined_date_sequence()
        sequence = model_sequence.sequence

        # Disable unsubscribe users
        setattr(
            settings,
            "SEQUENCE_UNSUBSCRIBE_USERS",
            False,
        )

        # create unsubscribed user model
        some_user = sequence.get_queryset().first()
        UserUnsubscribe.objects.create(user=some_user)

        # User in queryset. It is not excluded even if the user is unsubscribed
        sequence.prune()
        assert some_user in sequence.get_queryset()

        # Enable unsubscribe users
        setattr(
            settings,
            "SEQUENCE_UNSUBSCRIBE_USERS",
            True,
        )

        # User not in queryset. It is excluded.
        sequence.prune()
        assert some_user not in sequence.get_queryset()

    def test_custom_short_term_sequence(self):
        model_sequence = self.build_joined_date_sequence(shift_one=3, shift_two=4)
        sequence = model_sequence.sequence

        # ensure we are starting from a blank slate
        # 2 people meet the criteria
        assert 2 == sequence.get_queryset().count()

    def test_custom_date_range_walk(self):
        model_sequence = self.build_joined_date_sequence()
        sequence = model_sequence.sequence

        # vanilla (now-8, now-7), past (now-8-3, now-7-3),
        # future (now-8+1, now-7+1)
        for count, shifted_sequence in zip([0, 2, 2, 2, 2], sequence.walk(into_past=3, into_future=2)):
            assert count == shifted_sequence.get_queryset().count()

        # no reason to change after a send...
        sequence.send()
        sequence = Sequence.objects.get(id=model_sequence.id).sequence

        # vanilla (now-8, now-7), past (now-8-3, now-7-3),
        # future (now-8+1, now-7+1)
        for count, shifted_sequence in zip([0, 2, 2, 2, 2], sequence.walk(into_past=3, into_future=2)):
            assert count == shifted_sequence.get_queryset().count()

    def test_custom_sequence_with_count(self):
        model_sequence = self.build_joined_date_sequence()
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="profile__credits",
            lookup_type="gte",
            field_value="5",
        )
        sequence = model_sequence.sequence

        # 1 person meet the criteria
        assert 1 == sequence.get_queryset().count()

        for count, shifted_sequence in zip([0, 1, 1, 1, 1], sequence.walk(into_past=3, into_future=2)):
            assert count == shifted_sequence.get_queryset().count()

    def test_exclude_and_include(self):
        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="profile__credits",
            lookup_type="gte",
            field_value="1",
        )
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="profile__credits",
            method_type="exclude",
            lookup_type="exact",
            field_value=100,
        )
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="profile__credits",
            method_type="exclude",
            lookup_type="exact",
            field_value=125,
        )
        # 7 people meet the criteria
        assert 7 == model_sequence.sequence.get_queryset().count()

    def test_custom_sequence_static_datetime(self):
        model_sequence = self.build_joined_date_sequence()
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="lte",
            field_value=(timezone.now() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S"),
        )
        sequence = model_sequence.sequence

        for count, shifted_sequence in zip([0, 2, 2, 0, 0], sequence.walk(into_past=3, into_future=2)):
            assert count == shifted_sequence.get_queryset().count()

    def test_custom_sequence_static_now_datetime(self):
        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="gte",
            field_value=(timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
        )
        sequence = model_sequence.sequence

        # catches "today and yesterday" users
        for count, shifted_sequence in zip([4, 4, 4, 4, 4], sequence.walk(into_past=3, into_future=3)):
            assert count == shifted_sequence.get_queryset().count()

    def test_admin_timeline_prunes_user_output(self):
        """
        multiple users in timeline is confusing.
        """
        admin = User.objects.create(username="admin", email="admin@example.com")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        # create a sequence campaign that will surely give us duplicates.
        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="gte",
            field_value=(timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
        )

        # then get it's admin view.
        rf = RequestFactory()
        timeline_url = reverse(
            "admin:sequence_timeline",
            kwargs={
                "sequence_id": model_sequence.id,
                "into_past": 3,
                "into_future": 3,
            },
        )

        request = rf.get(timeline_url)
        request.user = admin

        match = resolve(timeline_url)

        response = match.func(request, *match.args, **match.kwargs)

        # check that our admin (not excluded from test) is shown once.
        assert 1 == unicode(response.content).count(admin.email)

    ##################
    #   TEST M2M     #
    ##################

    def test_annotated_field_name_property_no_count(self):
        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )

        qsr = QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="exact",
            field_value=2,
        )
        assert qsr.annotated_field_name == "date_joined"

    def test_annotated_field_name_property_with_count(self):

        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )

        qsr = QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="userprofile__user__groups__count",
            lookup_type="exact",
            field_value=2,
        )
        assert qsr.annotated_field_name == "num_userprofile_user_groups"

    def test_apply_annotations_no_count(self):

        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )

        qsr: QuerySetRule = QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="exact",
            field_value=(timezone.now()).strftime("%Y-%m-%d 00:00:00"),
        )
        base_queryset = model_sequence.sequence.get_queryset()
        qs = qsr.apply_any_annotation(base_queryset)

        assert qs == base_queryset

    def test_apply_annotations_with_count(self):

        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )

        qsr: QuerySetRule = QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="profile__user__groups__count",
            lookup_type="exact",
            field_value=2,
        )

        qs = qsr.apply_any_annotation(model_sequence.sequence.get_queryset())
        assert list(qs.query.annotation_select.keys()) == ["num_profile_user_groups"]  # type: ignore

    def test_apply_multiple_rules_with_aggregation(self):

        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )

        qsr = QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="profile__user__groups__count",
            lookup_type="exact",
            field_value="0",
        )

        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="gte",
            field_value=(timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
        )

        qsr.clean()
        qs = model_sequence.sequence.apply_queryset_rules(model_sequence.sequence.get_queryset())
        assert qs.count() == 4

    def test_apply_and_or_queryset_ruletype(self):

        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )

        qsr = QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="profile__user__groups__count",
            lookup_type="exact",
            field_value="0",
        )

        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="gte",
            field_value=(timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
            rule_type="or",
        )

        qsr.clean()
        qs = model_sequence.sequence.apply_queryset_rules(model_sequence.sequence.get_queryset())

        assert qs.count() == 20

    def test_apply_or_queryset_ruletype(self):

        model_sequence = Sequence.objects.create(
            name="A Custom Week Ago",
            subject_template="HELLO {{ user.username }}",
            body_html_template="KETTEHS ROCK!",
        )

        # returns 9 entries
        qsr = QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="profile__credits",
            lookup_type="gte",
            field_value="5",
            rule_type="or",
        )
        # returns 4 entries
        QuerySetRule.objects.create(
            sequence=model_sequence,
            field_name="date_joined",
            lookup_type="gte",
            field_value=(timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
            rule_type="or",
        )
        qsr.clean()
        qs = model_sequence.sequence.apply_queryset_rules(model_sequence.sequence.get_queryset())

        assert qs.count() == 12

    @pytest.mark.parametrize(
        "message_class_config, lenght_plus, default_class, custom_class",
        (
            (
                {"non-default-class": "email_sequences.sequences.OtherSequenceClass"},
                1,
                DEFAULT_SEQUENCE_MESSAGE_CLASS,
                None,
            ),  # adding a brand new MessageClass
            (
                {"default": "email_sequences.sequences.OtherSequenceClass"},
                0,
                "email_sequences.sequences.OtherSequenceClass",
                None,
            ),  # Replacing an existing Message Class
            (
                {
                    "default": "email_sequences.sequences.OtherSequenceClass",
                    "custom": "custom.module.ClassName",
                },
                1,
                "email_sequences.sequences.OtherSequenceClass",
                "custom.module.ClassName",
            ),  # Mixing replacing and adding a new class
        ),
    )
    def test_message_class_for(
        self,
        message_class_config: Dict[str, str],
        lenght_plus: int,
        default_class: str,
        custom_class: Optional[str],
    ):
        setattr(
            settings,
            "SEQUENCE_MESSAGE_CLASSES",
            message_class_config,
        )

        message_classes = configured_message_classes()

        assert len(message_classes.items()) == DEFAULT_MESSAGE_CLASSES_LENGTH + lenght_plus
        assert message_classes["default"] == default_class
        if custom_class:
            assert message_classes["custom"] == custom_class

    @pytest.mark.parametrize(
        "sequence_unsubscribe_users, expected_context_keys",
        (
            (
                True,
                {
                    "user",
                    "unsubscribe_link_sequence",
                    "unsubscribe_link_campaign",
                },
            ),  # Unsubscribe users is enabled, it should have user and unsubscribe link config key (sequence and campaign)
            (
                False,
                {
                    "user",
                },
            ),  # Unsubscribe users is disabled, it should have user key only
        ),
    )
    def test_sequence_message_build_context(self, sequence_unsubscribe_users: bool, expected_context_keys: set):
        # SEQUENCE_UNSUBSCRIBE_USERS config
        setattr(
            settings,
            "SEQUENCE_UNSUBSCRIBE_USERS",
            sequence_unsubscribe_users,
        )
        model_sequence = self.build_joined_date_sequence()
        sequence = model_sequence.sequence
        user = User.objects.first()
        sequence_message = message_class_for(  # type: ignore
            model_sequence.message_class,
        )(sequence, user)
        context = sequence_message.build_context()
        assert expected_context_keys.issubset(context)


class UrlsTestCase(TestCase):
    def test_sequence_timeline_url(self):
        timeline_url = reverse(
            "admin:sequence_timeline",
            kwargs={
                "sequence_id": 1,
                "into_past": 2,
                "into_future": 3,
            },
        )

        assert timeline_url == "/admin/email_sequences/sequence/1/timeline/2/3/"

    def test_view_sequence_email_url(self):
        view_sequence_email_url = reverse(
            "admin:view_sequence_email",
            kwargs={
                "sequence_id": 1,
                "into_past": 2,
                "into_future": 3,
                "user_id": 4,
            },
        )

        assert view_sequence_email_url == "/admin/email_sequences/sequence/1/timeline/2/3/4/"

    @patch("email_sequences.admin.get_user_model", new=get_user_model_mock)
    def test_sequence_timeline_url_user_uuid(self):
        test_admin = SequenceAdmin(model=Sequence, admin_site=AdminSite())
        new_urls = test_admin.get_urls()
        test_url_pattern = None
        for url_pattern in new_urls:
            if url_pattern.name == "view_sequence_email":
                test_url_pattern = url_pattern
                break
        assert test_url_pattern is not None
        assert (
            test_url_pattern.pattern._route  # type: ignore
            == "<int:sequence_id>/timeline/<int:into_past>/<int:into_future>/<uuid:user_id>/"
        )


class TestSendSequencesCommand(SetupDataSequenceMixin):
    @pytest.mark.parametrize(
        "build_users, model_sequence_enabled, sent_email_count, sequence_count_queryset",
        (
            (True, True, 2, 2),  # Sucess case, the command send sequences to users.
            (False, True, 0, 0),  # No users at all, enabled sequence.
            (True, False, 0, 2),  # Disabled sequence, the command will not get this sequence
            (False, False, 0, 0),  # No users at all, disabled sequence.
        ),
    )
    def test_send_sequences_command(
        self, build_users: bool, model_sequence_enabled: bool, sent_email_count: int, sequence_count_queryset: int
    ):
        if build_users:
            self.build_user_data()
        model_sequence = self.build_joined_date_sequence()
        model_sequence.enabled = model_sequence_enabled
        model_sequence.save()

        call_command("send_sequences")

        assert sent_email_count == SentEmail.objects.count()
        model_sequence.refresh_from_db()
        sequence = model_sequence.sequence
        assert sequence_count_queryset == sequence.get_queryset().count()


class TestFormAdminSequence:
    @pytest.mark.parametrize(
        "sequence_unsubscribe_users, has_changed_help_text",
        (
            (True, True),  # Unsubscribe users is enabled, it should change the help text in form
            (False, False),  # Unsubscribe users is disabled, it should NOT change the help text in form
        ),
    )
    def test_form_body_html_template(self, sequence_unsubscribe_users: bool, has_changed_help_text: bool):
        # SEQUENCE_UNSUBSCRIBE_USERS config
        setattr(
            settings,
            "SEQUENCE_UNSUBSCRIBE_USERS",
            sequence_unsubscribe_users,
        )
        form = SequenceForm()
        default_help_text = Sequence._meta.get_field("body_html_template").help_text
        form_help_text = form.fields["body_html_template"].help_text
        assert not (form_help_text == default_help_text) == has_changed_help_text
