import logging
from functools import wraps

from flask import flash, redirect, render_template, url_for

logger = logging.getLogger(__name__)


def handle_errors(redirect_endpoint=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f'Error in {f.__name__}: {str(e)}', exc_info=True)
                flash(f'Er is een fout opgetreden: {str(e)}', 'error')

                if redirect_endpoint:
                    return redirect(url_for(redirect_endpoint))

                return render_template('error.html', error=str(e)), 500

        return wrapper

    return decorator
