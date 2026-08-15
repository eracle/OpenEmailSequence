from collections import OrderedDict
from typing import Callable, List, Set, Union

from django.contrib import admin
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import URLPattern, path

from email_sequences.models import Campaign, Sequence
from email_sequences.utils import get_user_model

User = get_user_model()


class SequenceInline(admin.TabularInline):
    model = Sequence


class CampaignAdmin(admin.ModelAdmin):
    inlines = [
        SequenceInline,
    ]
    users_fields: Union[str, List[str]] = []

    def av(self, view: Callable) -> Callable:
        return self.admin_site.admin_view(view)

    def timeline(
        self,
        request: WSGIRequest,
        sequence_id: int,
        into_past: int,
        into_future: int,
    ) -> HttpResponse:
        """
        Return a list of people who should get emails.
        """

        campaign = get_object_or_404(Campaign, id=sequence_id)
        new_shifted_sequences = OrderedDict()
        for shift in range(-into_past, into_future + 1):
            new_shifted_sequences[shift] = {"sequences": [], "now_shift_kwargs_days": shift}
        for sequence in campaign.sequence_set.all():
            seen_users: Set[int] = set()
            for shifted_sequence in sequence.sequence.walk(into_past=int(into_past), into_future=int(into_future) + 1):
                shifted_sequence.prune()
                shifted_data = {
                    "sequence_model": sequence,
                    "sequence": shifted_sequence,
                    "qs": shifted_sequence.get_queryset().exclude(
                        id__in=seen_users,
                    ),
                }
                if not sequence.can_resend_sequence:
                    seen_users.update(shifted_sequence.get_queryset().values_list("id", flat=True))
                shift_days = shifted_sequence.now_shift_kwargs.get("days")
                if shift_days is not None:
                    new_shifted_sequences[shift_days]["sequences"].append(shifted_data)  # type: ignore
                    new_shifted_sequences[shift_days]["now"] = shifted_sequence.now()

        return render(request, "email_sequences/campaign_timeline.html", locals())

    def get_urls(self) -> List[URLPattern]:
        urls = super(CampaignAdmin, self).get_urls()
        my_urls = [
            path(
                "<int:sequence_id>/timeline/<int:into_past>/<int:into_future>/",
                self.av(self.timeline),
                name="campaign_sequence_timeline",
            ),
        ]

        return my_urls + urls
