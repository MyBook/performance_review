from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from templated_mail.mail import BaseEmailMessage

from apps.reviews.models import Interval
from apps.users.log import log_object_action


class PerfEmailMessage(BaseEmailMessage):
    template_name = 'email/base.html'
    inner_template_name = NotImplemented
    email_subject = NotImplemented

    def get_context_data(self):
        context = super().get_context_data()
        context['domain'] = Site.objects.get_current().domain
        context['current_interval'] = Interval.started.first()
        context['support_email'] = settings.CONTENT_SUPPORT_EMAIL
        context['email_signature'] = settings.CONTENT_EMAIL_SIGNATURE
        inner_html = render_to_string(self.inner_template_name, context=context)
        context['inner_html'] = inner_html
        context['subject'] = self.get_subject(context)
        return context

    def get_subject(self, context):
        return self.email_subject

    def send(self, to, *args, **kwargs):
        super(PerfEmailMessage, self).send(to, *args, **kwargs)
        log_object_action(self.context['user'], f'Отправлено письмо {self.inner_template_name}')


class WelcomeMessage(PerfEmailMessage):
    inner_template_name = 'email/welcome.html'
    email_subject = '[ACTION REQUIRED] Наступает супер-время performance review'


class SelfreviewPendingMessage(PerfEmailMessage):
    inner_template_name = 'email/selfreview_pending.html'

    def get_subject(self, context):
        return f"{context['selfreview'].user} написал self-review"


class SelfreviewRejectedMessage(PerfEmailMessage):
    inner_template_name = 'email/selfreview_rejected.html'

    def get_subject(self, context):
        return f"Ваш self-review нужно доработать"


class SelfreviewPublishedMessage(PerfEmailMessage):
    inner_template_name = 'email/selfreview_published.html'

    def get_subject(self, context):
        return f"👍 твой self-review проверил {context['selfreview'].user.manager}"


class ReviewDraftMessage(PerfEmailMessage):
    inner_template_name = 'email/review_draft.html'

    def get_subject(self, context):
        return f"Прошу тебя оценить работу {context['review'].target} в {context['review'].interval}"


class ReviewPendingMessage(PerfEmailMessage):
    inner_template_name = 'email/review_pending.html'

    def get_subject(self, context):
        return f"Требует проверки фидбэк {context['review'].reviewer} → {context['review'].target} ({context['review'].get_score_display()})"


class ReviewRejectedMessage(PerfEmailMessage):
    inner_template_name = 'email/review_rejected.html'

    def get_subject(self, context):
        return f"Требует доработки твой фидбэк на {context['review'].target} ({context['review'].get_score_display()})"
