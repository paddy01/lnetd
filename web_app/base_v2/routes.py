from flask import Blueprint, render_template, redirect, request, url_for

from flask_login import (
    current_user,
    LoginManager,
    login_required,
    login_user,
    logout_user
)

from .forms import LoginForm
from passlib.hash import argon2
from database import db
from .models import User

blueprint = Blueprint(
    'base_blueprint',
    __name__,
    url_prefix='/',
    template_folder='templates',
    static_folder='static'
)

login_manager = LoginManager()


@blueprint.route('/')
def route_default():
    return redirect(url_for('base_blueprint.login'))

'''
@blueprint.route('/<template>')
@login_required
def route_template(template):
    return render_template(template + '.html')
'''

'''
@blueprint.route('/fixed_<template>')
@login_required
def route_fixed_template(template):
    return render_template('fixed/fixed_{}.html'.format(template))
'''

@blueprint.route('/page_<error>')
def route_errors(error):
    return render_template('errors/page_{}.html'.format(error))


@blueprint.route('/no_admin')
def no_admin():
    return render_template('errors/page_403.html')

## Login & Registration


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    if 'login' in request.form:
        username = str(request.form['username'])
        password = str(request.form['password'])
        user = db.session.query(User).filter_by(username=username).first()
        if user and argon2.verify(password, user.password):
            login_user(user)
            return redirect(url_for('base_blueprint.route_default'))
        return render_template('errors/page_403.html')
    if not current_user.is_authenticated:
        return render_template(
            'login/login.html',
            login_form=login_form,
        )
    return redirect(url_for('home_blueprint.index'))


@blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('base_blueprint.login'))

# Errors


@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('base_blueprint.login'))


@blueprint.errorhandler(403)
def not_found_error(error):
    return render_template('errors/page_403.html'), 403

@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('errors/page_404.html'), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('errors/page_500.html'), 500
