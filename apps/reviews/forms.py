import logging

from braces.forms import UserKwargModelFormMixin
from django import forms
from django.core.exceptions import ValidationError

from apps.reviews.form_utils import GroupedModelMultipleChoiceField
from apps.reviews.models import SelfReview, Review
from apps.users.models import User

logger = logging.getLogger(__name__)


class ChoosePeersForm(UserKwargModelFormMixin, forms.Form):
    """
    Multiple checkbox form, can't choose self
    """
    peers = GroupedModelMultipleChoiceField(queryset=User.active.order_by('department__weight', 'department__name',
                                                                          'last_name',
                                                                          'first_name'),
                                            group_by_field='department',
                                            group_label=lambda x: x.name,
                                            widget=forms.CheckboxSelectMultiple,
                                            label='Подразделение')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['peers'].queryset = User.active.exclude(id=self.user.id)


class SelfReviewForm(UserKwargModelFormMixin, forms.ModelForm):
    """
    Single text field for personal self-review.
    """
    class Meta:
        model = SelfReview
        fields = ['text', 'interval']
        widgets = {'interval': forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].label = False

    def clean(self):
        self.cleaned_data = super().clean()
        # default model validation does not validate unique together (no idea why)
        if not self.instance.id and SelfReview.objects.filter(user=self.user,
                                                              interval=self.cleaned_data['interval']).exists():
            raise ValidationError('Ревью уже существует, двойная отправка')

        if self.instance.is_editable:
            if self.data.get('action') == 'pending':
                self.cleaned_data['action'] = self.data['action']
            return self.cleaned_data
        else:
            message = 'Ошибка при сохранении ревью, напишите в поддержку'
            logger.error(message, exc_info=True)
            raise ValidationError(message)

    def save(self, commit=True):
        if not self.instance.id:
            self.instance.user = self.user
        if self.cleaned_data.get('action'):
            self.instance.status = self.cleaned_data['action']

        # auto-publish boss review, because she has no manager to do this for her
        if self.instance.user.is_boss:
            self.instance.status = SelfReview.STATUS.published
        return super().save(commit=commit)


class ApproveForm(UserKwargModelFormMixin, forms.ModelForm):
    """
    Self-review approval for manager: comment + action (submit value)
    """
    class Meta:
        model = SelfReview
        fields = ['comment']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].label = False

    def clean(self):
        self.check_manager_permissions()
        if self.instance.is_pending:
            if self.data['action'] in {'rejected', 'published', 'hidden'}:
                self.cleaned_data['action'] = self.data['action']
        else:
            message = 'Ошибка при сохранении, напишите в поддержку'
            logger.error(message, exc_info=True)
            raise ValidationError(message)
        return super().clean()

    def save(self, commit=True):
        if self.cleaned_data.get('action'):
            self.instance.status = self.cleaned_data['action']
        return super().save(commit=commit)

    def check_manager_permissions(self):
        if self.user != self.instance.user.manager:
            message = (f'У вас недостаточно прав чтобы одобрять/отклонять этот self-review'
                       f'(за это отвечает {self.instance.user.manager})')
            logger.error(message, exc_info=True)
            raise ValidationError(message, code='not_manager')


class ReviewApproveForm(ApproveForm):
    """
    Same as ApproveForm, but for Review model
    """
    class Meta:
        model = Review
        fields = ['comment']

    def check_manager_permissions(self):
        if self.user != self.instance.target.manager:
            message = (f'У вас недостаточно прав чтобы одобрять/отклонять этот фидбэк'
                       f'(за это отвечает {self.instance.target.manager})')
            logger.error(message, exc_info=True)
            raise ValidationError(message, code='not_manager')


class ReviewForm(UserKwargModelFormMixin, forms.ModelForm):
    """
    Feedback review: score + comment. Interval is technical field (non-editable)
    """

    class Meta:
        model = Review
        fields = ['score', 'text', 'interval']
        widgets = {
            'interval': forms.HiddenInput(),
            'score': forms.RadioSelect
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['score'].required = True
        self.fields['score'].choices.pop(0)  # remove null value from choices
        self.fields['score'].label = False
        self.fields['text'].label = 'Прокомментируйте свою оценку'
        self.fields['score'].error_messages = {
            'required': 'Нужно оценить работу коллеги, если не работали плотно - выберите "Не взаимодействовал, оценить не могу"'  # noqa
        }

    def clean(self):
        if self.instance.is_editable:
            if self.data['action'] == 'pending':
                self.cleaned_data['action'] = self.data['action']
                if self.instance.is_subordinate_review:
                    # auto-approve manager -> subordinate review
                    self.cleaned_data['action'] = Review.STATUS.hidden
        else:
            message = 'Ошибка при сохранении ревью, напишите в поддержку'
            logger.error(message, exc_info=True)
            raise ValidationError(message)
        if not self.cleaned_data.get('text') and self.cleaned_data.get('score') and self.cleaned_data['score'] != '-':
            raise ValidationError('Без текста обратная связь не очень полезна, нужно обязательно написать комментарий.')
        return super().clean()

    def save(self, commit=True):
        if self.cleaned_data.get('action'):
            self.instance.status = self.cleaned_data['action']
        return super().save(commit=commit)
