from flask import Blueprint, render_template

bp = Blueprint('calculator', __name__, url_prefix='/calculator')

@bp.route('/')
def main():
    return render_template('calculator/calculator.html', 
                         title='Calculator',
                         data={'message': 'Welkom bij calculator!'})
