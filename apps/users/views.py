from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, When, Value, IntegerField
from django.urls import reverse
from django.views.generic import DetailView, ListView, RedirectView

from apps.goals.models import Goal
from apps.reviews.models import Interval, SelfReview, Review
from .models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    """
    User profile page
    """
    model = User
    slug_field = 'email'
    slug_url_kwarg = 'email'
    context_object_name = 'user'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        current_interval = Interval.objects.get(name=self.kwargs['interval'])
        next_interval = current_interval.get_next()

        context_data.update({
            'finished_intervals': Interval.finished.all(),
            'user_intervals': Interval.finished.filter(selfreview__user=self.object),
            'manager': self.object.manager,
            'subordinates': self.object.subordinates.filter(is_active=True),
            'current_interval': current_interval,
            'next_interval': next_interval,
            'current_interval_create_goal_url': Goal.get_create_url(email=self.object.email, interval=current_interval),
            'next_interval_create_goal_url': Goal.get_create_url(email=self.object.email, interval=next_interval),
        })
        for interval in context_data['finished_intervals']:
            interval.url = self.object.get_absolute_url(current_interval)

        current_self_review = SelfReview.objects.filter(user=self.object,
                                                        interval=current_interval).first()
        if not current_self_review:
            context_data['current_self_review_url'] = reverse('reviews:create-self-review',
                                                              kwargs={'interval': current_interval})
        else:
            context_data['current_self_review_url'] = current_self_review.get_absolute_url()
        context_data['current_self_review'] = current_self_review

        if self.request.user.has_perm('reviews.view_all_stats') or self.request.user == self.object:
            context_data = self.populate_subordinate_context(context_data)
        if self.request.user.has_perm('reviews.view_any_review') or self.request.user == self.object.manager:
            context_data['summary_url'] = reverse('users:summary', kwargs={'interval': current_interval,
                                                                           'email': self.object.email})

        if (self.request.user.has_perm('goals.view_any_goal')
                or self.request.user == self.object
                or self.request.user == self.object.manager):
            context_data['current_goal'] = Goal.objects.filter(target=self.object, interval=current_interval).first()
            context_data['next_goal'] = Goal.objects.filter(target=self.object, interval=next_interval).first()

        context_data.update({
            'current_peers': User.active.filter(responses__target=self.request.user,
                                                responses__interval=current_interval),
            'draft_reviews': Review.draft.filter(interval=current_interval,
                                                 reviewer=self.request.user,
                                                 target__selfreview__status='published',
                                                 target__selfreview__interval=current_interval),
            'pending_reviews': Review.pending.filter(interval=current_interval,
                                                     reviewer=self.request.user),
            'approved_reviews': Review.approved.filter(interval=current_interval,
                                                       reviewer=self.request.user),
            'rejected_reviews': Review.rejected.filter(interval=current_interval,
                                                       reviewer=self.request.user)
        })

        return context_data

    def populate_subordinate_context(self, context_data):
        for subordinate in context_data['subordinates']:
            subordinate.self_review = SelfReview.objects.filter(
                user=subordinate,
                interval=context_data['current_interval']).first()
            subordinate.peers_approved = [u.reviewer for u in Review.approved.filter(
                target=subordinate,
                interval=context_data['current_interval']
            )]
            subordinate.peers_require_approval = [u.reviewer for u in Review.require_approval.filter(
                target=subordinate,
                interval=context_data['current_interval']
            )]
            subordinate.peers_draft = [u.reviewer for u in Review.draft.filter(
                target=subordinate,
                interval=context_data['current_interval']
            )]
            subordinate.peers = (subordinate.peers_approved
                                 + subordinate.peers_require_approval
                                 + subordinate.peers_draft)
            subordinate.current_written_reviews = Review.visible_to_manager.filter(
                reviewer=subordinate,
                interval=context_data['current_interval']
            )
            subordinate.current_reviews = Review.objects.filter(
                reviewer=subordinate,
                interval=context_data['current_interval']
            )
        return context_data


class UserRedirectView(LoginRequiredMixin, RedirectView):
    """
    Facade for user profile, so that we don't have complex reverse for user profile page
    """
    permanent = False

    def get_redirect_url(self):
        return reverse('users:detail', kwargs={
            'email': self.request.user.email,
            'interval': Interval.active.current()})


class UserListView(LoginRequiredMixin, ListView):
    """
    User list view
    """
    model = User
    slug_field = 'email'
    slug_url_kwarg = 'email'


class SummaryView(LoginRequiredMixin, DetailView):
    """
    All user reviews
    """
    template_name = 'users/summary.html'
    model = User
    slug_field = 'email'
    slug_url_kwarg = 'email'
    context_object_name = 'user'

    def get_object(self, queryset=None):
        object = super().get_object(queryset=queryset)
        if object.manager == self.request.user:
            return object
        if self.request.user.has_perm('reviews.view_any_review'):
            messages.warning(self.request, 'Страница видна вам, т.к. у вас есть право view_any_review')
            return object
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context_data = super(SummaryView, self).get_context_data(**kwargs)
        self_review = SelfReview.objects.filter(
            user=self.object,
            interval__name=self.kwargs['interval']
        ).first()
        if self_review and (self_review.is_visible_to(self.request.user)
                            or self.request.user.has_perm('reviews.view_any_selfreview')):
            context_data['self_review'] = self_review
        context_data['reviews'] = Review.visible_to_manager.filter(
            target=self.object,
            interval__name=self.kwargs['interval']
        ).annotate(
            priority=Case(
                When(reviewer_id=self.object.manager, then=10),
                default=Value(1),
                output_field=IntegerField(),
            )).order_by('-priority', '-id')
        return context_data
