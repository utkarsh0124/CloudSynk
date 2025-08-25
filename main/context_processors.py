def api_flags(request):
    """Expose ENABLE_API_ENDPOINTS flag to templates so client JS can switch behavior.

    Returns a dict with 'ENABLE_API_ENDPOINTS' boolean.
    """
    from django.conf import settings
    return {'ENABLE_API_ENDPOINTS': getattr(settings, 'ENABLE_API_ENDPOINTS', False)}
