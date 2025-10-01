from flask import Blueprint, render_template

bp = Blueprint('test_app1', __name__, url_prefix='/test_app1')

@bp.route('/')
def main():
    return render_template('test_app1/test_app1.html',
                         title='Test App 1',
                         data={'message': 'Dit is de eerste test applicatie!'})
