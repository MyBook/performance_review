import factory

from apps.reviews.models import Job, Interval, Review, SelfReview
from apps.users.factories import DepartmentFactory
from apps.users.models import User


class JobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Job

    name = factory.Faker('job')


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    email = factory.Faker('email')
    username = factory.SelfAttribute('email')
    job = factory.SubFactory(JobFactory)
    department = factory.SubFactory(DepartmentFactory)
    manager = None

    @factory.post_generation
    def with_manager(obj, create, extracted, **kwargs):
        if extracted:
            obj.manager = UserFactory(**kwargs)
            obj.save()


class IntervalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Interval

    class Params:
        started = factory.Trait(status=Interval.STATUS.started)
        pending = factory.Trait(status=Interval.STATUS.pending)
        finished = factory.Trait(status=Interval.STATUS.finished)

    name = factory.Sequence(lambda n: '2018Q%s' % n)


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    interval = factory.SubFactory(IntervalFactory)
    reviewer = factory.SubFactory(UserFactory)
    target = factory.SubFactory(UserFactory)

    class Params:
        requested = factory.Trait(status=Review.STATUS.requested)
        draft = factory.Trait(status=Review.STATUS.draft)
        pending = factory.Trait(status=Review.STATUS.pending)
        rejected = factory.Trait(status=Review.STATUS.rejected)
        published = factory.Trait(status=Review.STATUS.published)
        hidden = factory.Trait(status=Review.STATUS.hidden)


class SelfReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SelfReview

    interval = factory.SubFactory(IntervalFactory)
    user = factory.SubFactory(UserFactory)

    class Params:
        draft = factory.Trait(status=SelfReview.STATUS.draft)
        published = factory.Trait(status=SelfReview.STATUS.published)
        pending = factory.Trait(status=SelfReview.STATUS.pending)
        rejected = factory.Trait(status=SelfReview.STATUS.rejected)
