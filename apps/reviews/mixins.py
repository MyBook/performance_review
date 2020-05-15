from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy

from apps.reviews.models import Interval


class CurrentIntervalMixin(LoginRequiredMixin):
    """
    Populate current_interval view attribute and context_data variable
    Populate interval variable in form initial data
    """
    def dispatch(self, request, *args, **kwargs):
        self.current_interval = Interval.started.first()
        if not self.current_interval:
            raise PermissionDenied('Нет активного MPR, нельзя написать self-review')

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            'interval': self.current_interval
        }

    def get_success_url(self):
        return reverse_lazy('users:redirect')

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_interval'] = self.current_interval
        return context_data
