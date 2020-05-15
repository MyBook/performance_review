import datetime
import logging

from dateutil.parser import parse as parse_date
from django.core.management import BaseCommand, CommandError
from django.template.loader import render_to_string

from apps.reviews.emails import PerfEmailMessage, WelcomeMessage
from apps.reviews.models import Review, Interval
from apps.users.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    python manage.py send_email --template=welcome --email=foo@example.com
    """
    help = 'Send email'
    templates = {'welcome', 'request_feedback'}

    def add_arguments(self, parser):
        parser.add_argument('--template')
        parser.add_argument('--email')
        parser.add_argument('--department')
        parser.add_argument('--suitable', action='store_true')
        parser.add_argument('--deadline')

    def handle(self, *args, **options):
        if not options['template']:
            raise CommandError('Specify which template to send, supported are: [welcome, request_feedback].')
        if not options['email'] and not options['suitable']:
            raise CommandError('Specify recipient email, e.g. --email=xxx@localhost, '
                               'or send to everybody via --suitable')
        if options['template'] in self.templates:
            base_context = {
                'deadline': (parse_date(options['deadline'])
                             if options['deadline'] else datetime.datetime.now() + datetime.timedelta(days=2)),
            }
            if options['email']:
                users = list(User.active.filter(email=options['email']))
            elif options['suitable']:
                users = getattr(self, f"get_audience_{options['template']}")(interval=Interval.started.first(),
                                                                             department=options['department'])
            for user in users:
                try:
                    getattr(self, f"handle_{options['template']}")(context={'user': user, **base_context})
                    self.stdout.write(f"Sent {options['template']} to {user.email}")
                except Exception as e:
                    self.stderr.write(str(e))
                    logger.error('Sending email failed %s to %s', user.email, options['template'], exc_info=True)
        else:
            raise CommandError(f"Unsupported template {options['template']}")

    def get_audience_welcome(self, interval, department):
        users = User.active.filter(is_reviewable=True)
        if department:
            users = users.filter(department__name=department)
        return users

    def get_audience_request_feedback(self, interval, department):
        return {r.reviewer for r in Review.visible_to_reviewer.filter(
            target__selfreview__status='published',
            target__selfreview__interval=interval,
            interval=interval
        ).filter(
            status__in=(Review.STATUS.draft, Review.STATUS.rejected)) if r.reviewer.is_active}

    def handle_welcome(self, context):
        WelcomeMessage(context=context).send(to=[context['user'].email])

    def handle_request_feedback(self, user, context):
        context = {
            'subject': f'[ACTION REQUIRED] Прошу тебя оценить работу коллег до {context["deadline"]:%d.%m.%Y}',
            'current_reviews': Review.objects.waiting_from_user(
                user=context['user'],
                interval=context['current_interval']).filter(
                    status__in=(Review.STATUS.draft, Review.STATUS.rejected)),
            **context
        }
        request_feedback_html = render_to_string('email/request_feedback.html', context=context)
        PerfEmailMessage(context=dict(context, inner_html=request_feedback_html)).send(
            to=[user.email])
