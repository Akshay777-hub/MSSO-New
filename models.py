from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from app import db

# User roles
class Role:
    DIRECTOR = 'director'
    PRODUCTION_MANAGER = 'production_manager'
    SCHEDULING_COORDINATOR = 'scheduling_coordinator'
    
    @classmethod
    def get_all(cls):
        return [cls.DIRECTOR, cls.PRODUCTION_MANAGER, cls.SCHEDULING_COORDINATOR]

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Projects created by this user
    projects = db.relationship('Project', backref='creator', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Project model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Project elements
    screenplay_path = db.Column(db.String(256))
    scenes = db.relationship('Scene', backref='project', lazy='dynamic')
    actors = db.relationship('Actor', backref='project', lazy='dynamic')
    locations = db.relationship('Location', backref='project', lazy='dynamic')
    schedules = db.relationship('Schedule', backref='project', lazy='dynamic')
    
    def __repr__(self):
        return f'<Project {self.name}>'

# Project access model for user-project relationships
class ProjectAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    
    # Relationships
    project = db.relationship('Project')
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<ProjectAccess {self.project_id}-{self.user_id}>'

# Scene model extracted from screenplay
class Scene(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    scene_number = db.Column(db.String(20))
    description = db.Column(db.Text)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
    estimated_duration = db.Column(db.Float)  # in hours
    priority = db.Column(db.Integer, default=5)  # 1-10 priority scale
    
    # Scene details extracted from screenplay
    int_ext = db.Column(db.String(10))  # INT or EXT
    time_of_day = db.Column(db.String(20))  # DAY, NIGHT, etc.
    page_number = db.Column(db.Float)  # Page number in screenplay
    
    # Relationships
    actor_scenes = db.relationship('ActorScene', backref='scene', lazy='dynamic')
    constraints = db.relationship('SceneConstraint', backref='scene', lazy='dynamic')
    scheduled_scenes = db.relationship('ScheduledScene', backref='scene', lazy='dynamic')
    
    def __repr__(self):
        return f'<Scene {self.scene_number}>'

# Actor model
class Actor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    character_name = db.Column(db.String(100))
    cost_per_day = db.Column(db.Float, default=0)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    
    # Relationships
    actor_scenes = db.relationship('ActorScene', backref='actor', lazy='dynamic')
    availability = db.relationship('ActorAvailability', backref='actor', lazy='dynamic')
    
    def __repr__(self):
        return f'<Actor {self.name} as {self.character_name}>'

# Actor-Scene relationship
class ActorScene(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('actor.id'), nullable=False)
    scene_id = db.Column(db.Integer, db.ForeignKey('scene.id'), nullable=False)
    lines_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<ActorScene {self.actor_id}-{self.scene_id}>'

# Actor availability
class ActorAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('actor.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<ActorAvailability {self.actor_id} on {self.date}>'

# Location model
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    cost_per_day = db.Column(db.Float, default=0)
    
    # Relationships
    scenes = db.relationship('Scene', backref='location', lazy='dynamic')
    availability = db.relationship('LocationAvailability', backref='location', lazy='dynamic')
    
    def __repr__(self):
        return f'<Location {self.name}>'

# Location availability
class LocationAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    is_available = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<LocationAvailability {self.location_id} on {self.date}>'

# Scene constraints
class SceneConstraint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scene_id = db.Column(db.Integer, db.ForeignKey('scene.id'), nullable=False)
    constraint_type = db.Column(db.String(50))  # weather, equipment, special effects, etc.
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SceneConstraint {self.scene_id}: {self.constraint_type}>'

# Schedule model
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    algorithm_used = db.Column(db.String(50))  # TSBM, PSOBM, ACOBM
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_cost = db.Column(db.Float)
    total_duration = db.Column(db.Float)  # in days
    
    # Relationships
    scheduled_scenes = db.relationship('ScheduledScene', backref='schedule', lazy='dynamic')
    notifications = db.relationship('Notification', backref='schedule', lazy='dynamic')
    
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<Schedule {self.name}>'

# Scheduled Scene model
class ScheduledScene(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    scene_id = db.Column(db.Integer, db.ForeignKey('scene.id'), nullable=False)
    shooting_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    estimated_cost = db.Column(db.Float)
    
    def __repr__(self):
        return f'<ScheduledScene {self.scene_id} on {self.shooting_date}>'

# Notification model
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    actor_id = db.Column(db.Integer, db.ForeignKey('actor.id'))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User')
    actor = db.relationship('Actor')
    
    def __repr__(self):
        return f'<Notification to {self.recipient_id or self.actor_id} at {self.created_at}>'
