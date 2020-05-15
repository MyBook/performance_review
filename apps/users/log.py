from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.utils.encoding import force_text

from apps.users.models import User


def log_object_action(obj, message, action_flag=CHANGE, user=None):
    """Create a LogEntry entry for given object"""
    user = user or 'django'
    if not isinstance(user, Model):
        user, _ = User.objects.get_or_create(username=user, defaults={'is_active': False})
    obj_content_type = ContentType.objects.get_for_model(type(obj))
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=obj_content_type.pk,
        object_id=obj.pk,
        object_repr=force_text(obj),
        action_flag=action_flag,
        change_message=message)
