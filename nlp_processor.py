import PyPDF2
import spacy
import re
import logging
from collections import Counter, defaultdict
from models import Scene, Actor, Location, ActorScene, SceneConstraint
from app import db

# Initialize spaCy NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # If model not found, use small web model
    logging.warning("en_core_web_sm not found, using en_core_web_sm as fallback")
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def process_screenplay(pdf_path):
    """
    Process a screenplay PDF and extract scenes, actors, locations, and constraints.
    
    Args:
        pdf_path (str): Path to the screenplay PDF file
        
    Returns:
        dict: Dictionary containing extracted screenplay data
    """
    logging.info(f"Processing screenplay: {pdf_path}")
    
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    
    # Extract scenes
    scenes = extract_scenes(text)
    
    # Extract actors/characters
    actors = extract_actors(text, scenes)
    
    # Extract locations
    locations = extract_locations(scenes)
    
    # Extract constraints (time-based, weather, special requirements)
    constraints = extract_constraints(text, scenes)
    
    # Extract actor-scene relationships
    actor_scenes = extract_actor_scene_relationships(text, scenes, actors)
    
    logging.info(f"Extracted {len(scenes)} scenes, {len(actors)} actors, {len(locations)} locations")
    
    return {
        'scenes': scenes,
        'actors': actors,
        'locations': locations,
        'constraints': constraints,
        'actor_scenes': actor_scenes
    }

