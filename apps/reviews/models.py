import logging

from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices, FieldTracker
from model_utils.fields import StatusField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel, StatusModel

from apps.users.models import User

logger = logging.getLogger(__name__)


class IntervalQueryManager(QueryManager):

    def current(self):
        return self.first()


class Interval(TimeStampedModel, StatusModel):
    STATUS = Choices('pending', 'started', 'finished')
    name = models.CharField(max_length=10)

    objects = QueryManager()
    active = IntervalQueryManager(status__in=(STATUS.started, STATUS.finished))

    class Meta:
        verbose_name = _('Квартал')
        verbose_name_plural = _('Кварталы')
        ordering = ['-name']
        get_latest_by = 'name'

    def __str__(self):
        return self.name

    def get_next(self):
        """This is not real implementation"""
        return Interval.objects.filter(status='pending').exclude(id=self.id).first()


class Job(TimeStampedModel):
    name = models.CharField(max_length=128)

    class Meta:
        verbose_name = _('Должность')
        verbose_name_plural = _('Должности')

    def __str__(self):
        return self.name


class Role(TimeStampedModel):
    name = models.CharField(max_length=128)
    expectations = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Роль')
        verbose_name_plural = _('Роли')

    def __str__(self):
        return self.name


class SelfReview(TimeStampedModel, StatusModel):
    STATUS = Choices(('draft', 'Черновик'),
                     ('rejected', 'Требует доработки'),
                     ('pending', 'Ожидает одобрения менеджера'),
                     ('published', 'Готово'))
    interval = models.ForeignKey(Interval, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    text = models.TextField()
    comment = models.TextField(blank=True)
    status = StatusField(_('status'))

    tracker = FieldTracker()

    class Meta:
        verbose_name = _('Self-review')
        verbose_name_plural = _('Self-review')
        unique_together = ('interval', 'user')

    def __str__(self):
        return f'Self-review {self.user} за {self.interval} [{self.status}]'

    def save(self, **kwargs):
        if self.tracker.has_changed('status') and self.status == SelfReview.STATUS.published:
            # prevent requested reviews from deletion, by making them draft
            # do not use update, so that signal triggers email
            for review in Review.requested.filter(target=self.user, interval=self.interval):
                review.status = Review.STATUS.draft
                review.save(update_fields=['status'])
        super().save(**kwargs)

    def get_absolute_url(self):
        return reverse('reviews:self-review', kwargs={
            'interval': self.interval.name,
            'pk': self.id
        })

    @property
    def status_human(self):
        return self.STATUS[self.status]

    @property
    def is_editable(self):
        return self.status in {self.STATUS.draft, self.STATUS.rejected}

    @property
    def is_rejected(self):
        return self.status == self.STATUS.rejected

    @property
    def is_pending(self):
        return self.status == self.STATUS.pending

    @property
    def is_published(self):
        return self.status == self.STATUS.published

    def is_visible_to(self, user):
        """
        Author sees own self-review at all times.
        Manager sees subordinate self-review while it's on moderation or is published.
        """
        if self.user == user:
            return True
        if self.user.manager == user:
            return self.status in {self.STATUS.rejected, self.STATUS.pending, self.STATUS.published}


class ReviewQueryManager(models.Manager):

    def waiting_from_user(self, *, user, interval):
        return self.model.visible_to_reviewer.filter(
            interval=interval,
            reviewer=user,
            target__selfreview__status='published',
            target__selfreview__interval=interval,
        ).exclude(status__in=(Review.STATUS.hidden, Review.STATUS.published))


class Review(TimeStampedModel, StatusModel):
    STATUS = Choices(
        ('requested', 'Запросил'),  # created by target
        ('draft', 'Черновик'),  # approved by manager when self-review is approved
        ('rejected', 'Требует доработки'),
        ('pending', 'Ожидает одобрения менеджера'),
        ('hidden', 'Скрыт от сотрудника'),
        ('published', 'Виден сотруднику')  # not used
    )
    SCORES = Choices(
        ('5', 'Сильно превышает ожидания'),
        ('4', 'Превышает ожидания'),
        ('3', 'Соответствует ожиданиям'),
        ('2', 'Ниже ожиданий'),
        ('1', 'Сильно ниже ожиданий'),
        ('-', 'Не взаимодействовал, оценить не могу'),
    )

    interval = models.ForeignKey(Interval, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(User, related_name='responses', on_delete=models.PROTECT)
    target = models.ForeignKey(User, related_name='reviews', on_delete=models.PROTECT)
    status = StatusField(_('status'), default=STATUS.draft)
    text = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    score = models.CharField(choices=SCORES, max_length=2, null=True, blank=True)

    tracker = FieldTracker()

    objects = ReviewQueryManager()
    visible_to_reviewer = QueryManager(status__in=(STATUS.draft, STATUS.rejected,
                                                   STATUS.pending, STATUS.published, STATUS.hidden))
    visible_to_manager = QueryManager(status__in=(STATUS.rejected, STATUS.pending, STATUS.published, STATUS.hidden))
    require_approval = QueryManager(status__in=(STATUS.rejected, STATUS.pending))
    approved = QueryManager(status__in=(STATUS.published, STATUS.hidden))

    class Meta:
        verbose_name = _('Оценка')
        verbose_name_plural = _('Оценки')

    def __str__(self):
        return f'{self.reviewer} -> {self.target} ({self.interval})'

    def get_absolute_url(self):
        return reverse('reviews:reviews-detail', kwargs={'pk': self.pk, 'interval': self.interval})

    @property
    def status_human(self):
        return self.STATUS[self.status]

    @property
    def is_rejected(self):
        return self.status == self.STATUS.rejected

    @property
    def is_editable(self):
        return self.status in {self.STATUS.draft, self.STATUS.rejected}

    @property
    def is_pending(self):
        return self.status == self.STATUS.pending

    @property
    def is_subordinate_review(self):
        return self.target.manager == self.reviewer

    def is_visible_to(self, user):
        """
        Reviewer sees review to be scored/commented if review passed requested status,
        e.g. manager approved requested -> draft.
        Manager sees all subordinate reviews in any status.
        Employee sees only published reviews (status hidden is not visible).

        NB: No review is visible if no self-review, or self-review is not published
        """
        current_self_review = SelfReview.objects.filter(user=self.target,
                                                        interval=self.interval).first()
        if not current_self_review:
            logger.info(f"Can't review without selfreview review_id={self.id}, request_user_id={user.id}")
            return False
        if not current_self_review.is_published:
            logger.info(f'Selfreview {current_self_review.id} is not published status={current_self_review.status},'
                        f'access denied for request_user_id={user.id}')
            return False

        if self.reviewer == user:
            return self.status != self.STATUS.requested
        if self.target.manager == user:
            return True
        if self.target == user:
            return self.status == self.STATUS.published


