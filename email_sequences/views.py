from typing import Any, Dict, List

from django.views.generic import TemplateView

from email_sequences.models import UserUnsubscribe
from email_sequences.tokens import EmailToken


class UnsubscribeSequenceView(TemplateView):
    template_name = "email_sequences/unsubscribe_sequence.html"
    invalid_template_name = "email_sequences/unsubscribe_sequence_invalid.html"
    success_template_name = "email_sequences/unsubscribe_sequence_success.html"

    def _set_user_and_sequence(self, **kwargs: Any):
        sequence_uidb64 = kwargs.get("sequence_uidb64", "")
        uidb64 = kwargs.get("uidb64", "")
        token = kwargs.get("token", "")
        self.user = EmailToken.validate_user_uidb64_token(uidb64, token)
        self.sequence = EmailToken.validate_sequence_uidb64(sequence_uidb64)
        self.post_sucess = False

    def dispatch(self, *args: Any, **kwargs: Any):
        self._set_user_and_sequence(**kwargs)
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["user"] = self.user
        context_data["sequence"] = self.sequence
        return context_data

    def get_template_names(self) -> List[str]:
        if not (self.user and self.sequence):
            return [self.invalid_template_name]
        if self.user and self.sequence and self.post_sucess:
            return [self.success_template_name]
        return super().get_template_names()

    def post(self, *args: Any, **kwargs: Any):
        context = self.get_context_data(**kwargs)
        if self.user and self.sequence:
            self.sequence.unsubscribed_users.add(self.user.pk)
            self.post_sucess = True
        return self.render_to_response(context)


class UnsubscribeCampaignView(TemplateView):
    template_name = "email_sequences/unsubscribe_campaign.html"
    invalid_template_name = "email_sequences/unsubscribe_campaign_invalid.html"
    success_template_name = "email_sequences/unsubscribe_campaign_success.html"

    def _set_user_and_campaign(self, **kwargs: Any):
        campaign_uidb64 = kwargs.get("campaign_uidb64", "")
        uidb64 = kwargs.get("uidb64", "")
        token = kwargs.get("token", "")
        self.user = EmailToken.validate_user_uidb64_token(uidb64, token)
        self.campaign = EmailToken.validate_campaign_uidb64(campaign_uidb64)
        self.post_sucess = False

    def dispatch(self, *args: Any, **kwargs: Any):
        self._set_user_and_campaign(**kwargs)
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["user"] = self.user
        context_data["campaign"] = self.campaign
        return context_data

    def get_template_names(self) -> List[str]:
        if not (self.user and self.campaign):
            return [self.invalid_template_name]
        if self.user and self.campaign and self.post_sucess:
            return [self.success_template_name]
        return super().get_template_names()

    def post(self, *args: Any, **kwargs: Any):
        context = self.get_context_data(**kwargs)
        if self.user and self.campaign:
            self.campaign.unsubscribed_users.add(self.user.pk)
            self.post_sucess = True
        return self.render_to_response(context)


class UnsubscribeView(TemplateView):
    template_name = "email_sequences/unsubscribe_general.html"
    invalid_template_name = "email_sequences/unsubscribe_general_invalid.html"
    success_template_name = "email_sequences/unsubscribe_general_success.html"

    def _set_user(self, **kwargs: Any):
        uidb64 = kwargs.get("uidb64", "")
        token = kwargs.get("token", "")
        self.user = EmailToken.validate_user_uidb64_token(uidb64, token)
        self.post_sucess = False

    def dispatch(self, *args: Any, **kwargs: Any):
        self._set_user(**kwargs)
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["user"] = self.user
        return context_data

    def get_template_names(self) -> List[str]:
        if not self.user:
            return [self.invalid_template_name]
        if self.user and self.post_sucess:
            return [self.success_template_name]
        return super().get_template_names()

    def post(self, *args: Any, **kwargs: Any):
        context = self.get_context_data(**kwargs)
        if self.user:
            UserUnsubscribe.objects.create(user=self.user)  # type: ignore
            self.post_sucess = True
        return self.render_to_response(context)
