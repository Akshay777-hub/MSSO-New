import random
import datetime
import os
from app import app, db
from models import User, Project, ProjectAccess, Scene, Actor, Location, ActorScene, Role

def create_demo_screenplay():
    """
    Create a sample screenplay with scenes, locations, and actors for demonstration purposes.
    """
    print("Creating sample screenplay data...")
    
    # Create a director user if none exists
    director = User.query.filter_by(role=Role.DIRECTOR).first()
    if not director:
        director = User(
            username="director",
            email="director@example.com",
            role=Role.DIRECTOR
        )
        director.set_password("password")
        db.session.add(director)
        db.session.flush()
        print("Created director user: director/password")
    
    # Create a project
    project = Project(
        name="Sample Movie",
        description="A demo screenplay for testing",
        creator_id=director.id
    )
    db.session.add(project)
    db.session.flush()
    
    # Add project access for the director
    access = ProjectAccess(
        project_id=project.id,
        user_id=director.id,
        role=Role.DIRECTOR
    )
    db.session.add(access)
    
    # Create locations
    locations = [
        {"name": "Beach House", "address": "123 Ocean Drive", "cost_per_day": 4500.00},
        {"name": "Downtown Cafe", "address": "456 Main Street", "cost_per_day": 2000.00},
        {"name": "Hospital", "address": "789 Medical Avenue", "cost_per_day": 6000.00},
        {"name": "Office Building", "address": "101 Business Plaza", "cost_per_day": 3500.00},
        {"name": "Park", "address": "Green View Park", "cost_per_day": 1500.00},
        {"name": "Apartment", "address": "202 Residential Lane", "cost_per_day": 2200.00}
    ]
    
    location_objects = []
    for loc_data in locations:
        location = Location(
            project_id=project.id,
            name=loc_data["name"],
            address=loc_data["address"],
            cost_per_day=loc_data["cost_per_day"]
        )
        db.session.add(location)
        location_objects.append(location)
    
    db.session.flush()
    
    # Create actors
    actors = [
        {"name": "Emily Johnson", "character_name": "Sarah", "cost_per_day": 8500.00, "email": "emily@example.com", "phone": "555-123-4567"},
        {"name": "Michael Chen", "character_name": "Alex", "cost_per_day": 7500.00, "email": "michael@example.com", "phone": "555-234-5678"},
        {"name": "Sophia Rodriguez", "character_name": "Dr. Maria", "cost_per_day": 6000.00, "email": "sophia@example.com", "phone": "555-345-6789"},
        {"name": "James Wilson", "character_name": "Detective Parker", "cost_per_day": 5500.00, "email": "james@example.com", "phone": "555-456-7890"},
        {"name": "Olivia Smith", "character_name": "Emma", "cost_per_day": 3000.00, "email": "olivia@example.com", "phone": "555-567-8901"},
        {"name": "Daniel Brown", "character_name": "Officer Davis", "cost_per_day": 2500.00, "email": "daniel@example.com", "phone": "555-678-9012"}
    ]
    
    actor_objects = []
    for actor_data in actors:
        actor = Actor(
            project_id=project.id,
            name=actor_data["name"],
            character_name=actor_data["character_name"],
            cost_per_day=actor_data["cost_per_day"],
            email=actor_data["email"],
            phone=actor_data["phone"]
        )
        db.session.add(actor)
        actor_objects.append(actor)
    
    db.session.flush()
    
    # Create scenes
    scenes = [
        {
            "scene_number": "1", 
            "description": "Sarah sits at a cafe, drinking coffee and looking pensive.", 
            "location_id": 2,  # Cafe
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 3.0,
            "priority": 8,
            "actors": [1]  # Sarah
        },
        {
            "scene_number": "2", 
            "description": "Alex enters the cafe, spots Sarah, and approaches her table.", 
            "location_id": 2,  # Cafe
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 2.5,
            "priority": 9,
            "actors": [1, 2]  # Sarah, Alex
        },
        {
            "scene_number": "3", 
            "description": "Sarah and Alex walk through the park, deep in conversation.", 
            "location_id": 5,  # Park
            "int_ext": "EXT", 
            "time_of_day": "DAY",
            "estimated_duration": 4.0,
            "priority": 7,
            "actors": [1, 2]  # Sarah, Alex
        },
        {
            "scene_number": "4", 
            "description": "Detective Parker reviews case files in his office.", 
            "location_id": 4,  # Office Building
            "int_ext": "INT", 
            "time_of_day": "NIGHT",
            "estimated_duration": 3.5,
            "priority": 6,
            "actors": [4]  # Detective Parker
        },
        {
            "scene_number": "5", 
            "description": "Dr. Maria examines a patient while Emma assists.", 
            "location_id": 3,  # Hospital
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 5.0,
            "priority": 8,
            "actors": [3, 5]  # Dr. Maria, Emma
        },
        {
            "scene_number": "6", 
            "description": "Alex arrives at the beach house, looking nervous.", 
            "location_id": 1,  # Beach House
            "int_ext": "EXT", 
            "time_of_day": "EVENING",
            "estimated_duration": 2.0,
            "priority": 5,
            "actors": [2]  # Alex
        },
        {
            "scene_number": "7", 
            "description": "Officer Davis secures the crime scene at the beach house.", 
            "location_id": 1,  # Beach House
            "int_ext": "INT", 
            "time_of_day": "NIGHT",
            "estimated_duration": 3.0,
            "priority": 7,
            "actors": [6]  # Officer Davis
        },
        {
            "scene_number": "8", 
            "description": "Detective Parker questions Alex about his whereabouts.", 
            "location_id": 4,  # Office Building
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 4.5,
            "priority": 9,
            "actors": [2, 4]  # Alex, Detective Parker
        },
        {
            "scene_number": "9", 
            "description": "Sarah packs her belongings in her apartment, looking worried.", 
            "location_id": 6,  # Apartment
            "int_ext": "INT", 
            "time_of_day": "EVENING",
            "estimated_duration": 2.5,
            "priority": 6,
            "actors": [1]  # Sarah
        },
        {
            "scene_number": "10", 
            "description": "Dr. Maria shares important test results with Detective Parker.", 
            "location_id": 3,  # Hospital
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 3.0,
            "priority": 8,
            "actors": [3, 4]  # Dr. Maria, Detective Parker
        },
        {
            "scene_number": "11", 
            "description": "Sarah meets with Emma at the cafe to exchange information.", 
            "location_id": 2,  # Cafe
            "int_ext": "INT", 
            "time_of_day": "MORNING",
            "estimated_duration": 3.5,
            "priority": 7,
            "actors": [1, 5]  # Sarah, Emma
        },
        {
            "scene_number": "12", 
            "description": "Alex and Officer Davis review security footage at the office.", 
            "location_id": 4,  # Office Building
            "int_ext": "INT", 
            "time_of_day": "NIGHT",
            "estimated_duration": 4.0,
            "priority": 8,
            "actors": [2, 6]  # Alex, Officer Davis
        },
        {
            "scene_number": "13", 
            "description": "Final confrontation at the beach house between all main characters.", 
            "location_id": 1,  # Beach House
            "int_ext": "INT", 
            "time_of_day": "NIGHT",
            "estimated_duration": 6.0,
            "priority": 10,
            "actors": [1, 2, 3, 4, 5, 6]  # Everyone
        },
        {
            "scene_number": "14", 
            "description": "Sarah and Alex reconcile at the park bench.", 
            "location_id": 5,  # Park
            "int_ext": "EXT", 
            "time_of_day": "SUNSET",
            "estimated_duration": 3.0,
            "priority": 9,
            "actors": [1, 2]  # Sarah, Alex
        },
        {
            "scene_number": "15", 
            "description": "Epilogue: Detective Parker closes the case file in his office.", 
            "location_id": 4,  # Office Building
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 2.0,
            "priority": 7,
            "actors": [4]  # Detective Parker
        }
    ]
    
    scene_objects = []
    for scene_data in scenes:
        scene = Scene(
            project_id=project.id,
            scene_number=scene_data["scene_number"],
            description=scene_data["description"],
            location_id=scene_data["location_id"],
            int_ext=scene_data["int_ext"],
            time_of_day=scene_data["time_of_day"],
            estimated_duration=scene_data["estimated_duration"],
            priority=scene_data["priority"],
            page_number=float(scene_data["scene_number"])
        )
        db.session.add(scene)
        scene_objects.append(scene)
    
    db.session.flush()
    
    # Create actor-scene relationships
    for i, scene_data in enumerate(scenes):
        for actor_idx in scene_data["actors"]:
            actor_scene = ActorScene(
                actor_id=actor_idx,
                scene_id=scene_objects[i].id,
                lines_count=random.randint(3, 20)
            )
            db.session.add(actor_scene)
    
    # Create actor availability (more available dates for supporting actors)
    today = datetime.date.today()
    for actor in actor_objects:
        # Main actors (top 3) have more limited availability
        is_main_actor = actor.id <= 3
        availability_percentage = 0.6 if is_main_actor else 0.8
        
        # Generate availability for the next 30 days
        for day in range(30):
            date = today + datetime.timedelta(days=day)
            
            # Skip some weekends for everyone
            if date.weekday() >= 5 and random.random() < 0.7:
                continue
                
            # Randomly determine availability based on actor importance
            is_available = random.random() < availability_percentage
            
            # Create availability record
            from models import ActorAvailability
            availability = ActorAvailability(
                actor_id=actor.id,
                date=date,
                is_available=is_available
            )
            db.session.add(availability)
    
    # Create location availability
    for location in location_objects:
        # Generate availability for the next 30 days
        for day in range(30):
            date = today + datetime.timedelta(days=day)
            
            # Skip some weekends for outdoor locations
            is_outdoor = location.id in [1, 5]  # Beach house and park
            if is_outdoor and date.weekday() >= 5 and random.random() < 0.8:
                continue
                
            # Randomly determine availability (90% available)
            is_available = random.random() < 0.9
            
            # Create availability record
            from models import LocationAvailability
            availability = LocationAvailability(
                location_id=location.id,
                date=date,
                is_available=is_available,
                start_time=datetime.time(8, 0),  # 8:00 AM
                end_time=datetime.time(18, 0)    # 6:00 PM
            )
            db.session.add(availability)
    
    db.session.commit()
    print(f"Created sample project '{project.name}' with:")
    print(f"- {len(location_objects)} locations")
    print(f"- {len(actor_objects)} actors")
    print(f"- {len(scene_objects)} scenes")
    print("Sample data created successfully!")

