import pytest
from django.core.management import call_command, CommandError

from apps.reviews.factories import UserFactory, SelfReviewFactory, ReviewFactory
from apps.reviews.models import SelfReview, Review


def test_send_email_edgecase(running_interval, mailoutbox):
    with pytest.raises(CommandError) as excinfo:
        call_command('send_email')
    assert 'Specify which template' in str(excinfo.value)

    with pytest.raises(CommandError) as excinfo:
        call_command('send_email', template='welcome')
    assert 'Specify recipient email' in str(excinfo.value)

    with pytest.raises(CommandError) as excinfo:
        call_command('send_email', suitable=True, template='xxx')
    assert 'Unsupported' in str(excinfo.value)


def test_send_welcome(running_interval, mailoutbox):
    UserFactory(is_active=False)
    UserFactory(is_reviewable=False)
    UserFactory(email='ecastillo@hotmail.com', department__name='ACME')
    UserFactory(email='blahblah@ya.ru', department__name='DC')
    call_command('send_email', template='welcome', suitable=True)
    assert len(mailoutbox) == 2

    mail = mailoutbox[0]
    assert 'Наступает супер-время' in mail.subject
    assert {m.to[0] for m in mailoutbox} == {'ecastillo@hotmail.com', 'blahblah@ya.ru'}

    mailoutbox.clear()
    call_command('send_email', template='welcome', suitable=True, department='ACME')
    assert len(mailoutbox) == 1
    assert {m.to[0] for m in mailoutbox} == {'ecastillo@hotmail.com'}


@pytest.mark.parametrize(['status', 'subject', 'recipient'], [
    (SelfReview.STATUS.pending, 'написал self-review', 'manager@yahoo.com'),
    (SelfReview.STATUS.rejected, 'нужно доработать', 'user@yahoo.com'),
    (SelfReview.STATUS.published, 'твой self-review проверил', 'user@yahoo.com'),
])
def test_selfreview_written(running_interval, mailoutbox, status, subject, recipient):
    self_review = SelfReviewFactory(user__email='user@yahoo.com',
                                    user__with_manager=True,
                                    user__with_manager__email='manager@yahoo.com',
                                    draft=True)
    assert len(mailoutbox) == 0

    self_review.status = status
    self_review.save()
    assert len(mailoutbox) == 1

    mail = mailoutbox[0]
    assert subject in mail.subject
    assert mail.to[0] == recipient


@pytest.mark.parametrize(['status', 'subject', 'recipient'], [
    (Review.STATUS.pending, 'Требует проверки фидбэк', 'manager@yahoo.com'),
    (Review.STATUS.draft, 'Прошу тебя оценить', 'reviewer@yahoo.com'),
    (Review.STATUS.rejected, 'Требует доработки', 'reviewer@yahoo.com'),
])
def test_review_written(running_interval, mailoutbox, status, subject, recipient):
    selfreview = SelfReviewFactory(user__with_manager=True,
                                   user__with_manager__email='manager@yahoo.com',
                                   interval=running_interval)
    review = ReviewFactory(reviewer__email='reviewer@yahoo.com',
                           target=selfreview.user,
                           requested=True,
                           interval=running_interval)
    assert len(mailoutbox) == 0

    review.status = status
    review.save()
    assert len(mailoutbox) == 1

    mail = mailoutbox[0]
    assert subject in mail.subject
    assert mail.to[0] == recipient
