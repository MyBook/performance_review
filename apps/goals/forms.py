from braces.forms import UserKwargModelFormMixin
from django import forms

from apps.goals.models import Goal


class GoalForm(UserKwargModelFormMixin, forms.ModelForm):
    """
    Single text field for goals
    """
    class Meta:
        model = Goal
        fields = ['text', 'interval']
        widgets = {'interval': forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].label = ''

    def clean(self):
        self.cleaned_data['target'] = self.user
        return super(GoalForm, self).clean()

    def save(self, commit=True):
        if not self.instance.id:
            self.instance.target = self.cleaned_data['target']
        return super().save(commit=commit)
