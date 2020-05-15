import logging

from braces.views import UserFormKwargsMixin
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.utils.safestring import mark_safe
from django.views.generic import UpdateView, CreateView

from apps.goals.forms import GoalForm
from apps.goals.models import Goal
from apps.reviews.models import Interval
from apps.users.models import User

logger = logging.getLogger(__name__)


class SelfReviewContextMixin(SuccessMessageMixin):
    model = Goal
    form_class = GoalForm
    template_name = 'goals/goal_detail.html'
    success_message = 'Цели %(target)s на %(interval)s сохранены'

    def dispatch(self, request, *args, **kwargs):
        self.current_interval = Interval.objects.get(name=self.kwargs['interval'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super(SelfReviewContextMixin, self).get_context_data(**kwargs)
        context_data['current_interval'] = self.current_interval
        return context_data

    def get_initial(self):
        return {
            'interval': self.current_interval,
        }

    def get_success_url(self):
        return self.object.target.get_absolute_url(interval=self.current_interval)

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, mark_safe(
            '<h4 class="alert-heading">Ошибки при заполнении формы</h4>%s' % form.errors))
        return response


class CreateGoal(SelfReviewContextMixin, CreateView):
    """
    Assign goal for subordinate
    """

    def dispatch(self, request, *args, **kwargs):
        self.target = User.active.get(email=self.kwargs['email'])
        if self.request.user == self.target.manager:
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.target})
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super(CreateGoal, self).get_context_data(**kwargs)
        context_data['target'] = self.target
        context_data['is_editable'] = True
        context_data['goal_form'] = GoalForm(**self.get_form_kwargs())
        context_data['manager'] = self.request.user
        previous_goal = Goal.objects.filter(target=self.target).last()
        context_data['previous_goal'] = previous_goal
        return context_data


class EditGoal(UserFormKwargsMixin, SelfReviewContextMixin, UpdateView):
    """
    Edit existing subordinate goal
    """
    def get_object(self, queryset=None):
        object = Goal.objects.get(id=self.kwargs['pk'])
        if self.request.method == 'POST' and not object.is_editable_by(self.request.user):
            raise PermissionDenied
        if object.is_visible_to(self.request.user):
            return object
        if self.request.user.has_perm('goals.view_any_goal'):
            messages.warning(self.request, 'Страница видна вам, т.к. у вас есть право view_any_goal')
            return object
        raise PermissionDenied

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.object.target})
        return kwargs

    def get_context_data(self, **kwargs):
        context_data = super(EditGoal, self).get_context_data(**kwargs)
        context_data['target'] = self.object.target
        context_data['goal_form'] = GoalForm(**self.get_form_kwargs())
        context_data['is_editable'] = self.request.user == self.object.target.manager
        context_data['manager'] = self.object.target.manager
        previous_goal = Goal.objects.filter(target=self.object.target).filter(pk__lt=self.object.pk).last()
        context_data['previous_goal'] = previous_goal
        return context_data
