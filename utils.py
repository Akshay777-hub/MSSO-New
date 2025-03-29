import datetime
import json
from flask import session
from models import (
    Project, ProjectAccess, ActorAvailability, LocationAvailability,
    Actor, Location
)
from flask_login import current_user

# Allowed file extensions for screenplay uploads
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if a file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_current_project():
    """Get the current active project for the user."""
    if not current_user.is_authenticated:
        return None
    
    project_id = session.get('current_project_id')
    
    if not project_id:
        # Find the first project the user has access to
        project_access = ProjectAccess.query.filter_by(user_id=current_user.id).first()
        
        if project_access:
            project_id = project_access.project_id
            session['current_project_id'] = project_id
    
    if project_id:
        return Project.query.get(project_id)
    
    return None

def set_current_project(project_id):
    """Set the current active project for the user."""
    session['current_project_id'] = project_id

def format_date_for_json(date_obj):
    """Format a date object for JSON serialization."""
    if isinstance(date_obj, datetime.date):
        return date_obj.strftime('%Y-%m-%d')
    return None

def get_actor_availability_data(project_id):
    """Get actor availability data formatted for JS."""
    actors = Actor.query.filter_by(project_id=project_id).all()
    
    availability_data = {}
    
    for actor in actors:
        availability_data[actor.id] = {}
        
        # Get all availability records
        availabilities = ActorAvailability.query.filter_by(actor_id=actor.id).all()
        
        for avail in availabilities:
            date_str = format_date_for_json(avail.date)
            availability_data[actor.id][date_str] = avail.is_available
    
    return json.dumps(availability_data)

def get_location_availability_data(project_id):
    """Get location availability data formatted for JS."""
    locations = Location.query.filter_by(project_id=project_id).all()
    
    availability_data = {}
    
    for location in locations:
        availability_data[location.id] = {}
        
        # Get all availability records
        availabilities = LocationAvailability.query.filter_by(location_id=location.id).all()
        
        for avail in availabilities:
            date_str = format_date_for_json(avail.date)
            
            # Format times
            start_time = avail.start_time.strftime('%H:%M') if avail.start_time else None
            end_time = avail.end_time.strftime('%H:%M') if avail.end_time else None
            
            availability_data[location.id][date_str] = {
                'is_available': avail.is_available,
                'start_time': start_time,
                'end_time': end_time
            }
    
    return json.dumps(availability_data)
