from django.contrib import admin

from apps.reviews.models import Interval, Job, SelfReview, Review


@admin.register(Interval)
class IntervalAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'status_changed', 'created']
    readonly_fields = ('status_changed', 'created', 'modified')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(SelfReview)
class SelfReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'interval', 'created']
    list_filter = ['interval', 'status']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['reviewer', 'target', 'score', 'status', 'modified', 'interval']
    list_filter = ['interval', 'score', 'status', 'target', 'reviewer']
    actions = ['make_draft']

    def make_draft(self, request, queryset):
        queryset.filter(status='requested').update(status='draft')
    make_draft.short_description = 'Одобрить выбор ревьюера'
