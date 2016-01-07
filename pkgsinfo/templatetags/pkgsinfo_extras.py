from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from distutils.version import LooseVersion

# Reference for creating custom filters and tags:-
# https://docs.djangoproject.com/en/dev/howto/custom-template-tags/

register = template.Library()

@register.filter(name='wrappable', needs_autoescape=True)
@stringfilter
def wrappable_filter(value, autoescape=None):
    """
    Places zero-width breaking spaces in text to allow it to wrap 
    before a underscore (_) or fullstop (.). The browser will use this
    as a hint as to where to wrap the text if required.
    """
    
    # Escape the input text so that it's safe to display
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    escaped_wrapped_text = '%s' % (esc(value))

    # Add hints to the browser that it can wrap before a _ of .
    escaped_wrapped_text = escaped_wrapped_text.replace('_', '&#8203;_')
    escaped_wrapped_text = escaped_wrapped_text.replace('.', '&#8203;.')

    # Return the text marked as safe so that the new &#8203;'s aren't escaped
    return mark_safe(escaped_wrapped_text)


@register.filter
def type_is(item, kind):
    """Returns the data type of the item (plist-style)"""
    if kind == 'string':
        return isinstance(item, basestring)
    if kind == 'boolean':
        return isinstance(item, bool)
    if kind == 'integer':
        return isinstance(item, int)
    if kind == 'float':
        return isinstance(item, float)
    if kind == 'array':
        return isinstance(item, list)
    if kind == 'dictionary':
        return isinstance(item, dict)
    return False
type_is.is_safe = True
