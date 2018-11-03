
from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask_login import login_required, current_user
from flask_wtf import Form
from flask_mongoengine.wtf import model_form
from . import main
from .forms import UserForm
from ..models import User


@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # MyForm = model_form(User, Form, exclude=['password_hash'], field_args={'password': {
    #     'lebel': 'password',
    # }})
    # form = MyForm(request.form)
    '''form = UserForm()
    print('index call...')
    if form.validate_on_submit():
        print('form valid')
        print(form)
        return make_response('hello')
    return render_template('index.html', form=form)'''

    return 'hello %s' % current_user.name

@main.route('/user/<username>', methods=['GET'])
@login_required
def user(username):
    return 'hello'