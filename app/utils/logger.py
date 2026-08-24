"""
Logging utility for Flowintel
"""
import logging
from flask import request, current_app, has_request_context


def _sanitize_log_fragment(value):
    """Keep log records on one physical line."""
    return str(value).replace('\r', '\\r').replace('\n', '\\n')


def flowintel_log(log_type, severity, message, **kwargs):
    """Log an event with standardized format"""
    _log_message(log_type, severity, message, **kwargs)


def _log_message(log_type, severity, message, **kwargs):
    """Format and log messages"""
    ip_address = _sanitize_log_fragment(request.remote_addr if has_request_context() else 'N/A')
    
    if log_type == 'audit':
        prefix = current_app.config.get('AUDIT_LOG_PREFIX', 'AUDIT') if has_request_context() else 'AUDIT'
    else:
        prefix = log_type.upper()
    prefix = _sanitize_log_fragment(prefix)
    message = _sanitize_log_fragment(message)
    
    additional_info = ''
    if kwargs:
        additional_info = ' ' + ' '.join([
            f'{_sanitize_log_fragment(key)}: {_sanitize_log_fragment(value)}'
            for key, value in kwargs.items()
        ])
    
    log_msg = f'{ip_address} - - "{prefix}: {severity} - {message}.{additional_info}'
    
    if severity >= 500 or log_type == 'error':
        logging.error(log_msg)
    elif severity >= 400 or log_type == 'warning':
        logging.warning(log_msg)
    else:
        logging.info(log_msg)
