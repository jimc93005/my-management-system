from django import template

# This registers our custom filters so Django templates can use them
register = template.Library()

@register.filter
def dict_get(dictionary, key):
    """
    Safely gets a value from a dictionary using the key.
    Usage in template: {{ my_dict|dict_get:my_key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None