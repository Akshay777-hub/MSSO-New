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
    
    # Let's do a more robust extraction using line-by-line processing
    lines = text.split('\n')
    
    # Track scene information
    scene_count = 0
    current_scene = None
    scene_content = []
    
    scene_pattern = r'^(INT|EXT|INT\.\/EXT|I\/E)\.\s+([^-]+)\s*-\s*(DAY|NIGHT|MORNING|EVENING|AFTERNOON|DUSK|DAWN|LATER|CONTINUOUS|SAME TIME|SAME|MOMENTS LATER)$'
    
    # Track current page
    page_number = 1
    
    for line in lines:
        line = line.strip()
        
        # Check if this is a scene header
        match = re.match(scene_pattern, line)
        if match or (line.startswith('INT.') or line.startswith('EXT.') or 
                    line.startswith('INT./EXT.') or line.startswith('I/E.')):
            
            # Save the previous scene if there is one
            if current_scene:
                current_scene['content'] = '\n'.join(scene_content)
                scenes.append(current_scene)
                scene_content = []
            
            # Start a new scene
            scene_count += 1
            
            # Extract components from the line
            if match:
                int_ext = match.group(1)
                location = match.group(2).strip()
                time_of_day = match.group(3).strip()
            else:
                # Manual extraction for headers that don't match the regex
                parts = line.split(' - ')
                
                if len(parts) >= 2:
                    header_part = parts[0].strip()
                    time_part = parts[1].strip()
                    
                    # Extract INT/EXT
                    if header_part.startswith('INT.'):
                        int_ext = 'INT.'
                        location = header_part[4:].strip()
                    elif header_part.startswith('EXT.'):
                        int_ext = 'EXT.'
                        location = header_part[4:].strip()
                    elif header_part.startswith('INT./EXT.'):
                        int_ext = 'INT./EXT.'
                        location = header_part[9:].strip()
                    elif header_part.startswith('I/E.'):
                        int_ext = 'I/E.'
                        location = header_part[4:].strip()
                    else:
                        int_ext = ''
                        location = header_part
                    
                    time_of_day = time_part
                else:
                    # Very basic fallback
                    if line.startswith('INT.'):
                        int_ext = 'INT.'
                        location = line[4:].strip()
                    elif line.startswith('EXT.'):
                        int_ext = 'EXT.'
                        location = line[4:].strip()
                    elif line.startswith('INT./EXT.'):
                        int_ext = 'INT./EXT.'
                        location = line[9:].strip()
                    elif line.startswith('I/E.'):
                        int_ext = 'I/E.'
                        location = line[4:].strip()
                    else:
                        int_ext = ''
                        location = line
                    
                    time_of_day = ''
            
            # Create the new scene object
            current_scene = {
                'scene_number': f"Scene {scene_count}",
                'int_ext': int_ext,
                'location': location,
                'time_of_day': time_of_day,
                'page_number': page_number,
                'content': ''
            }
        elif line.isdigit():
            # This might be a page number
            try:
                num = int(line)
                if num > page_number and num < page_number + 5:  # Reasonable page increment
                    page_number = num
            except ValueError:
                pass
            
            # Add to current scene content
            if current_scene:
                scene_content.append(line)
        else:
            # Add to current scene content
            if current_scene:
                scene_content.append(line)
    
    # Add the last scene
    if current_scene:
        current_scene['content'] = '\n'.join(scene_content)
        scenes.append(current_scene)
    
    # If no scenes were found, try a more lenient approach (direct patterns)
    if not scenes:
        logging.info("No scenes found with standard approach, trying backup method...")
        
        # Simpler regex to find just INT/EXT headers
        basic_headers = re.finditer(r'(INT\.|EXT\.|INT\.\/EXT\.|I\/E)\.\s+([^\n]+)', text)
        scene_matches = list(basic_headers)
        
        for i, match in enumerate(scene_matches):
            int_ext = match.group(1)
            location_and_time = match.group(2).strip()
            
            # Try to split location and time of day
            parts = location_and_time.split(' - ')
            if len(parts) >= 2:
                location = parts[0].strip()
                time_of_day = parts[1].strip()
            else:
                location = location_and_time
                time_of_day = ""
            
            # Get scene content (everything until the next scene header or end of text)
            if i < len(scene_matches) - 1:
                next_match = scene_matches[i+1]
                scene_content = text[match.end():next_match.start()]
            else:
                scene_content = text[match.end():]
            
            scenes.append({
                'scene_number': f"Scene {i+1}",
                'int_ext': int_ext,
                'location': location,
                'time_of_day': time_of_day,
                'page_number': 1,
                'content': scene_content
            })
    
    # Final error check - if still no scenes with locations, provide warning
    if not scenes or not any(scene['location'] for scene in scenes):
        logging.warning("Failed to extract proper scene locations. Scene extraction may be incomplete.")
    
    return scenes

