from ..models import User
from flask import current_app
from flask_mongoengine.wtf import model_form
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateField, DateTimeField, SelectField, TextField, IntegerField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError


class UserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
               'Usernames must have only letters, numbers, dots or '
               'underscores')])
    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    name = StringField('Name')
    phone = StringField('Phone Number')
    submit = SubmitField('Register')


class CarInformationForm(FlaskForm):
    car_id = IntegerField('Car ID')
    license_plate = StringField('License Plate', validators=[DataRequired()])
    brand = StringField('Brand', validators=[DataRequired()])
    owner_company = StringField('Owner Company')
    project_related = StringField('Project Related')
    buy_time = DateField('Buy Time', validators=[DataRequired()])
    insurance_num = StringField('Insurance Number')
    model_name = StringField('Model')
    # vehicle_type = SelectField('Vehicle Type', choices=list(zip(current_app.config['VEHICLE_TYPE'],
    #                                                             current_app.config['VEHICLE_TYPE'])))
    # power_type = SelectField('Power Type', choices=list(zip(current_app.config['POWER_TYPE'],
                                                            # current_app.config['POWER_TYPE'])))
    autonomous = BooleanField('Autonomous Vehicle')
    accident_log = TextField('Accident Log')
    others = TextField('Others')


class DriverInformationForm(FlaskForm):
    driver_id = IntegerField('Car ID')
    first_name = StringField('First Name', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('Last Name', validators=[Length(0, 64)])
    address = StringField('Address')
    city = StringField('City')
    state = StringField('State')
    zip = StringField('Zip')
    gender = SelectField('Gender', choices=[('M', 'Male'), ('F', 'Female')])
    location = StringField('Location')
    brithday = DateField('Brithday')
    vehicle = StringField('Vehicle')
    driving_years = IntegerField('Driving Years')
    profession = StringField('Profession')
    mileage_total = IntegerField('Mileage(km)')
    start_date = DateField('Start Date')
    return_date = DateField('Return Date')
    end_date = DateField('End Date')
    mileage_1th_month = IntegerField('Mileage(km) at 1th month')
    mileage_2th_month = IntegerField('Mileage(km) at 2th month')
