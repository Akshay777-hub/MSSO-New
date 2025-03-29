from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed

# Disable CSRF protection
class NoCSRFFlaskForm(FlaskForm):
    class Meta:
        csrf = False
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, FloatField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange
from models import Role

class LoginForm(NoCSRFFlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(NoCSRFFlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    password_confirm = PasswordField(
        'Confirm Password', 
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    role = SelectField(
        'Role', 
        choices=[
            (Role.DIRECTOR, 'Director'),
            (Role.PRODUCTION_MANAGER, 'Production Manager'),
            (Role.SCHEDULING_COORDINATOR, 'Scheduling Coordinator')
        ],
        validators=[DataRequired()]
    )

class ProjectForm(NoCSRFFlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])

class ScreenplayUploadForm(NoCSRFFlaskForm):
    screenplay = FileField(
        'Screenplay PDF',
        validators=[
            FileRequired(),
            FileAllowed(['pdf'], 'PDF files only!')
        ]
    )

class ActorForm(NoCSRFFlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    character_name = StringField('Character Name', validators=[DataRequired(), Length(max=100)])
    cost_per_day = FloatField(
        'Cost Per Day ($)',
        validators=[DataRequired(), NumberRange(min=0)]
    )
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])

class LocationForm(NoCSRFFlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    address = StringField('Address', validators=[Optional(), Length(max=200)])
    cost_per_day = FloatField(
        'Cost Per Day ($)',
        validators=[DataRequired(), NumberRange(min=0)]
    )

class ScheduleForm(NoCSRFFlaskForm):
    name = StringField('Schedule Name', validators=[DataRequired(), Length(max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[Optional()])
    algorithm = SelectField(
        'Optimization Algorithm',
        choices=[
            ('ant_colony', 'Ant Colony Optimization (ACOBM)'),
            ('tabu_search', 'Tabu Search (TSBM)'),
            ('particle_swarm', 'Particle Swarm Optimization (PSOBM)')
        ],
        default='ant_colony',
        validators=[DataRequired()]
    )
