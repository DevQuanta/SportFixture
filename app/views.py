from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)

@main_bp.route('/')
def home_page():
    return render_template('main.html')


@main_bp.route('/knockouts')
def knockouts_page():
    return render_template('knockouts.html')
