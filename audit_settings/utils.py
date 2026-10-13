from audit_settings.models import AuditLog


def log_audit(request, action, target_type='', target_id='', target_reference='', details=''):
    """
    Safely creates an audit log entry from a trusted server-side operation.
    """
    actor = request.user if (request and hasattr(request, 'user') and request.user.is_authenticated) else None
    
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        target_reference=str(target_reference),
        details=details,
        ip_address=ip_address
    )
