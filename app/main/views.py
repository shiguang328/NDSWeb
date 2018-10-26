
from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask_login import login_required, current_user
from . import main
from .forms import UserForm


@main.route('/', methods=['GET', 'POST'])
def index():
    form = UserForm()
    print('index call...')
    if form.validate_on_submit():
        print('form valid')
        print(form)
        return make_response('hello')
    return render_template('index.html', form=form)