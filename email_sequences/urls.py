from django.conf import settings
from django.urls import re_path

from email_sequences.views import UnsubscribeCampaignView, UnsubscribeSequenceView, UnsubscribeView

urlpatterns = []

if getattr(settings, "SEQUENCE_UNSUBSCRIBE_USERS", False):
    urlpatterns += [
        re_path(
            r"^sequence/(?P<sequence_uidb64>\w+)/(?P<uidb64>\w+)/(?P<token>[\w-]+)/$",
            UnsubscribeSequenceView.as_view(),
            name="unsubscribe_sequence",
        ),
        re_path(
            r"^campaign/(?P<campaign_uidb64>\w+)/(?P<uidb64>\w+)/(?P<token>[\w-]+)/$",
            UnsubscribeCampaignView.as_view(),
            name="unsubscribe_campaign",
        ),
        re_path(
            r"^app/(?P<uidb64>\w+)/(?P<token>[\w-]+)/$",
            UnsubscribeView.as_view(),
            name="unsubscribe_app",
        ),
    ]
