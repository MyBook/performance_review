from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.reviews.models import Review, SelfReview
from apps.reviews.emails import ReviewPendingMessage, SelfreviewPendingMessage, ReviewRejectedMessage, \
    SelfreviewRejectedMessage, SelfreviewPublishedMessage, ReviewDraftMessage


@receiver(post_save, sender=SelfReview)
def send_selfreview_notification(sender, instance, created, **kwargs):
    if instance.tracker.has_changed('status'):
        if instance.status == instance.STATUS.pending and instance.user.manager:
            SelfreviewPendingMessage(context={
                'selfreview': instance,
                'user': instance.user.manager
            }).send(to=[instance.user.manager.email],)
        elif instance.status == instance.STATUS.rejected:
            SelfreviewRejectedMessage(context={
                'selfreview': instance,
                'user': instance.user
            }).send(to=[instance.user.email])
        elif instance.status == instance.STATUS.published and instance.user.manager:
            SelfreviewPublishedMessage(context={
                'selfreview': instance,
                'user': instance.user
            }).send(to=[instance.user.email])


@receiver(post_save, sender=Review)
def send_review_notification(sender, instance, created, **kwargs):
    if instance.tracker.has_changed('status'):
        if instance.status == instance.STATUS.pending and instance.target.manager:
            ReviewPendingMessage(context={
                'review': instance,
                'user': instance.target.manager
            }).send(to=[instance.target.manager.email])
        elif instance.status == instance.STATUS.rejected:
            ReviewRejectedMessage(context={
                'review': instance,
                'user': instance.reviewer
            }).send(to=[instance.reviewer.email])
        elif instance.status == instance.STATUS.draft:
            selfreview = SelfReview.objects.filter(user=instance.target, interval=instance.interval).first()
            if selfreview:
                ReviewDraftMessage(context={
                    'review': instance,
                    'user': instance.reviewer,
                    'selfreview': selfreview
                }).send(to=[instance.reviewer.email])



