import factory

from apps.goals.models import Goal
from apps.reviews.factories import IntervalFactory, UserFactory


class GoalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Goal

    interval = factory.SubFactory(IntervalFactory)
    target = factory.SubFactory(UserFactory)
