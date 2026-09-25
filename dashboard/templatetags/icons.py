"""Inline SVG icon set — {% icon "name" %} — replacing all emoji glyphs.

Stroke icons inherit the surrounding text colour via `currentColor`, so a single
definition works on the dark sidebar, in coloured card headers, and on buttons.
Filled marks (logo, sparkle) set their own fill.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_STROKE = (
    '<svg class="ic-svg {cls}" width="{s}" height="{s}" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">{body}</svg>'
)
_FILL = (
    '<svg class="ic-svg {cls}" width="{s}" height="{s}" viewBox="0 0 24 24" '
    'fill="currentColor" aria-hidden="true">{body}</svg>'
)

_ICONS = {
    "dashboard": ('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>'
                  '<rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>'),
    "clients": ('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
                '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
    "caregivers": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "schedule": ('<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>'
                 '<line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>'),
    "visits": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "incidents": ('<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
                  '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'),
    "reports": ('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
                '<polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>'
                '<line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/>'),
    "map": ('<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>'
            '<line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>'),
    "analytics": ('<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>'
                  '<line x1="6" y1="20" x2="6" y2="14"/>'),
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "menu": '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "close": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "calendarplus": ('<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>'
                     '<line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>'
                     '<line x1="12" y1="14" x2="12" y2="18"/><line x1="10" y1="16" x2="14" y2="16"/>'),
    "inbox": ('<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>'
              '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'),
    "repeat": ('<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/>'
               '<polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>'),
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>',
    "award": ('<circle cx="12" cy="8" r="6"/>'
              '<polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>'),
    "radio": ('<circle cx="12" cy="12" r="2"/>'
              '<path d="M4.93 19.07a10 10 0 0 1 0-14.14M7.76 16.24a6 6 0 0 1 0-8.48'
              'M16.24 7.76a6 6 0 0 1 0 8.48M19.07 4.93a10 10 0 0 1 0 14.14"/>'),
    "dollar": ('<line x1="12" y1="1" x2="12" y2="23"/>'
               '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'),
    "logout": ('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
               '<polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'),
    "megaphone": ('<path d="M3 11l18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>'),
    "recruitment": ('<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/>'
                    '<line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>'),
    "settings": ('<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
                 '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
                 '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
                 '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
                 '<line x1="17" y1="16" x2="23" y2="16"/>'),
    "bell": ('<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
             '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>'),
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "warning": ('<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
                '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'),
    "arrow": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "download": ('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
                 '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>'),
    "print": ('<polyline points="6 9 6 2 18 2 18 9"/>'
              '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
              '<rect x="6" y="14" width="12" height="8"/>'),
}

# Filled marks
_ICONS_FILL = {
    "ai": ('<path d="M12 2l1.9 5.1L19 9l-5.1 1.9L12 16l-1.9-5.1L5 9l5.1-1.9L12 2z"/>'
           '<path d="M18.5 14l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2z"/>'),
    "paw": ('<ellipse cx="12" cy="15.5" rx="4.6" ry="3.6"/>'
            '<ellipse cx="6.3" cy="10.5" rx="1.9" ry="2.3"/>'
            '<ellipse cx="9.7" cy="7.2" rx="2" ry="2.5"/>'
            '<ellipse cx="14.3" cy="7.2" rx="2" ry="2.5"/>'
            '<ellipse cx="17.7" cy="10.5" rx="1.9" ry="2.3"/>'),
}


@register.simple_tag
def icon(name, size=18, cls=""):
    if name in _ICONS_FILL:
        return mark_safe(_FILL.format(s=size, cls=cls, body=_ICONS_FILL[name]))
    body = _ICONS.get(name, _ICONS["dashboard"])
    return mark_safe(_STROKE.format(s=size, cls=cls, body=body))


@register.filter
def dictkey(d, key):
    """Look up d[key] in a template (supports int or str keys)."""
    try:
        return d.get(key, d.get(str(key), ""))
    except AttributeError:
        return ""