def extract_actors(text, scenes):
    """
    Extract actor/character information from screenplay text and assign arbitrary costs.
    
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
    
    # Get total appearances to calculate relative importance
    total_appearances = sum(count for name, count in character_counter.items() 
                           if count >= 2 and name not in common_uppercase and len(name) > 1)
    
    # Calculate dialog length for each character
    dialog_lengths = {}
    for name in character_counter.keys():
        if name not in common_uppercase and len(name) > 1:
            # Find all dialog for this character
            dialog_pattern = fr'\n\s*{re.escape(name)}\s*\n(.*?)(?=\n\s*[A-Z][A-Z\s\-\']+\s*\n|\Z)'
            dialog_matches = re.finditer(dialog_pattern, text, re.DOTALL)
            dialog_text = " ".join(match.group(1) for match in dialog_matches)
            dialog_lengths[name] = len(dialog_text)
    
    # Characters that appear multiple times are likely actual characters
    import random
    for name, count in character_counter.items():
        if count >= 2 and name not in common_uppercase and len(name) > 1:
            # Use NLP to check if it's likely a person
            doc = nlp(name)
            if any(ent.label_ in ["PERSON", "ORG", "GPE"] for ent in doc.ents) or count >= 3:
                # Calculate relative importance (0.0-1.0)
                importance = min(1.0, count / (total_appearances * 0.3))
                
                # Calculate dialog importance
                dialog_importance = 0.0
                if name in dialog_lengths and sum(dialog_lengths.values()) > 0:
                    dialog_importance = min(1.0, dialog_lengths[name] / (sum(dialog_lengths.values()) * 0.3))
                
                # Combine importance factors
                combined_importance = (importance + dialog_importance) / 2
                
                # Assign cost based on importance
                # Lead actors (high importance) cost more
                base_cost = 1000  # Minimum cost
                
                # Star power factor - leads get much higher pay
                if combined_importance > 0.8:  # Lead actor/actress
                    cost_factor = 50.0  # A-list star
                elif combined_importance > 0.5:  # Supporting role
                    cost_factor = 20.0  # B-list actor
                elif combined_importance > 0.2:  # Minor supporting role
                    cost_factor = 5.0   # Character actor
                else:  # Bit part
                    cost_factor = 1.0   # Day player
                
                # Calculate cost (higher importance = higher cost)
                actor_cost = base_cost * cost_factor * (1 + combined_importance)
                
                # Add some randomness (±30%)
                cost_variation = random.uniform(0.7, 1.3)
                final_cost = round(actor_cost * cost_variation, 2)
                
                actors.append({
                    'name': name,
                    'character_name': name,
                    'appearances': count,
                    'importance': combined_importance,
                    'cost_per_day': final_cost,
                    'email': f"{name.lower().replace(' ', '.')}@example.com",
                    'phone': f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
                })
    
    # Sort by importance (descending)
    actors.sort(key=lambda x: x['importance'], reverse=True)
    return actors

def extract_locations(scenes):
    """Extract unique locations from scene headers and full screenplay and assign arbitrary costs."""
    locations = []
    unique_locations = set()
    
    # Location complexity modifiers
    complexity_keywords = {
        "expensive": ["mansion", "castle", "palace", "penthouse", "yacht", "helicopter", "jet", "airport", 
                     "hospital", "stadium", "concert", "theater", "downtown", "skyline", "skyscraper", 
                     "resort", "lobby", "courtroom", "lab", "laboratory", "military", "base"],
        "moderate": ["restaurant", "bar", "office", "school", "store", "shop", "mall", "park", 
                    "beach", "hotel", "motel", "apartment", "condo", "street", "alley", "road",
                    "café", "cafe", "diner", "pool", "parking", "lot", "garden", "backyard", "front yard"],
        "inexpensive": ["living room", "bedroom", "kitchen", "bathroom", "hallway", "closet", "basement", 
                       "attic", "garage", "yard", "porch", "balcony", "cabin", "shed", "room", "den", 
                       "study", "dining room", "pantry", "toilet", "shower", "foyer", "entry", "doorway"]
    }
    
    # First, extract locations from scene headers
    for scene in scenes:
        location = scene['location'].strip()
        if location and location not in unique_locations:
            unique_locations.add(location)
            
            # Use NLP to categorize location
            doc = nlp(location)
            location_type = "INTERIOR" if scene['int_ext'] in ["INT.", "INT"] else "EXTERIOR"
            if scene['int_ext'] in ["INT./EXT.", "I/E", "EXT./INT."]:
                location_type = "BOTH"
            
            # Determine location category for address field
            location_category = ""
            location_entities = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "ORG", "LOC", "FAC"]]
            if location_entities:
                location_category = f"{location_entities[0]} - "
            
            # Assign arbitrary cost based on complexity
            base_cost = 1000  # Default base cost
            
            # Check for complexity keywords
            location_lower = location.lower()
            for keyword in complexity_keywords["expensive"]:
                if keyword in location_lower:
                    base_cost = 5000 + (len(location) * 10)  # More expensive
                    break
                    
            for keyword in complexity_keywords["moderate"]:
                if keyword in location_lower:
                    base_cost = 2500 + (len(location) * 5)  # Moderate
                    break
                    
            for keyword in complexity_keywords["inexpensive"]:
                if keyword in location_lower:
                    base_cost = 1000 + (len(location) * 2)  # Less expensive
                    break
            
            # Exterior locations tend to be more expensive due to weather/lighting concerns
            if location_type == "EXTERIOR":
                base_cost *= 1.5
            elif location_type == "BOTH":
                base_cost *= 1.25
                
            # Add some randomness (±20%)
            import random
            cost_variation = random.uniform(0.8, 1.2)
            final_cost = round(base_cost * cost_variation, 2)
            
            locations.append({
                'name': location,
                'type': location_type,
                'category': location_category,
                'cost_per_day': final_cost,
                'address': f"{location_type} - {location_category}{location}"
            })
    
    # Now extract additional locations from dialogue and action descriptions
    import re
    
    # Regular expressions for common location phrases
    location_patterns = [
        r"(?:at|in|to|from|near|outside|inside) the ([A-Z][a-z]+ [A-Za-z'\-]+)",  # at the Central Park
        r"(?:at|in|to|from) ([A-Z][a-z]+'s [A-Za-z\-]+)",  # at John's House
        r"EXT\. ([A-Z][A-Za-z'\- ]+) -",  # EXT. CENTRAL PARK -
        r"INT\. ([A-Z][A-Za-z'\- ]+) -",  # INT. JOHN'S HOUSE -
        r"(?:at|in|to|from) ([A-Z][a-z]+ [A-Za-z'\-]+)",  # at Central Park
        r"(?:arrive|travel|go|head) (?:at|to|towards) ([A-Z][A-Za-z'\- ]+)",  # travel to Central Park
    ]
    
    # Look through all scene content for potential locations
    location_candidates = set()
    for scene in scenes:
        content = scene['content']
        
        # Apply all patterns
        for pattern in location_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                location_name = match.group(1).strip()
                # Filter out very short locations and common false positives
                if len(location_name) > 3 and location_name not in ["The End", "The Room", "The Door", "The Car", "A Car"]:
                    location_candidates.add(location_name)
    
    # Process all extracted location candidates
    for location in location_candidates:
        if location not in unique_locations:
            unique_locations.add(location)
            
            # Determine if location is likely interior or exterior
            location_lower = location.lower()
            is_interior = any(keyword in location_lower for keyword in ["room", "house", "building", "office", "apartment"])
            is_exterior = any(keyword in location_lower for keyword in ["street", "park", "beach", "mountain", "garden", "yard"])
            
            location_type = "INTERIOR" if is_interior else "EXTERIOR" if is_exterior else "BOTH"
            
            # Determine category using NLP
            doc = nlp(location)
            location_category = ""
            location_entities = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "ORG", "LOC", "FAC"]]
            if location_entities:
                location_category = f"{location_entities[0]} - "
            
            # Assign arbitrary cost based on complexity
            base_cost = 1500  # Default base cost for extracted locations
            
            # Check for complexity keywords
            for keyword in complexity_keywords["expensive"]:
                if keyword in location_lower:
                    base_cost = 5500 + (len(location) * 12)  # More expensive
                    break
                    
            for keyword in complexity_keywords["moderate"]:
                if keyword in location_lower:
                    base_cost = 3000 + (len(location) * 6)  # Moderate
                    break
                    
            for keyword in complexity_keywords["inexpensive"]:
                if keyword in location_lower:
                    base_cost = 1200 + (len(location) * 3)  # Less expensive
                    break
            
            # Apply interior/exterior multiplier
            if location_type == "EXTERIOR":
                base_cost *= 1.5
            elif location_type == "BOTH":
                base_cost *= 1.25
                
            # Add some randomness (±25%)
            import random
            cost_variation = random.uniform(0.75, 1.25)
            final_cost = round(base_cost * cost_variation, 2)
            
            # Add to the locations list
            locations.append({
                'name': location,
                'type': location_type,
                'category': location_category,
                'cost_per_day': final_cost,
                'address': f"{location_type} - {location_category}{location}"
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
        import random
        import datetime
        from models import ActorAvailability, LocationAvailability
        
        # Get date range for availability (next 60 days)
        today = datetime.date.today()
        date_range = [today + datetime.timedelta(days=i) for i in range(60)]
        
        # First, create all locations
        location_map = {}  # Map location name to Location object
        for location_data in extracted_data['locations']:
            location = Location(
                project_id=project_id,
                name=location_data['name'],
                address=location_data.get('address', f"{location_data['type']} - {location_data['name']}"),
                cost_per_day=location_data.get('cost_per_day', 1000.0)  # Use extracted cost or default
            )
            db.session.add(location)
            db.session.flush()  # Get ID without committing
            location_map[location_data['name']] = location
            
            # Generate random availability for locations
            # More expensive locations are less available
            availability_chance = 0.9 - (min(location.cost_per_day, 10000) / 20000)
            availability_chance = max(0.4, availability_chance)  # Minimum 40% availability
            
            for date in date_range:
                # Skip weekends for some locations
                if date.weekday() >= 5 and random.random() < 0.7:  # 70% of locations unavailable on weekends
                    continue
                    
                # Randomize availability
                if random.random() < availability_chance:
                    # Available this day
                    # Also generate random time restrictions
                    start_hour = random.randint(7, 10)  # Between 7 AM and 10 AM
                    end_hour = random.randint(16, 20)  # Between 4 PM and 8 PM
                    
                    start_time = datetime.time(hour=start_hour, minute=0)
                    end_time = datetime.time(hour=end_hour, minute=0)
                    
                    location_availability = LocationAvailability(
                        location_id=location.id,
                        date=date,
                        start_time=start_time,
                        end_time=end_time,
                        is_available=True
                    )
                    db.session.add(location_availability)
        
        # Create all actors
        actor_map = {}  # Map actor name to Actor object
        for actor_data in extracted_data['actors']:
            actor = Actor(
                project_id=project_id,
                name=actor_data['name'],
                character_name=actor_data['character_name'],
                cost_per_day=actor_data.get('cost_per_day', 1500.0),  # Use extracted cost or default
                email=actor_data.get('email', ''),
                phone=actor_data.get('phone', '')
            )
            db.session.add(actor)
            db.session.flush()  # Get ID without committing
            actor_map[actor_data['name']] = actor
            
            # Generate random availability for actors
            # More important actors (higher cost) have less availability
            importance = actor_data.get('importance', 0.5)
            availability_chance = 0.95 - (importance * 0.5)  # Convert importance to unavailability
            availability_chance = max(0.3, availability_chance)  # At least 30% availability
            
            for date in date_range:
                # Randomize availability with weight by importance
                if random.random() < availability_chance:
                    # Actor is available this day
                    actor_availability = ActorAvailability(
                        actor_id=actor.id,
                        date=date,
                        is_available=True
                    )
                    db.session.add(actor_availability)
        
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
