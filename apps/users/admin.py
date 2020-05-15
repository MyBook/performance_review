from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from hijack_admin.admin import HijackUserAdminMixin

from .models import User, Department


class MyUserChangeForm(UserChangeForm):

    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(forms.ModelForm):
    """
    Create new employee (no password required)
    """
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'job', 'manager', 'department')


class DefaultYesFilter(admin.SimpleListFilter):
    def lookups(self, request, model_admin):
        return (
            ('no', 'Нет'),
            ('yes', 'Да'),
        )

    def value(self):
        """Override default selected value -> yes"""
        real_value = super().value()
        if real_value is None:
            real_value = 'yes'
        return real_value

    def queryset(self, request, queryset):
        if self.value() == 'no':
            return queryset.filter(**{self.parameter_name: False})
        else:
            return queryset.filter(**{self.parameter_name: True})


class ActiveDefaultFilter(DefaultYesFilter):
    title = 'Активный'
    parameter_name = 'is_active'


class IsReviewableFilter(DefaultYesFilter):
    title = 'Участвует в ревью'
    parameter_name = 'is_reviewable'


def make_disabled(modeladmin, request, queryset):
    queryset.update(is_active=False)
make_disabled.short_description = 'Уволить сотрудника'


def make_unreviewable(modeladmin, request, queryset):
    queryset.update(is_reviewable=False)
make_unreviewable.short_description = 'Убрать из perf review'


def make_reviewable(modeladmin, request, queryset):
    queryset.update(is_reviewable=True)
make_reviewable.short_description = 'Добавить в perf review'


@admin.register(User)
class MyUserAdmin(HijackUserAdminMixin, AuthUserAdmin):
    actions = [make_disabled, make_unreviewable, make_reviewable, ]
    add_form = MyUserCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'username', 'email', 'job', 'manager', 'department'),
        }),
    )
    autocomplete_fields = ['manager', 'job', 'department']
    fieldsets = (('User Profile', {'fields': ('avatar', 'job', 'manager', 'department', 'is_reviewable')}),) + AuthUserAdmin.fieldsets
    form = MyUserChangeForm
    list_display = ('html_handler', 'html_avatar', 'email', 'is_reviewable', 'last_login', 'absolute_url', 'hijack_field',)
    list_select_related = ['job', 'department']
    list_filter = [ActiveDefaultFilter, IsReviewableFilter, 'department']
    prepopulated_fields = {'username': ('first_name', 'last_name',)}
    search_fields = ['email', 'first_name', 'last_name']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    def html_handler(self, obj):
        return mark_safe(f'{str(obj)}<br/><i>{obj.job}</i>')
    html_handler.allow_tags = True
    html_handler.short_description = 'Имя'

    def html_avatar(self, obj):
        if obj.avatar:
            html_template = '<img src="{image}" width=50 height=50>'
            return format_html(html_template, image=obj.avatar.url)
        else:
            return ''
    html_avatar.allow_tags = True
    html_avatar.short_description = 'Аватар'

    def absolute_url(self, obj):
        return format_html('<a href="{url}">Сайт</a>', url=obj.get_absolute_url())
    absolute_url.allow_tags = True
    absolute_url.short_description = 'На сайте'


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'weight']
    list_editable = ['weight']
    search_fields = ['name']
