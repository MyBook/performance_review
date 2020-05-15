import logging

from asciitree import LeftAligned, DictTraversal
from django.core.management import BaseCommand

from apps.users.tree import get_people_tree

logger = logging.getLogger(__name__)


class HRTraversal(DictTraversal):
    def get_text(self, node):
        prefix = '[X] ' if not node[0].is_reviewable else ''
        return f'{prefix}{node[0].hr_friendly_name}'


class Command(BaseCommand):
    help = 'Print ascii tree of perf review participants (for HR and sharing)'

    def handle(self, *args, **options):
        for tree in get_people_tree():
            self.stdout.write(LeftAligned(traverse=HRTraversal())(tree))
