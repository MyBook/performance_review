from django.contrib import admin

from apps.goals.models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ['target', 'modified', 'interval']
    list_filter = ['interval', 'target']
    autocomplete_fields = ['target']
