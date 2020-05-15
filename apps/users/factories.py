import factory

from apps.users.models import Department


class DepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Department

    name = factory.Faker('job')
    parent = None
