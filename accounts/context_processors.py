def auth_roles(request):
    """
    Exposes role flags to templates for clean and unified checks.
    """
    user = getattr(request, 'user', None)
    is_authenticated = user and user.is_authenticated
    is_admin = is_authenticated and getattr(user, 'is_admin_role', lambda: False)()
    is_basic = is_authenticated and getattr(user, 'is_basic_role', lambda: False)()
    return {
        'is_admin': is_admin,
        'is_basic_user': is_basic,
        'current_user_role': getattr(user, 'role', '') if is_authenticated else '',
    }
