# tests/test_mail_log_backfill.py
"""The conversation table becomes the mail log without losing a turn.

Run against the real migration graph rather than the current models, because
that is the only place the question lives: an install upgrading into this design
has years of ``ChatMessage`` rows and must come out the other side with the same
conversations, threaded, and its deals pointing at them.
"""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

BEFORE = [
    ("emails", "0007_deliveryevent_foldercoverage_message_thread_and_more"),
    ("crm", "0021_remove_deal_email_message_id_deal_thread"),
    ("chat", "0005_alter_chatmessage_external_id"),
]
AFTER = [
    ("emails", "0008_backfill_mail_log"),
    ("chat", "0006_remove_chatmessage_uniq_deal_external_id_and_more"),
]


def _migrate(targets):
    """Move the test database to *targets* and return the resulting model state."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor.loader.project_state(targets).apps


@pytest.fixture
def at_the_seam(django_db_setup, django_db_blocker):
    """The schema one migration before the log exists, and back to head afterwards."""
    with django_db_blocker.unblock():
        yield _migrate(BEFORE)
        _migrate(AFTER)


@pytest.mark.django_db(transaction=True)
def test_a_conversation_survives_the_move(at_the_seam, django_db_blocker):
    old = at_the_seam
    Campaign = old.get_model("core", "Campaign")
    Deal = old.get_model("crm", "Deal")
    Lead = old.get_model("crm", "Lead")
    Mailbox = old.get_model("emails", "Mailbox")
    ChatMessage = old.get_model("chat", "ChatMessage")

    with django_db_blocker.unblock():
        campaign = Campaign.objects.create(name="Backfill")
        box = Mailbox.objects.create(username="s@infra.com", password="pw",
                                     from_address="s@infra.com")
        lead = Lead.objects.create(profile_url="https://x/1", email="p@corp.com")
        deal = Deal.objects.create(lead=lead, campaign=campaign, mailbox=box,
                                   state="Emailed", email_subject="Hi")
        now = timezone.now()
        ChatMessage.objects.create(deal=deal, external_id="<root@infra.com>",
                                   content="The opener.", is_outgoing=True,
                                   creation_date=now)
        ChatMessage.objects.create(deal=deal, external_id="<reply@corp.com>",
                                   content="Sure, happy to chat.", is_outgoing=False,
                                   creation_date=now)

        new = _migrate(AFTER)
        Message = new.get_model("emails", "Message")
        moved = new.get_model("crm", "Deal").objects.get(pk=deal.pk)

        assert moved.thread_id is not None
        rows = list(Message.objects.filter(thread_id=moved.thread_id)
                    .order_by("sent_at", "pk"))
        assert [row.message_id for row in rows] == ["root@infra.com", "reply@corp.com"]
        assert [row.direction for row in rows] == ["out", "in"]
        assert [row.kind for row in rows] == ["outbound", "human_reply"]
        assert rows[1].body_text == "Sure, happy to chat."
        # Stamped at the current classifier version: these rows have no bytes, so a
        # re-run must not overwrite a true verdict with a guess.
        assert {row.classifier_version for row in rows} == {1}
