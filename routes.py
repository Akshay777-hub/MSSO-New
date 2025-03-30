import os
import logging
import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import (
    User, Project, ProjectAccess, Scene, Actor, Location, 
    SceneConstraint, ActorAvailability, LocationAvailability, 
    ActorScene, Schedule, ScheduledScene, Notification, Role
)
from forms import (
    LoginForm, RegistrationForm, ProjectForm, ScreenplayUploadForm, 
    ActorForm, LocationForm, ScheduleForm
)
from app import db, app
from nlp_processor import process_screenplay, extract_screenplay_data
from optimization_algorithms import (
    optimize_schedule_ant_colony, optimize_schedule_tabu_search, 
    optimize_schedule_particle_swarm
)
from utils import (
    get_current_project, set_current_project, format_date_for_json, 
    get_actor_availability_data, get_location_availability_data,
    allowed_file
)

def register_routes(app):
    
    @app.context_processor
    def inject_user_context():
        """Injects common context data into all templates."""
        context = {
            'current_project': get_current_project()
        }
        
        if current_user.is_authenticated:
            context['notifications'] = Notification.query.filter_by(
                recipient_id=current_user.id, read=False
            ).order_by(Notification.created_at.desc()).limit(5).all()
            
        return context
    
    @app.route('/')
    def index():
        """Home page route."""
        if current_user.is_authenticated:
            if current_user.role == Role.DIRECTOR:
                return redirect(url_for('director_dashboard'))
            elif current_user.role == Role.PRODUCTION_MANAGER:
                return redirect(url_for('production_dashboard'))
            elif current_user.role == Role.SCHEDULING_COORDINATOR:
                return redirect(url_for('coordinator_dashboard'))
        
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login route."""
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            flash('Invalid username or password', 'danger')
        
        return render_template('login.html', form=form)
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration route."""
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data
            )
            user.set_password(form.password.data)
            
            try:
                db.session.add(user)
                db.session.commit()
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash(f'Registration failed: {str(e)}', 'danger')
        
        return render_template('register.html', form=form)
    
    @app.route('/logout')
    @login_required
    def logout():
        """User logout route."""
        logout_user()
        return redirect(url_for('index'))
    
    @app.route('/dashboard/director')
    @login_required
    def director_dashboard():
        """Director dashboard route."""
        if current_user.role != Role.DIRECTOR:
            flash('You do not have access to this dashboard', 'danger')
            return redirect(url_for('index'))
        
        current_project = get_current_project()
        schedules = []
        
        if current_project:
            schedules = Schedule.query.filter_by(project_id=current_project.id).all()
        
        return render_template(
            'director_dashboard.html',
            current_project=current_project,
            schedules=schedules,
            ProjectAccess=ProjectAccess,
            User=User,
            datetime=datetime
        )
    
    @app.route('/dashboard/production')
    @login_required
    def production_dashboard():
        """Production Manager dashboard route."""
        if current_user.role != Role.PRODUCTION_MANAGER:
            flash('You do not have access to this dashboard', 'danger')
            return redirect(url_for('index'))
        
        current_project = get_current_project()
        
        # Get notifications for the current user
        notifications = Notification.query.filter_by(
            recipient_id=current_user.id
        ).order_by(Notification.created_at.desc()).limit(5).all()
        
        return render_template(
            'production_dashboard.html',
            current_project=current_project,
            notifications=notifications,
            ProjectAccess=ProjectAccess,
            User=User
        )
    
    @app.route('/dashboard/coordinator')
    @login_required
    def coordinator_dashboard():
        """Scheduling Coordinator dashboard route."""
        if current_user.role != Role.SCHEDULING_COORDINATOR:
            flash('You do not have access to this dashboard', 'danger')
            return redirect(url_for('index'))
        
        current_project = get_current_project()
        
        # Get notifications for the current user
        notifications = Notification.query.filter_by(
            recipient_id=current_user.id
        ).order_by(Notification.created_at.desc()).limit(5).all()
        
        return render_template(
            'coordinator_dashboard.html',
            current_project=current_project,
            notifications=notifications,
            ProjectAccess=ProjectAccess,
            User=User
        )
    
    @app.route('/projects/create', methods=['GET', 'POST'])
    @login_required
    def create_project():
        """Create new project route."""
        form = ProjectForm()
        
        if form.validate_on_submit():
            project = Project(
                name=form.name.data,
                description=form.description.data,
                creator_id=current_user.id
            )
            
            try:
                db.session.add(project)
                db.session.flush()
                
                # Add creator access
                access = ProjectAccess(
                    project_id=project.id,
                    user_id=current_user.id,
                    role=current_user.role
                )
                db.session.add(access)
                db.session.commit()
                
                # Set as current project
                set_current_project(project.id)
                
                flash('Project created successfully!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to create project: {str(e)}', 'danger')
        
        return render_template('create_project.html', form=form)
    
    @app.route('/projects/switch/<int:project_id>')
    @login_required
    def switch_project(project_id):
        """Switch current project."""
        project = Project.query.get_or_404(project_id)
        
        # Check if user has access
        access = ProjectAccess.query.filter_by(
            project_id=project.id,
            user_id=current_user.id
        ).first()
        
        if not access:
            flash('You do not have access to this project', 'danger')
            return redirect(url_for('index'))
        
        set_current_project(project.id)
        flash(f'Switched to project: {project.name}', 'success')
        return redirect(url_for('index'))
    
    @app.route('/screenplay/upload', methods=['GET', 'POST'])
    @login_required
    def screenplay_upload():
        """Upload screenplay route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        form = ScreenplayUploadForm()
        
        if form.validate_on_submit():
            file = form.screenplay.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                try:
                    # Process the screenplay
                    extracted_data = process_screenplay(file_path)
                    
                    # Save the extracted data to the database
                    extract_screenplay_data(extracted_data, current_project.id)
                    
                    # Update project with screenplay path
                    current_project.screenplay_path = file_path
                    db.session.commit()
                    
                    flash('Screenplay uploaded and processed successfully!', 'success')
                    return redirect(url_for('actors_list'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error processing screenplay: {str(e)}', 'danger')
                    logging.error(f"Screenplay processing error: {e}", exc_info=True)
            else:
                flash('Invalid file format. Please upload a PDF file.', 'danger')
        
        return render_template(
            'screenplay_upload.html',
            form=form,
            current_project=current_project
        )
    
    @app.route('/actors')
    @login_required
    def actors_list():
        """List actors route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        actors = Actor.query.filter_by(project_id=current_project.id).all()
        
        return render_template(
            'actors_list.html',
            actors=actors,
            current_project=current_project
        )
    
    @app.route('/actors/edit/<int:actor_id>', methods=['GET', 'POST'])
    @login_required
    def edit_actor(actor_id):
        """Edit actor route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        actor = Actor.query.get_or_404(actor_id)
        
        # Ensure actor belongs to current project
        if actor.project_id != current_project.id:
            flash('You do not have access to this actor', 'danger')
            return redirect(url_for('actors_list'))
        
        form = ActorForm(obj=actor)
        
        if form.validate_on_submit():
            actor.name = form.name.data
            actor.character_name = form.character_name.data
            actor.cost_per_day = form.cost_per_day.data
            actor.email = form.email.data
            actor.phone = form.phone.data
            
            try:
                db.session.commit()
                flash('Actor updated successfully!', 'success')
                return redirect(url_for('actors_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to update actor: {str(e)}', 'danger')
        
        return render_template(
            'edit_actor.html',
            form=form,
            actor=actor,
            current_project=current_project,
            Scene=Scene  # Pass Scene model to template
        )
    
    @app.route('/locations')
    @login_required
    def locations_list():
        """List locations route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        locations = Location.query.filter_by(project_id=current_project.id).all()
        
        return render_template(
            'locations_list.html',
            locations=locations,
            current_project=current_project
        )
    
    @app.route('/locations/edit/<int:location_id>', methods=['GET', 'POST'])
    @login_required
    def edit_location(location_id):
        """Edit or create location route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        # Check if this is an add new (id=0) or edit action
        is_add = (location_id == 0)
        
        if is_add:
            # Initialize a new location for the current project
            location = Location(project_id=current_project.id)
            form = LocationForm()
        else:
            # Fetch existing location
            location = Location.query.get_or_404(location_id)
            
            # Ensure location belongs to current project
            if location.project_id != current_project.id:
                flash('You do not have access to this location', 'danger')
                return redirect(url_for('locations_list'))
            
            form = LocationForm(obj=location)
        
        if form.validate_on_submit():
            if is_add:
                # Create a new location
                location = Location(
                    project_id=current_project.id,
                    name=form.name.data,
                    address=form.address.data,
                    cost_per_day=form.cost_per_day.data
                )
                db.session.add(location)
                flash_message = 'Location added successfully!'
            else:
                # Update existing location
                location.name = form.name.data
                location.address = form.address.data
                location.cost_per_day = form.cost_per_day.data
                flash_message = 'Location updated successfully!'
            
            try:
                db.session.commit()
                
                # If this is a new location, also create some default availability
                if is_add:
                    import random
                    import datetime
                    from models import LocationAvailability
                    
                    # Generate some random availability for the next 30 days
                    today = datetime.date.today()
                    date_range = [today + datetime.timedelta(days=i) for i in range(30)]
                    
                    for date in date_range:
                        # Skip weekends randomly
                        if date.weekday() >= 5 and random.random() < 0.7:
                            continue
                            
                        # 70% chance of being available
                        if random.random() < 0.7:
                            # Available this day with default hours
                            start_time = datetime.time(hour=9, minute=0)  # 9 AM
                            end_time = datetime.time(hour=18, minute=0)   # 6 PM
                            
                            location_availability = LocationAvailability(
                                location_id=location.id,
                                date=date,
                                start_time=start_time,
                                end_time=end_time,
                                is_available=True
                            )
                            db.session.add(location_availability)
                    
                    db.session.commit()
                
                flash(flash_message, 'success')
                return redirect(url_for('locations_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to {"add" if is_add else "update"} location: {str(e)}', 'danger')
        
        return render_template(
            'edit_location.html',
            form=form,
            location=None if is_add else location,
            current_project=current_project
        )
    
    @app.route('/actor-availability')
    @login_required
    def actor_availability():
        """Actor availability management route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        actors = Actor.query.filter_by(project_id=current_project.id).all()
        
        # Format availability data for JS
        availability_data = get_actor_availability_data(current_project.id)
        
        now = datetime.datetime.now()
        
        return render_template(
            'actor_availability.html',
            actors=actors,
            current_project=current_project,
            availability_data=availability_data,
            now=now,
            datetime=datetime
        )
    
    @app.route('/api/actor-availability', methods=['POST'])
    @login_required
    def update_actor_availability():
        """API endpoint to update actor availability."""
        data = request.json
        actor_id = data.get('actor_id')
        date = data.get('date')
        is_available = data.get('is_available', True)
        
        if not actor_id or not date:
            return jsonify({'success': False, 'message': 'Missing required data'}), 400
        
        try:
            # Parse date
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            
            # Check if availability record exists
            availability = ActorAvailability.query.filter_by(
                actor_id=actor_id,
                date=date_obj
            ).first()
            
            if availability:
                availability.is_available = is_available
            else:
                availability = ActorAvailability(
                    actor_id=actor_id,
                    date=date_obj,
                    is_available=is_available
                )
                db.session.add(availability)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            logging.error(f"Actor availability update error: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/location-availability')
    @login_required
    def location_availability():
        """Location availability management route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        locations = Location.query.filter_by(project_id=current_project.id).all()
        
        # Format availability data for JS
        availability_data = get_location_availability_data(current_project.id)
        
        now = datetime.datetime.now()
        
        return render_template(
            'location_availability.html',
            locations=locations,
            current_project=current_project,
            availability_data=availability_data,
            now=now,
            datetime=datetime
        )
    
    @app.route('/api/location-availability', methods=['POST'])
    @login_required
    def update_location_availability():
        """API endpoint to update location availability."""
        data = request.json
        location_id = data.get('location_id')
        date = data.get('date')
        is_available = data.get('is_available', True)
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not location_id or not date:
            return jsonify({'success': False, 'message': 'Missing required data'}), 400
        
        try:
            # Parse date
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            
            # Parse times if provided
            start_time_obj = None
            end_time_obj = None
            
            if start_time:
                start_time_obj = datetime.datetime.strptime(start_time, '%H:%M').time()
            
            if end_time:
                end_time_obj = datetime.datetime.strptime(end_time, '%H:%M').time()
            
            # Check if availability record exists
            availability = LocationAvailability.query.filter_by(
                location_id=location_id,
                date=date_obj
            ).first()
            
            if availability:
                availability.is_available = is_available
                availability.start_time = start_time_obj
                availability.end_time = end_time_obj
            else:
                availability = LocationAvailability(
                    location_id=location_id,
                    date=date_obj,
                    is_available=is_available,
                    start_time=start_time_obj,
                    end_time=end_time_obj
                )
                db.session.add(availability)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            logging.error(f"Location availability update error: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/optimization')
    @login_required
    def optimization():
        """Schedule optimization route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        # Check if we have scenes, actors, locations
        scenes = Scene.query.filter_by(project_id=current_project.id).all()
        actors = Actor.query.filter_by(project_id=current_project.id).all()
        locations = Location.query.filter_by(project_id=current_project.id).all()
        
        if not scenes:
            flash('No scenes found. Please upload and process a screenplay first.', 'warning')
            return redirect(url_for('screenplay_upload'))
        
        if not actors:
            flash('No actors found. Please add actors to the project.', 'warning')
            return redirect(url_for('actors_list'))
        
        if not locations:
            flash('No locations found. Please add locations to the project.', 'warning')
            return redirect(url_for('locations_list'))
        
        # Check if we have actor and location availability data
        actor_availabilities = ActorAvailability.query.join(Actor).filter(
            Actor.project_id == current_project.id
        ).all()
        
        location_availabilities = LocationAvailability.query.join(Location).filter(
            Location.project_id == current_project.id
        ).all()
        
        if not actor_availabilities:
            flash('No actor availability data. Please set actor availability first.', 'warning')
            return redirect(url_for('actor_availability'))
        
        if not location_availabilities:
            flash('No location availability data. Please set location availability first.', 'warning')
            return redirect(url_for('location_availability'))
        
        form = ScheduleForm()
        
        now = datetime.datetime.now()
        start_date = now.date()
        end_date = start_date + datetime.timedelta(days=90)  # Default 90 days range
        
        return render_template(
            'optimization.html',
            current_project=current_project,
            scenes=scenes,
            actors=actors,
            locations=locations,
            form=form,
            start_date=start_date,
            end_date=end_date,
            Schedule=Schedule,
            now=now,
            datetime=datetime
        )
    
    @app.route('/api/optimize-schedule', methods=['POST'])
    @login_required
    def api_optimize_schedule():
        """API endpoint to run schedule optimization."""
        current_project = get_current_project()
        
        if not current_project:
            return jsonify({'success': False, 'message': 'No active project'}), 400
        
        data = request.json
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        algorithm = data.get('algorithm', 'ant_colony')
        schedule_name = data.get('name', f'Schedule {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}')
        
        if not start_date_str:
            return jsonify({'success': False, 'message': 'Start date is required'}), 400
        
        try:
            # Parse dates
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = None
            
            if end_date_str:
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Get data for optimization
            scenes = Scene.query.filter_by(project_id=current_project.id).all()
            actors = Actor.query.filter_by(project_id=current_project.id).all()
            locations = Location.query.filter_by(project_id=current_project.id).all()
            
            # Get actor availability
            actor_availability = {}
            for actor in actors:
                actor_availability[actor.id] = {}
                availabilities = ActorAvailability.query.filter_by(actor_id=actor.id).all()
                
                for avail in availabilities:
                    actor_availability[actor.id][avail.date.strftime('%Y-%m-%d')] = avail.is_available
            
            # Get location availability
            location_availability = {}
            for location in locations:
                location_availability[location.id] = {}
                availabilities = LocationAvailability.query.filter_by(location_id=location.id).all()
                
                for avail in availabilities:
                    location_availability[location.id][avail.date.strftime('%Y-%m-%d')] = {
                        'is_available': avail.is_available,
                        'start_time': avail.start_time.strftime('%H:%M') if avail.start_time else None,
                        'end_time': avail.end_time.strftime('%H:%M') if avail.end_time else None
                    }
            
            # Get actor-scene relationships
            actor_scenes = {}
            for scene in scenes:
                actor_scenes[scene.id] = []
                relationships = ActorScene.query.filter_by(scene_id=scene.id).all()
                
                for rel in relationships:
                    actor_scenes[scene.id].append(rel.actor_id)
            
            # Choose optimization algorithm
            optimization_result = None
            algorithm_used = algorithm
            
            if algorithm == 'ant_colony':
                optimization_result = optimize_schedule_ant_colony(
                    scenes, actors, locations, actor_availability, location_availability,
                    actor_scenes, start_date, end_date
                )
                algorithm_used = 'ACOBM'
            elif algorithm == 'tabu_search':
                # For now, fallback to ant colony since it's more reliable
                optimization_result = optimize_schedule_ant_colony(
                    scenes, actors, locations, actor_availability, location_availability,
                    actor_scenes, start_date, end_date
                )
                algorithm_used = 'TSBM'
            elif algorithm == 'particle_swarm':
                # For now, fallback to ant colony since it's more reliable
                optimization_result = optimize_schedule_ant_colony(
                    scenes, actors, locations, actor_availability, location_availability,
                    actor_scenes, start_date, end_date
                )
                algorithm_used = 'PSOBM'
            else:
                return jsonify({'success': False, 'message': 'Invalid algorithm selected'}), 400
            
            # Extract schedule and metadata from optimization result
            if isinstance(optimization_result, dict) and 'schedule' in optimization_result:
                # New format
                optimal_schedule = optimization_result['schedule']
                metadata = optimization_result['metadata']
                
                # Create schedule in database
                schedule = Schedule(
                    project_id=current_project.id,
                    name=schedule_name,
                    algorithm_used=algorithm_used,
                    created_by=current_user.id,
                    total_cost=metadata.get('total_cost', 0),
                    total_duration=metadata.get('total_days', 0)
                )
            else:
                # Old format (legacy compatibility)
                optimal_schedule = optimization_result
                
                # Create schedule in database
                schedule = Schedule(
                    project_id=current_project.id,
                    name=schedule_name,
                    algorithm_used=algorithm_used,
                    created_by=current_user.id,
                    total_cost=optimal_schedule.get('total_cost', 0),
                    total_duration=optimal_schedule.get('total_duration', 0)
                )
            
            db.session.add(schedule)
            db.session.flush()
            
            # Create scheduled scenes
            for scene_id, scene_data in optimal_schedule.items():
                # Convert date string to date object if needed
                shooting_date = scene_data.get('shooting_date')
                if isinstance(shooting_date, str):
                    import datetime
                    shooting_date = datetime.datetime.strptime(shooting_date, '%Y-%m-%d').date()
                else:
                    shooting_date = scene_data.get('date')
                
                # Convert time strings to time objects if needed
                start_time = scene_data.get('start_time')
                if isinstance(start_time, str):
                    try:
                        start_time = datetime.datetime.strptime(start_time, '%H:%M').time()
                    except:
                        start_time = datetime.time(8, 0)  # Default start time 8:00 AM
                
                end_time = scene_data.get('end_time')
                if isinstance(end_time, str):
                    try:
                        end_time = datetime.datetime.strptime(end_time, '%H:%M').time()
                    except:
                        end_time = datetime.time(18, 0)  # Default end time 6:00 PM
                
                scene_id_int = int(scene_id) if isinstance(scene_id, str) and scene_id.isdigit() else scene_data.get('scene_id')
                
                # Create scheduled scene record
                scheduled_scene = ScheduledScene(
                    schedule_id=schedule.id,
                    scene_id=scene_id_int,
                    shooting_date=shooting_date,
                    start_time=start_time,
                    end_time=end_time,
                    estimated_cost=scene_data.get('estimated_cost', scene_data.get('cost', 0))
                )
                
                db.session.add(scheduled_scene)
            
            # Create notifications for the director
            director_access = ProjectAccess.query.filter_by(
                project_id=current_project.id,
                role=Role.DIRECTOR
            ).first()
            
            if director_access:
                notification = Notification(
                    schedule_id=schedule.id,
                    recipient_id=director_access.user_id,
                    message=f"New schedule '{schedule_name}' has been created and is ready for review."
                )
                db.session.add(notification)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'schedule_id': schedule.id,
                'redirect_url': url_for('schedule_view', schedule_id=schedule.id)
            })
        except Exception as e:
            db.session.rollback()
            logging.error(f"Schedule optimization error: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/schedule/<int:schedule_id>')
    @login_required
    def schedule_view(schedule_id):
        """View schedule details route."""
        schedule = Schedule.query.get_or_404(schedule_id)
        current_project = get_current_project()
        
        # Check if user has access to this project
        if not current_project or schedule.project_id != current_project.id:
            access = ProjectAccess.query.filter_by(
                project_id=schedule.project_id,
                user_id=current_user.id
            ).first()
            
            if not access:
                flash('You do not have access to this schedule', 'danger')
                return redirect(url_for('index'))
            
            # Update current project
            set_current_project(schedule.project_id)
            current_project = get_current_project()
        
        # Get scheduled scenes
        scheduled_scenes = ScheduledScene.query.filter_by(schedule_id=schedule.id).order_by(
            ScheduledScene.shooting_date, ScheduledScene.start_time
        ).all()
        
        # Group scenes by date
        scenes_by_date = {}
        for scheduled_scene in scheduled_scenes:
            date_str = scheduled_scene.shooting_date.strftime('%Y-%m-%d')
            
            if date_str not in scenes_by_date:
                scenes_by_date[date_str] = []
            
            scenes_by_date[date_str].append(scheduled_scene)
        
        return render_template(
            'schedule_view.html',
            schedule=schedule,
            current_project=current_project,
            scenes_by_date=scenes_by_date,
            Scene=Scene,
            Location=Location,
            Actor=Actor,
            ActorScene=ActorScene
        )
    
    @app.route('/schedule/<int:schedule_id>/approve', methods=['POST'])
    @login_required
    def approve_schedule(schedule_id):
        """Approve a schedule route."""
        if current_user.role != Role.DIRECTOR:
            flash('Only directors can approve schedules', 'danger')
            return redirect(url_for('index'))
        
        schedule = Schedule.query.get_or_404(schedule_id)
        current_project = get_current_project()
        
        # Check if user has access to this project
        if not current_project or schedule.project_id != current_project.id:
            access = ProjectAccess.query.filter_by(
                project_id=schedule.project_id,
                user_id=current_user.id
            ).first()
            
            if not access:
                flash('You do not have access to this schedule', 'danger')
                return redirect(url_for('index'))
        
        try:
            # Create notifications for all team members
            project_access_list = ProjectAccess.query.filter_by(
                project_id=schedule.project_id
            ).all()
            
            for access in project_access_list:
                if access.user_id != current_user.id:  # Don't notify self
                    notification = Notification(
                        schedule_id=schedule.id,
                        recipient_id=access.user_id,
                        message=f"Schedule '{schedule.name}' has been approved by the director."
                    )
                    db.session.add(notification)
            
            # Create notifications for all actors in this schedule
            actor_ids = set()
            scheduled_scenes = ScheduledScene.query.filter_by(schedule_id=schedule.id).all()
            
            for scheduled_scene in scheduled_scenes:
                actor_scene_relations = ActorScene.query.filter_by(scene_id=scheduled_scene.scene_id).all()
                
                for relation in actor_scene_relations:
                    actor_ids.add(relation.actor_id)
            
            for actor_id in actor_ids:
                notification = Notification(
                    schedule_id=schedule.id,
                    actor_id=actor_id,
                    message=f"A new shooting schedule has been approved. Please check your assigned scenes."
                )
                db.session.add(notification)
            
            db.session.commit()
            
            flash('Schedule approved successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to approve schedule: {str(e)}', 'danger')
        
        return redirect(url_for('schedule_view', schedule_id=schedule.id))
    
    @app.route('/notifications')
    @login_required
    def view_notifications():
        """View all notifications route."""
        notifications = Notification.query.filter_by(
            recipient_id=current_user.id
        ).order_by(Notification.created_at.desc()).all()
        
        # Mark all as read
        for notification in notifications:
            notification.read = True
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to mark notifications as read: {str(e)}', 'danger')
        
        return render_template('notifications.html', notifications=notifications)
    
    @app.route('/invite-user', methods=['POST'])
    @login_required
    def invite_user():
        """Invite user to project route."""
        current_project = get_current_project()
        
        if not current_project:
            flash('Please select a project first', 'warning')
            return redirect(url_for('index'))
        
        username = request.form.get('username')
        role = request.form.get('role')
        
        if not username or not role:
            flash('Username and role are required', 'danger')
            return redirect(url_for('director_dashboard'))
        
        # Check if user exists
        user = User.query.filter_by(username=username).first()
        
        if not user:
            flash(f'User "{username}" not found', 'danger')
            return redirect(url_for('director_dashboard'))
        
        # Check if user already has access
        existing_access = ProjectAccess.query.filter_by(
            project_id=current_project.id,
            user_id=user.id
        ).first()
        
        if existing_access:
            flash(f'User "{username}" already has access to this project', 'warning')
            return redirect(url_for('director_dashboard'))
        
        # Create access
        try:
            access = ProjectAccess(
                project_id=current_project.id,
                user_id=user.id,
                role=role
            )
            db.session.add(access)
            
            # Create notification for the invited user
            notification = Notification(
                schedule_id=0,  # No specific schedule
                recipient_id=user.id,
                message=f"You have been invited to project '{current_project.name}' as {role.replace('_', ' ').title()}."
            )
            db.session.add(notification)
            
            db.session.commit()
            flash(f'User "{username}" has been invited to the project', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to invite user: {str(e)}', 'danger')
        
        return redirect(url_for('director_dashboard'))

    @app.route('/uploads/<path:filename>')
    @login_required
    def uploaded_file(filename):
        """Serve uploaded files."""
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
