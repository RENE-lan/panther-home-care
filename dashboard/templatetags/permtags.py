from django import template
register = template.Library()

@register.filter
def dictkey(d, k):
    try:
        return d.get(k)
    except Exception:
        return None
