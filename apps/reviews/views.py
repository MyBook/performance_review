import logging
from itertools import chain

from braces.views import UserFormKwargsMixin
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import CreateView, UpdateView, FormView, TemplateView

from apps.reviews.forms import ChoosePeersForm, SelfReviewForm, ReviewForm, ApproveForm, ReviewApproveForm
from apps.reviews.mixins import CurrentIntervalMixin
from apps.reviews.models import SelfReview, Review
from apps.users.models import User

logger = logging.getLogger(__name__)


class SelfReviewContextMixin(SuccessMessageMixin):
    """
    Populate success_message for selfreview page
    """
    model = SelfReview
    form_class = SelfReviewForm
    success_message = 'Self-review сохранён'

    def get_success_url(self):
        """Redirect to index if author can't edit it"""
        if self.object.is_pending or self.object.is_published:
            return reverse('users:redirect')
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context_data = super(SelfReviewContextMixin, self).get_context_data(**kwargs)
        user = self.object.user if self.object else self.request.user
        if self.object:
            previous_sr = SelfReview.published.filter(user=user).filter(pk__lt=self.object.pk).last()
        else:
            previous_sr = SelfReview.published.filter(user=user).exclude(interval=self.current_interval).last()
        context_data['previous_self_review'] = previous_sr
        return context_data


class CreateSelfReview(SelfReviewContextMixin, UserFormKwargsMixin, CurrentIntervalMixin, CreateView):
    """
    Create self-review for current user
    """
    template_name = 'reviews/selfreview_form.html'

    def get_context_data(self, **kwargs):
        context_data = super(CreateSelfReview, self).get_context_data(**kwargs)
        context_data['review_form'] = SelfReviewForm(**self.get_form_kwargs())
        context_data['manager'] = self.request.user.manager
        return context_data


class EditSelfReview(SelfReviewContextMixin, UserFormKwargsMixin, CurrentIntervalMixin, UpdateView):
    """
    Edit existing self-review draft of view.
    Approve subordinate self-review.
    """
    model = SelfReview
    template_name = 'reviews/selfreview_form.html'

    def get_object(self, queryset=None):
        object = SelfReview.objects.get(id=self.kwargs['pk'])
        if object.is_visible_to(self.request.user):
            return object
        if self.request.user.has_perm('reviews.view_any_selfreview'):
            messages.warning(self.request, 'Страница видна вам, т.к. у вас есть право view_any_selfreview')
            return object
        raise PermissionDenied

    def get_form_class(self):
        if self.request.POST.get('action') in {'draft', 'pending'}:
            return SelfReviewForm
        elif self.request.POST.get('action') in {'rejected', 'published'}:
            return ApproveForm
        else:
            return SelfReviewForm

    def get_context_data(self, **kwargs):
        context_data = super(EditSelfReview, self).get_context_data(**kwargs)
        context_data['review_form'] = SelfReviewForm(**self.get_form_kwargs())
        context_data['approve_form'] = ApproveForm(**self.get_form_kwargs())
        context_data['manager'] = self.object.user.manager
        context_data['is_manager_view'] = self.object.is_pending and self.object.user.manager == self.request.user
        context_data['reviewers'] = User.active.filter(responses__target=self.object.user,
                                                       responses__interval=self.current_interval)
        return context_data


