from flask import Blueprint, render_template

bp = Blueprint('onboarding-in-front', __name__, url_prefix='/onboarding-in-front')


@bp.route('/')
def main():
    return render_template(
        'onboarding-in-front/onboarding-in-front.html',
        title='Onboarding-In-Front',
        data={'message': 'Welkom bij onboarding-in-front!'},
    )
