from django import template

register = template.Library()

status2class_mapping = {
    'draft': 'badge-secondary',
    'rejected': 'badge-danger',
    'pending': 'badge-info',
    'published': 'badge-success',
}


@register.filter
def status2bootstraplabel(status):
    """
    Twitter Boostrap class name for badge CSS class depending on (self-)review status
    """
    return status2class_mapping.get(status)