class ChoosePeers(SuccessMessageMixin, CurrentIntervalMixin, FormView):
    """
    Choose reviewers (aka peers), or view existing
    """
    form_class = ChoosePeersForm
    template_name = 'reviews/choose_peers_form.html'
    success_message = 'Выбор пиров сохранён'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(ChoosePeers, self).dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        user = User.objects.get(email=self.kwargs['email'])
        if user == self.request.user or user.manager == self.request.user:
            return user
        if self.request.user.has_perm('reviews.view_all_peers'):
            messages.warning(self.request, 'Страница видна вам, т.к. у вас есть право view_all_peers')
            return user
        raise PermissionDenied

    def get_or_create_existing_peers(self):
        existing_peers = self.get_existing_peers()
        logger.debug('existing peers %s' % existing_peers)
        if not existing_peers:
            possible_peers = self.object.subordinates.filter(is_active=True)
            if self.object.manager:
                possible_peers = chain(possible_peers, [self.object.manager])
            subordinate_and_manager_reviews = Review.objects.bulk_create([
                Review(interval=self.current_interval,
                       target=self.object,
                       reviewer=user,
                       status=Review.STATUS.requested)
                for user in possible_peers])
            logger.debug('Created default review requests %s' % list(subordinate_and_manager_reviews))
            existing_peers = [r.reviewer for r in subordinate_and_manager_reviews]
        return existing_peers

    def get_existing_peers(self):
        return User.objects.filter(responses__target=self.object,
                                   responses__interval=self.current_interval)

    def get_initial(self):
        return {'peers': self.get_or_create_existing_peers()}

    def get_form_kwargs(self):
        kwargs = super(ChoosePeers, self).get_form_kwargs()
        kwargs['user'] = self.object
        return kwargs

    def form_valid(self, form):
        existing_peers = self.get_existing_peers()
        peers_selected = form.cleaned_data['peers']
        peers_to_add = [p for p in peers_selected if p not in existing_peers]
        for peer in peers_to_add:
            Review.objects.get_or_create(interval=self.current_interval,
                                         target=self.object,
                                         reviewer=peer,
                                         status=Review.STATUS.requested)
        peers_to_delete = [p for p in existing_peers
                           if p not in peers_selected and self.object.manager != p]

        # deleting peers is available only when self-review is not approved (reviews are in requested state)
        Review.requested.filter(interval=self.current_interval,
                                reviewer__in=peers_to_delete).delete()
        return super().form_valid(form)


class AddReviews(CurrentIntervalMixin, TemplateView):
    """
    List of requested reviews for current user to fill in this interval
    """
    template_name = 'reviews/review_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_reviews'] = Review.objects.waiting_from_user(
            user=self.request.user, interval=self.current_interval)
        return context


class ApproveReviews(CurrentIntervalMixin, TemplateView):
    """
    List of requested reviews for current user to approve in this interval
    """
    template_name = 'reviews/approve_reviews_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews_require_approval'] = Review.require_approval.filter(interval=self.current_interval,
                                                                             target__manager=self.request.user)
        context['reviews_approved'] = Review.approved.filter(interval=self.current_interval,
                                                             target__manager=self.request.user).order_by('target')
        return context


class ReviewDetail(UserFormKwargsMixin, SuccessMessageMixin, CurrentIntervalMixin, UpdateView):
    """
    Edit / view / approve single review
    """
    template_name = 'reviews/review_detail.html'
    model = Review

    def get_object(self, queryset=None):
        object = super().get_object(queryset=queryset)
        if object.is_visible_to(self.request.user):
            return object
        if self.request.user.has_perm('reviews.view_any_review'):
            messages.warning(self.request, 'Страница видна вам, т.к. у вас есть право view_any_review')
            return object
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['review_form'] = ReviewForm(**self.get_form_kwargs())
        context_data['approve_form'] = ReviewApproveForm(**self.get_form_kwargs())
        context_data['self_review'] = SelfReview.objects.get(user=self.object.target,
                                                             interval=self.object.interval)
        context_data['previous_review'] = (Review.visible_to_reviewer.filter(target=self.object.target,
                                                                             reviewer=self.object.reviewer)
                                                                     .exclude(interval=self.current_interval)
                                                                     .order_by('interval__name').last())
        return context_data

    def get_success_url(self):
        return self.object.get_absolute_url()

    def _is_approve_review_form(self):
        return self.request.POST.get('action') in {'rejected', 'hidden', 'published'}

    def get_success_message(self, cleaned_data):
        if self._is_approve_review_form():
            return 'Отзыв на фидбэк сохранён'
        else:
            return 'Фидбэк сохранён'

    def get_form_class(self):
        if self._is_approve_review_form():
            return ReviewApproveForm
        else:
            return ReviewForm

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, mark_safe(
            '<h4 class="alert-heading">Ошибки при заполнении формы</h4>%s' % form.errors))
        return response