def extract_text_from_pdf(pdf_path):
    """Extract all text content from a PDF file."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n"
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {str(e)}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    return text

def extract_scenes(text):
    """
    Extract scene information from screenplay text.
    
    Scenes in screenplays typically start with INT. or EXT. following by location and time of day.
    """
    scenes = []
    
    # Regex pattern for scene headers (INT./EXT. followed by location and time)
    scene_pattern = r'(INT\.|EXT\.|INT\.\/EXT\.|I\/E)\.?\s+(.*?)(?:\s+-\s+|\s+--\s+|\s+–\s+)?(DAY|NIGHT|MORNING|EVENING|AFTERNOON|DUSK|DAWN|LATER|CONTINUOUS|SAME TIME|SAME|MOMENTS LATER)?'
    
    # Find all scene headers
    scene_matches = re.finditer(scene_pattern, text, re.MULTILINE)
    
    # Track current page
    page_number = 1
    current_pos = 0
    page_breaks = [m.start() for m in re.finditer(r'\n\s*\d+\.?\s*\n', text)]
    
    for i, match in enumerate(scene_matches):
        int_ext = match.group(1)
        location = match.group(2).strip()
        time_of_day = match.group(3) if match.group(3) else ""
        
        # Estimate page number
        while page_breaks and match.start() > page_breaks[0]:
            page_number += 1
            page_breaks.pop(0)
        
        # Find scene number if it exists
        scene_number = f"Scene {i+1}"
        scene_num_match = re.search(r'(\d+[A-Z]?)\s*$', location)
        if scene_num_match:
            scene_number = scene_num_match.group(1)
            location = location[:scene_num_match.start()].strip()
        
        # Get scene content (everything until the next scene header or end of text)
        if i < len(list(re.finditer(scene_pattern, text, re.MULTILINE))) - 1:
            next_match = list(re.finditer(scene_pattern, text, re.MULTILINE))[i+1]
            scene_content = text[match.end():next_match.start()]
        else:
            scene_content = text[match.end():]
        
        scenes.append({
            'scene_number': scene_number,
            'int_ext': int_ext,
            'location': location,
            'time_of_day': time_of_day,
            'page_number': page_number,
            'content': scene_content
        })
    
    return scenes

def extract_actors(text, scenes):
    """
    Extract actor/character information from screenplay text.
    
    Characters in screenplays are typically in ALL CAPS when they speak.
    """
    actors = []
    character_pattern = r'\n\s*([A-Z][A-Z\s\-\']+)(?:\s*\(.*?\))?\s*\n'
    
    # Find all potential character names
    character_matches = re.finditer(character_pattern, text)
    character_names = [match.group(1).strip() for match in character_matches]
    
    # Filter out common non-character uppercase words
    common_uppercase = ["CUT TO", "FADE IN", "FADE OUT", "DISSOLVE TO", "SMASH CUT", 
                        "QUICK CUT", "MATCH CUT", "JUMP CUT", "TITLE", "SUPER", 
                        "ANGLE ON", "CLOSE ON", "MONTAGE", "SERIES OF SHOTS", "BEGIN", "END"]
    
    character_counter = Counter(character_names)
    
    # Characters that appear multiple times are likely actual characters
    for name, count in character_counter.items():
        if count >= 2 and name not in common_uppercase and len(name) > 1:
            # Use NLP to check if it's likely a person
            doc = nlp(name)
            if any(ent.label_ in ["PERSON", "ORG", "GPE"] for ent in doc.ents) or count >= 3:
                actors.append({
                    'name': name,
                    'character_name': name,
                    'appearances': count
                })
    
    return actors

def extract_locations(scenes):
    """Extract unique locations from scene headers."""
    locations = []
    unique_locations = set()
    
    for scene in scenes:
        location = scene['location'].strip()
        if location and location not in unique_locations:
            unique_locations.add(location)
            
            # Use NLP to categorize location
            doc = nlp(location)
            location_type = "INTERIOR" if scene['int_ext'] in ["INT.", "INT"] else "EXTERIOR"
            if scene['int_ext'] in ["INT./EXT.", "I/E", "EXT./INT."]:
                location_type = "BOTH"
            
            locations.append({
                'name': location,
                'type': location_type
            })
    
    return locations

def extract_constraints(text, scenes):
    """
    Extract constraints from screenplay text.
    
    Constraints can include weather conditions, time constraints, special equipment, etc.
    """
    constraints = []
    
    # Weather-related keywords
    weather_terms = ["rain", "snow", "storm", "sunny", "cloudy", "fog", "wind", "hurricane", 
                     "tornado", "blizzard", "heat wave", "lightning", "thunder"]
    
    # Time-related constraints
    time_terms = ["sunrise", "sunset", "dawn", "dusk", "morning", "noon", "afternoon", 
                  "evening", "night", "midnight"]
    
    # Special equipment or effects
    special_terms = ["stunt", "explosion", "fire", "water", "aerial", "underwater", "crane", 
                     "drone", "special effect", "SFX", "VFX", "props", "makeup", "prosthetic"]
    
    for i, scene in enumerate(scenes):
        scene_constraints = []
        content = scene['content'].lower()
        
        # Check for weather constraints
        for term in weather_terms:
            if term in content:
                scene_constraints.append({
                    'type': 'weather',
                    'description': f"Scene requires {term} conditions"
                })
        
        # Check for time constraints (beyond basic day/night)
        for term in time_terms:
            if term in content:
                scene_constraints.append({
                    'type': 'time',
                    'description': f"Scene should be shot during {term}"
                })
        
        # Check for special equipment or effects
        for term in special_terms:
            if term in content:
                scene_constraints.append({
                    'type': 'special',
                    'description': f"Scene requires {term}"
                })
        
        # Add any found constraints
        if scene_constraints:
            constraints.append({
                'scene_number': scene['scene_number'],
                'constraints': scene_constraints
            })
    
    return constraints

def extract_actor_scene_relationships(text, scenes, actors):
    """Determine which actors appear in which scenes."""
    actor_scenes = defaultdict(list)
    
    # Get all character names
    character_names = [actor['name'] for actor in actors]
    
    for i, scene in enumerate(scenes):
        scene_content = scene['content']
        
        # Check each actor against scene content
        for actor in actors:
            # Look for dialog headers with this character
            actor_pattern = fr'\n\s*{re.escape(actor["name"])}\s*\n'
            if re.search(actor_pattern, scene_content):
                actor_scenes[actor['name']].append(scene['scene_number'])
                continue
                
            # Also check for character name mentions in action
            # This is less reliable but can be useful
            if re.search(fr'\b{re.escape(actor["name"])}\b', scene_content):
                actor_scenes[actor['name']].append(scene['scene_number'])
    
    return dict(actor_scenes)

def extract_screenplay_data(extracted_data, project_id):
    """
    Save extracted screenplay data to the database.
    
    Args:
        extracted_data (dict): Dictionary of extracted screenplay data
        project_id (int): ID of the project to associate data with
    
    Returns:
        bool: True if successful
    """
    try:
        # First, create all locations
        location_map = {}  # Map location name to Location object
        for location_data in extracted_data['locations']:
            location = Location(
                project_id=project_id,
                name=location_data['name'],
                address=f"{location_data['type']} - {location_data['name']}"
            )
            db.session.add(location)
            db.session.flush()  # Get ID without committing
            location_map[location_data['name']] = location
        
        # Create all actors
        actor_map = {}  # Map actor name to Actor object
        for actor_data in extracted_data['actors']:
            actor = Actor(
                project_id=project_id,
                name=actor_data['name'],
                character_name=actor_data['character_name']
            )
            db.session.add(actor)
            db.session.flush()  # Get ID without committing
            actor_map[actor_data['name']] = actor
        
        # Create all scenes
        scene_map = {}  # Map scene number to Scene object
        for scene_data in extracted_data['scenes']:
            # Find matching location
            location_id = None
            if scene_data['location'] in location_map:
                location_id = location_map[scene_data['location']].id
            
            # Calculate estimated duration based on content length
            # This is a rough estimate: about 1 minute per page
            content_length = len(scene_data['content'])
            estimated_duration = max(0.25, min(3, content_length / 5000))  # Between 15 min and 3 hours
            
            scene = Scene(
                project_id=project_id,
                scene_number=scene_data['scene_number'],
                description=scene_data['content'][:200] + "..." if len(scene_data['content']) > 200 else scene_data['content'],
                location_id=location_id,
                estimated_duration=estimated_duration,
                int_ext=scene_data['int_ext'],
                time_of_day=scene_data['time_of_day'],
                page_number=scene_data['page_number']
            )
            db.session.add(scene)
            db.session.flush()  # Get ID without committing
            scene_map[scene_data['scene_number']] = scene
        
        # Create actor-scene relationships
        for actor_name, scene_numbers in extracted_data['actor_scenes'].items():
            if actor_name not in actor_map:
                continue
                
            actor = actor_map[actor_name]
            
            for scene_number in scene_numbers:
                if scene_number not in scene_map:
                    continue
                    
                scene = scene_map[scene_number]
                
                # Estimate number of lines
                scene_content = scene.description
                actor_pattern = fr'\n\s*{re.escape(actor_name)}\s*\n'
                lines_count = len(re.findall(actor_pattern, scene_content))
                
                actor_scene = ActorScene(
                    actor_id=actor.id,
                    scene_id=scene.id,
                    lines_count=max(1, lines_count)  # At least 1 line
                )
                db.session.add(actor_scene)
        
        # Create scene constraints
        for constraint_data in extracted_data['constraints']:
            scene_number = constraint_data['scene_number']
            
            if scene_number not in scene_map:
                continue
                
            scene = scene_map[scene_number]
            
            for constraint in constraint_data['constraints']:
                scene_constraint = SceneConstraint(
                    scene_id=scene.id,
                    constraint_type=constraint['type'],
                    description=constraint['description']
                )
                db.session.add(scene_constraint)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error extracting screenplay data: {str(e)}", exc_info=True)
        raise
