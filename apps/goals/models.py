import logging

from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel, StatusModel

from apps.reviews.models import Interval
from apps.users.models import User

logger = logging.getLogger(__name__)


class Goal(TimeStampedModel):
    interval = models.ForeignKey(Interval, on_delete=models.PROTECT)
    target = models.ForeignKey(User, related_name='goals', on_delete=models.PROTECT)
    text = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Цель')
        verbose_name_plural = _('Цели')
        unique_together = ('interval', 'target')

    def __str__(self):
        return f'Цели {self.target} на {self.interval}'

    def get_absolute_url(self):
        return reverse_lazy('goals:detail', kwargs={'pk': self.pk, 'interval': self.interval})

    def is_visible_to(self, user):
        return user == self.target or self.target.manager == user

    def is_editable_by(self, user):
        return self.target.manager == user

    @staticmethod
    def get_create_url(email, interval):
        return reverse_lazy('goals:create', kwargs={'email': email, 'interval': interval})