def create_sample_screenplay_for_project(project_id):
    """
    Create sample screenplay data for an existing project using the specific project ID.
    """
    print(f"Creating sample screenplay data for project ID {project_id}...")
    
    import random
    import datetime
    
    # Get project
    project = Project.query.get(project_id)
    if not project:
        raise ValueError(f"Project with ID {project_id} not found")
    
    # Create locations
    locations = [
        {"name": "Beach House", "address": "123 Ocean Drive", "cost_per_day": 4500.00},
        {"name": "Downtown Cafe", "address": "456 Main Street", "cost_per_day": 2000.00},
        {"name": "Hospital", "address": "789 Medical Avenue", "cost_per_day": 6000.00},
        {"name": "Office Building", "address": "101 Business Plaza", "cost_per_day": 3500.00},
        {"name": "Park", "address": "Green View Park", "cost_per_day": 1500.00},
        {"name": "Apartment", "address": "202 Residential Lane", "cost_per_day": 2200.00}
    ]
    
    location_objects = []
    for loc_data in locations:
        location = Location(
            project_id=project_id,
            name=loc_data["name"],
            address=loc_data["address"],
            cost_per_day=loc_data["cost_per_day"]
        )
        db.session.add(location)
        location_objects.append(location)
    
    db.session.flush()
    
    # Create actors
    actors = [
        {"name": "Emily Johnson", "character_name": "Sarah", "cost_per_day": 8500.00, "email": "emily@example.com", "phone": "555-123-4567"},
        {"name": "Michael Chen", "character_name": "Alex", "cost_per_day": 7500.00, "email": "michael@example.com", "phone": "555-234-5678"},
        {"name": "Sophia Rodriguez", "character_name": "Dr. Maria", "cost_per_day": 6000.00, "email": "sophia@example.com", "phone": "555-345-6789"},
        {"name": "James Wilson", "character_name": "Detective Parker", "cost_per_day": 5500.00, "email": "james@example.com", "phone": "555-456-7890"},
        {"name": "Olivia Smith", "character_name": "Emma", "cost_per_day": 3000.00, "email": "olivia@example.com", "phone": "555-567-8901"},
        {"name": "Daniel Brown", "character_name": "Officer Davis", "cost_per_day": 2500.00, "email": "daniel@example.com", "phone": "555-678-9012"}
    ]
    
    actor_objects = []
    for actor_data in actors:
        actor = Actor(
            project_id=project_id,
            name=actor_data["name"],
            character_name=actor_data["character_name"],
            cost_per_day=actor_data["cost_per_day"],
            email=actor_data["email"],
            phone=actor_data["phone"]
        )
        db.session.add(actor)
        actor_objects.append(actor)
    
    db.session.flush()
    
    # Create scenes
    scenes = [
        {
            "scene_number": "1", 
            "description": "Sarah sits at a cafe, drinking coffee and looking pensive.", 
            "location_id": location_objects[1].id,  # Cafe
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 3.0,
            "priority": 8,
            "actors": [actor_objects[0]]  # Sarah
        },
        {
            "scene_number": "2", 
            "description": "Alex enters the cafe, spots Sarah, and approaches her table.", 
            "location_id": location_objects[1].id,  # Cafe
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 2.5,
            "priority": 9,
            "actors": [actor_objects[0], actor_objects[1]]  # Sarah, Alex
        },
        {
            "scene_number": "3", 
            "description": "Sarah and Alex walk through the park, deep in conversation.", 
            "location_id": location_objects[4].id,  # Park
            "int_ext": "EXT", 
            "time_of_day": "DAY",
            "estimated_duration": 4.0,
            "priority": 7,
            "actors": [actor_objects[0], actor_objects[1]]  # Sarah, Alex
        },
        {
            "scene_number": "4", 
            "description": "Detective Parker reviews case files in his office.", 
            "location_id": location_objects[3].id,  # Office Building
            "int_ext": "INT", 
            "time_of_day": "NIGHT",
            "estimated_duration": 3.5,
            "priority": 6,
            "actors": [actor_objects[3]]  # Detective Parker
        },
        {
            "scene_number": "5", 
            "description": "Dr. Maria examines a patient while Emma assists.", 
            "location_id": location_objects[2].id,  # Hospital
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 5.0,
            "priority": 8,
            "actors": [actor_objects[2], actor_objects[4]]  # Dr. Maria, Emma
        },
        {
            "scene_number": "6", 
            "description": "Alex arrives at the beach house, looking nervous.", 
            "location_id": location_objects[0].id,  # Beach House
            "int_ext": "EXT", 
            "time_of_day": "EVENING",
            "estimated_duration": 2.0,
            "priority": 5,
            "actors": [actor_objects[1]]  # Alex
        },
        {
            "scene_number": "7", 
            "description": "Officer Davis secures the crime scene at the beach house.", 
            "location_id": location_objects[0].id,  # Beach House
            "int_ext": "INT", 
            "time_of_day": "NIGHT",
            "estimated_duration": 3.0,
            "priority": 7,
            "actors": [actor_objects[5]]  # Officer Davis
        },
        {
            "scene_number": "8", 
            "description": "Detective Parker questions Alex about his whereabouts.", 
            "location_id": location_objects[3].id,  # Office Building
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 4.5,
            "priority": 9,
            "actors": [actor_objects[1], actor_objects[3]]  # Alex, Detective Parker
        },
        {
            "scene_number": "9", 
            "description": "Sarah packs her belongings in her apartment, looking worried.", 
            "location_id": location_objects[5].id,  # Apartment
            "int_ext": "INT", 
            "time_of_day": "EVENING",
            "estimated_duration": 2.5,
            "priority": 6,
            "actors": [actor_objects[0]]  # Sarah
        },
        {
            "scene_number": "10", 
            "description": "Dr. Maria shares important test results with Detective Parker.", 
            "location_id": location_objects[2].id,  # Hospital
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 3.0,
            "priority": 8,
            "actors": [actor_objects[2], actor_objects[3]]  # Dr. Maria, Detective Parker
        },
        {
            "scene_number": "11", 
            "description": "Sarah meets with Emma at the cafe to exchange information.", 
            "location_id": location_objects[1].id,  # Cafe
            "int_ext": "INT", 
            "time_of_day": "MORNING",
            "estimated_duration": 3.5,
            "priority": 7,
            "actors": [actor_objects[0], actor_objects[4]]  # Sarah, Emma
        },
        {
            "scene_number": "12", 
            "description": "Alex and Officer Davis review security footage at the office.", 
            "location_id": location_objects[3].id,  # Office Building
            "int_ext": "INT", 
            "time_of_day": "NIGHT",
            "estimated_duration": 4.0,
            "priority": 8,
            "actors": [actor_objects[1], actor_objects[5]]  # Alex, Officer Davis
        },
        {
            "scene_number": "13", 
            "description": "Final confrontation at the beach house between all main characters.", 
            "location_id": location_objects[0].id,  # Beach House
            "int_ext": "INT", 
            "time_of_day": "NIGHT",
            "estimated_duration": 6.0,
            "priority": 10,
            "actors": actor_objects  # Everyone
        },
        {
            "scene_number": "14", 
            "description": "Sarah and Alex reconcile at the park bench.", 
            "location_id": location_objects[4].id,  # Park
            "int_ext": "EXT", 
            "time_of_day": "SUNSET",
            "estimated_duration": 3.0,
            "priority": 9,
            "actors": [actor_objects[0], actor_objects[1]]  # Sarah, Alex
        },
        {
            "scene_number": "15", 
            "description": "Epilogue: Detective Parker closes the case file in his office.", 
            "location_id": location_objects[3].id,  # Office Building
            "int_ext": "INT", 
            "time_of_day": "DAY",
            "estimated_duration": 2.0,
            "priority": 7,
            "actors": [actor_objects[3]]  # Detective Parker
        }
    ]
    
    scene_objects = []
    for scene_data in scenes:
        scene = Scene(
            project_id=project_id,
            scene_number=scene_data["scene_number"],
            description=scene_data["description"],
            location_id=scene_data["location_id"],
            int_ext=scene_data["int_ext"],
            time_of_day=scene_data["time_of_day"],
            estimated_duration=scene_data["estimated_duration"],
            priority=scene_data["priority"],
            page_number=float(scene_data["scene_number"])
        )
        db.session.add(scene)
        scene_objects.append(scene)
    
    db.session.flush()
    
    # Create actor-scene relationships
    for i, scene_data in enumerate(scenes):
        for actor in scene_data["actors"]:
            actor_scene = ActorScene(
                actor_id=actor.id,
                scene_id=scene_objects[i].id,
                lines_count=random.randint(3, 20)
            )
            db.session.add(actor_scene)
    
    # Create actor availability (more available dates for supporting actors)
    today = datetime.date.today()
    for actor in actor_objects:
        # Main actors (top 3) have more limited availability
        is_main_actor = actor == actor_objects[0] or actor == actor_objects[1] or actor == actor_objects[2]
        availability_percentage = 0.6 if is_main_actor else 0.8
        
        # Generate availability for the next 30 days
        for day in range(30):
            date = today + datetime.timedelta(days=day)
            
            # Skip some weekends for everyone
            if date.weekday() >= 5 and random.random() < 0.7:
                continue
                
            # Randomly determine availability based on actor importance
            is_available = random.random() < availability_percentage
            
            # Create availability record
            from models import ActorAvailability
            availability = ActorAvailability(
                actor_id=actor.id,
                date=date,
                is_available=is_available
            )
            db.session.add(availability)
    
    # Create location availability
    for location in location_objects:
        # Generate availability for the next 30 days
        for day in range(30):
            date = today + datetime.timedelta(days=day)
            
            # Skip some weekends for outdoor locations
            is_outdoor = location == location_objects[0] or location == location_objects[4]  # Beach house and park
            if is_outdoor and date.weekday() >= 5 and random.random() < 0.8:
                continue
                
            # Randomly determine availability (90% available)
            is_available = random.random() < 0.9
            
            # Create availability record
            from models import LocationAvailability
            availability = LocationAvailability(
                location_id=location.id,
                date=date,
                is_available=is_available,
                start_time=datetime.time(8, 0),  # 8:00 AM
                end_time=datetime.time(18, 0)    # 6:00 PM
            )
            db.session.add(availability)
    
    db.session.commit()
    print(f"Created sample data for project '{project.name}' with:")
    print(f"- {len(location_objects)} locations")
    print(f"- {len(actor_objects)} actors")
    print(f"- {len(scene_objects)} scenes")
    print("Sample data created successfully!")
    return True

if __name__ == "__main__":
    with app.app_context():
        create_demo_screenplay()