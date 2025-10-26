from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def has_group(context, group_name):
    user = context['request'].user
    try:
        return user.groups.filter(name=group_name).exists()
    except Exception:
        return False
