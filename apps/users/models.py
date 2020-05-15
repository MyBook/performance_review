from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from model_utils.managers import QueryManagerMixin
from model_utils.models import TimeStampedModel


class QueryUserManager(QueryManagerMixin, UserManager):
    pass


class User(AbstractUser):
    name = models.CharField(_('Name of User'), blank=True, max_length=255)
    avatar = models.ImageField(null=True, blank=True)
    job = models.ForeignKey('reviews.Job', null=True, on_delete=models.SET_NULL,
                            verbose_name=_('Должность'))
    manager = models.ForeignKey('self', related_name='subordinates', null=True,
                                on_delete=models.SET_NULL, blank=True,
                                limit_choices_to={'is_active': True},)
    is_reviewable = models.BooleanField(default=True,
                                        help_text='Пишет self-review и получает обратную связь')
    department = models.ForeignKey('users.Department', null=True,
                                   on_delete=models.SET_NULL, blank=True, verbose_name=_('Отдел'))

    objects = QueryUserManager()
    active = QueryUserManager(is_active=True)
    reviewable = QueryUserManager(is_reviewable=True)

    class Meta:
        unique_together = ('email',)
        ordering = ['last_name', 'first_name', 'email']

    def __str__(self):
        return f'{self.last_name} {self.first_name}'.strip() if (self.last_name or self.first_name) else self.email

    @property
    def hr_friendly_name(self):
        return f'{str(self)} ({self.job.name})'

    def get_absolute_url(self, interval=None):
        if not interval:
            from apps.reviews.models import Interval
            interval = Interval.started.first()
        if not self.is_active:  # avoid 500 for system user (e.g. django, with no email)
            return False
        return reverse('users:detail', kwargs={'email': self.email, 'interval': interval})

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/images/owl.png'

    @property
    def is_boss(self):
        return self.manager is None


class Department(TimeStampedModel):
    name = models.CharField(max_length=128)
    parent = models.ForeignKey('self', related_name='subdepartments', null=True,
                               on_delete=models.SET_NULL, blank=True,)
    weight = models.IntegerField(default=0)

    class Meta:
        verbose_name = _('Отдел')
        verbose_name_plural = _('Отделы')
        ordering = ['weight', 'name']

    def __str__(self):
        return self.name
