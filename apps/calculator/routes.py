"""Routing for the calculator application."""

from flask import Blueprint, render_template

from core.error_handler import handle_errors

bp = Blueprint('calculator', __name__, url_prefix='/calculator')


@bp.route('/')
@handle_errors(redirect_endpoint='calculator.main')
def main():
    return render_template(
        'calculator/calculator.html',
        title='Calculator',
        data={'message': 'Welkom bij calculator!'},
    )
