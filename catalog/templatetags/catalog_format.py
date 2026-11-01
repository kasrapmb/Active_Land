from django import template
register = template.Library()
@register.filter
def fa(value):
    return str(value).translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹'))
@register.filter
def toman(value):
    return fa(f'{value:,}'.replace(',', '٬'))
