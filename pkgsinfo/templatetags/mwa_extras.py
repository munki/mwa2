from django import template

register = template.Library()

@register.filter(name='addcss')
def addcss(field, css):
    class_old = field.field.widget.attrs.get('class', '')
    if class_old:
        class_new = class_old + ' ' + css
    else:
        class_new = css
    return field.as_widget(attrs={"class": class_new})