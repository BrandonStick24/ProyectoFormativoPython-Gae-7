from django import template
register = template.Library()

@register.filter
def get_star_count(distribucion, star):
    return distribucion.get(star, 0)

@register.filter
def get_star_percentage(porcentajes, star):
    return porcentajes.get(star, 0)