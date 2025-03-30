import datetime
import random
import copy
import numpy as np
import logging
from itertools import permutations
from collections import defaultdict

def optimize_schedule_tabu_search(scenes, actors, locations, actor_availability, location_availability, actor_scenes, start_date, end_date=None):
    """
    Tabu Search-Based Method for schedule optimization.
    
    Args:
        scenes: List of Scene objects
        actors: List of Actor objects
        locations: List of Location objects
        actor_availability: Dict mapping actor_id to availability by date
        location_availability: Dict mapping location_id to availability by date
        actor_scenes: Dict mapping scene_id to list of actor_ids
        start_date: First possible shooting date
        end_date: Last possible shooting date (optional)
        
    Returns:
        Dict mapping scene_id to scheduling information
    """
    logging.info("Starting Tabu Search optimization")
    
    # If no end date specified, set a reasonable range
    if not end_date:
        end_date = start_date + datetime.timedelta(days=len(scenes) * 2)
    
    # Initialize parameters
    tabu_tenure = min(20, len(scenes) // 2)  # How long moves stay in tabu list
    max_iterations = 1000
    max_no_improvement = 100
    
    # Generate all available dates
    available_dates = []
    current_date = start_date
    while current_date <= end_date:
        available_dates.append(current_date)
        current_date += datetime.timedelta(days=1)
    
    # Initial solution: random assignment
    current_solution = generate_initial_solution(scenes, available_dates, actor_scenes, actor_availability, location_availability)
    
    # Evaluate initial solution
    current_cost = evaluate_solution(current_solution, scenes, actors, locations, actor_scenes)
    best_solution = copy.deepcopy(current_solution)
    best_cost = current_cost
    
    # Tabu list (moves that are prohibited)
    tabu_list = []
    
    # Iteration control
    iterations = 0
    iterations_no_improvement = 0
    
    while iterations < max_iterations and iterations_no_improvement < max_no_improvement:
        iterations += 1
        
        # Generate neighborhood (possible moves)
        neighbors = generate_neighbors(current_solution, scenes, available_dates, actor_scenes, actor_availability, location_availability)
        
        # Find best non-tabu move
        best_neighbor = None
        best_neighbor_cost = float('inf')
        
        for neighbor in neighbors:
            move_key = (neighbor['scene_id'], neighbor['date'])
            
            # Check if move is tabu
            if move_key in tabu_list:
                continue
                
            # Evaluate neighbor
            neighbor_cost = evaluate_solution(neighbor['solution'], scenes, actors, locations, actor_scenes)
            
            # Update best neighbor
            if neighbor_cost < best_neighbor_cost:
                best_neighbor = neighbor
                best_neighbor_cost = neighbor_cost
        
        # If no valid move found, break
        if not best_neighbor:
            break
            
        # Make the move
        current_solution = best_neighbor['solution']
        current_cost = best_neighbor_cost
        
        # Add move to tabu list
        move_key = (best_neighbor['scene_id'], best_neighbor['date'])
        tabu_list.append(move_key)
        
        # Remove old entries from tabu list
        if len(tabu_list) > tabu_tenure:
            tabu_list.pop(0)
        
        # Update best solution
        if current_cost < best_cost:
            best_solution = copy.deepcopy(current_solution)
            best_cost = current_cost
            iterations_no_improvement = 0
        else:
            iterations_no_improvement += 1
    
    logging.info(f"Tabu Search completed after {iterations} iterations")
    
    # Convert solution to the expected return format
    return format_solution(best_solution, scenes, actors, locations)

def optimize_schedule_particle_swarm(scenes, actors, locations, actor_availability, location_availability, actor_scenes, start_date, end_date=None):
    """
    Particle Swarm Optimization-Based Method for schedule optimization.
    
    Args:
        scenes: List of Scene objects
        actors: List of Actor objects
        locations: List of Location objects
        actor_availability: Dict mapping actor_id to availability by date
        location_availability: Dict mapping location_id to availability by date
        actor_scenes: Dict mapping scene_id to list of actor_ids
        start_date: First possible shooting date
        end_date: Last possible shooting date (optional)
        
    Returns:
        Dict mapping scene_id to scheduling information
    """
    logging.info("Starting Particle Swarm optimization")
    
    # If no end date specified, set a reasonable range
    if not end_date:
        end_date = start_date + datetime.timedelta(days=len(scenes) * 2)
    
    # Initialize parameters
    num_particles = min(30, len(scenes) * 2)
    max_iterations = 100
    max_no_improvement = 20
    inertia_weight = 0.7
    cognitive_weight = 1.5
    social_weight = 1.5
    
    # Generate all available dates
    available_dates = []
    current_date = start_date
    while current_date <= end_date:
        available_dates.append(current_date)
        current_date += datetime.timedelta(days=1)
    
    # Initialize particles
    particles = []
    for i in range(num_particles):
        particle = {
            'position': generate_initial_solution(scenes, available_dates, actor_scenes, actor_availability, location_availability),
            'velocity': {},
            'best_position': None,
            'best_cost': float('inf')
        }
        
        # Evaluate initial position
        cost = evaluate_solution(particle['position'], scenes, actors, locations, actor_scenes)
        particle['best_position'] = copy.deepcopy(particle['position'])
        particle['best_cost'] = cost
        
        particles.append(particle)
    
    # Global best
    global_best_position = None
    global_best_cost = float('inf')
    
    for particle in particles:
        if particle['best_cost'] < global_best_cost:
            global_best_position = copy.deepcopy(particle['best_position'])
            global_best_cost = particle['best_cost']
    
    # Iteration control
    iterations = 0
    iterations_no_improvement = 0
    
    while iterations < max_iterations and iterations_no_improvement < max_no_improvement:
        iterations += 1
        improved = False
        
        for particle in particles:
            # Update velocity and position
            for scene_id in particle['position']:
                # Initialize velocity if not exists
                if scene_id not in particle['velocity']:
                    particle['velocity'][scene_id] = {}
                    for key in particle['position'][scene_id]:
                        if key in ['date', 'start_time', 'end_time']:
                            particle['velocity'][scene_id][key] = 0
                
                # PSO velocity update
                r1 = random.random()
                r2 = random.random()
                
                # Date velocity
                particle['velocity'][scene_id]['date'] = (
                    inertia_weight * particle['velocity'][scene_id]['date'] +
                    cognitive_weight * r1 * (particle['best_position'][scene_id]['date'] - particle['position'][scene_id]['date']).days +
                    social_weight * r2 * (global_best_position[scene_id]['date'] - particle['position'][scene_id]['date']).days
                )
                
                # Update position
                new_date_idx = max(0, min(len(available_dates) - 1, 
                                      available_dates.index(particle['position'][scene_id]['date']) + 
                                      int(particle['velocity'][scene_id]['date'])))
                particle['position'][scene_id]['date'] = available_dates[new_date_idx]
                
                # Time velocity updates (simplified)
                # In practice, we'd need to handle time slots properly
                for time_key in ['start_time', 'end_time']:
                    if isinstance(particle['position'][scene_id][time_key], datetime.time):
                        hrs = particle['position'][scene_id][time_key].hour
                        mins = particle['position'][scene_id][time_key].minute
                        
                        particle['velocity'][scene_id][time_key] = (
                            inertia_weight * particle['velocity'][scene_id][time_key]
                        )
                        
                        new_minutes = max(0, min(23*60, hrs*60 + mins + int(particle['velocity'][scene_id][time_key])))
                        new_hrs = new_minutes // 60
                        new_mins = new_minutes % 60
                        
                        particle['position'][scene_id][time_key] = datetime.time(new_hrs, new_mins)
            
            # Check feasibility and repair if needed
            repair_solution(particle['position'], scenes, actor_scenes, actor_availability, location_availability)
            
            # Evaluate new position
            cost = evaluate_solution(particle['position'], scenes, actors, locations, actor_scenes)
            
            # Update particle best
            if cost < particle['best_cost']:
                particle['best_position'] = copy.deepcopy(particle['position'])
                particle['best_cost'] = cost
                
                # Update global best
                if cost < global_best_cost:
                    global_best_position = copy.deepcopy(particle['position'])
                    global_best_cost = cost
                    improved = True
        
        if improved:
            iterations_no_improvement = 0
        else:
            iterations_no_improvement += 1
    
    logging.info(f"PSO completed after {iterations} iterations")
    
    # Convert solution to the expected return format
    return format_solution(global_best_position, scenes, actors, locations)

def optimize_schedule_ant_colony(scenes, actors, locations, actor_availability, location_availability, actor_scenes, start_date, end_date=None):
    """
    Ant Colony Optimization-Based Method for schedule optimization.
    
    Args:
        scenes: List of Scene objects
        actors: List of Actor objects
        locations: List of Location objects
        actor_availability: Dict mapping actor_id to availability by date
        location_availability: Dict mapping location_id to availability by date
        actor_scenes: Dict mapping scene_id to list of actor_ids
        start_date: First possible shooting date
        end_date: Last possible shooting date (optional)
        
    Returns:
        Dict mapping scene_id to scheduling information
    """
    import logging
    
    # Safety checks
    if not scenes:
        logging.warning("No scenes provided for scheduling")
        return {'scenes': {}, 'total_cost': 0, 'total_duration': 0}
        
    if not actors:
        logging.warning("No actors provided for scheduling")
        
    if not locations:
        logging.warning("No locations provided for scheduling")
        
    # Verify actor availability data
    if not actor_availability:
        logging.warning("No actor availability data provided, using defaults")
        # Set default availability (all actors available all dates)
        actor_availability = {}
        for actor in actors:
            actor_availability[actor.id] = {}
            current_date = start_date
            while current_date <= (end_date or start_date + datetime.timedelta(days=30)):
                actor_availability[actor.id][current_date.strftime('%Y-%m-%d')] = True
                current_date += datetime.timedelta(days=1)
                
    # Verify location availability data
    if not location_availability:
        logging.warning("No location availability data provided, using defaults")
        # Set default availability (all locations available all dates)
        location_availability = {}
        for location in locations:
            location_availability[location.id] = {}
            current_date = start_date
            while current_date <= (end_date or start_date + datetime.timedelta(days=30)):
                location_availability[location.id][current_date.strftime('%Y-%m-%d')] = {
                    'is_available': True,
                    'start_time': '08:00',
                    'end_time': '18:00'
                }
                current_date += datetime.timedelta(days=1)
    
    logging.info("Starting Ant Colony optimization")
    
    # If no end date specified, set a reasonable range
    if not end_date:
        end_date = start_date + datetime.timedelta(days=len(scenes) * 2)
    
    # ACO parameters
    num_ants = min(20, len(scenes))
    max_iterations = 100
    evaporation_rate = 0.1
    alpha = 1.0  # pheromone influence
    beta = 2.0   # heuristic influence
    
    # Generate all available dates
    available_dates = []
    current_date = start_date
    while current_date <= end_date:
        available_dates.append(current_date)
        current_date += datetime.timedelta(days=1)
    
    # Initialize pheromone matrix
    # For each scene, we have a pheromone level for each possible date
    pheromone = {}
    for scene in scenes:
        pheromone[scene.id] = {}
        for date in available_dates:
            pheromone[scene.id][date.strftime('%Y-%m-%d')] = 1.0
    
    # Track best solution
    best_solution = None
    best_cost = float('inf')
    
    # Main ACO loop
    for iteration in range(max_iterations):
        # Solutions for this iteration
        solutions = []
        
        # Each ant builds a solution
        for ant in range(num_ants):
            # Build solution by assigning scenes to dates
            solution = {}
            scene_order = list(scenes)
            random.shuffle(scene_order)  # Randomize order for diversity
            
            for scene in scene_order:
                # Calculate probabilities for each date
                probabilities = []
                valid_dates = []
                
                for date in available_dates:
                    date_str = date.strftime('%Y-%m-%d')
                    
                    # Check feasibility (actor & location availability)
                    is_feasible = True
                    
                    # Check actor availability
                    for actor_id in actor_scenes.get(scene.id, []):
                        if actor_id in actor_availability and date_str in actor_availability[actor_id]:
                            if not actor_availability[actor_id][date_str]:
                                is_feasible = False
                                break
                    
                    # Check location availability
                    if is_feasible and scene.location_id:
                        if (scene.location_id in location_availability and 
                            date_str in location_availability[scene.location_id]):
                            if not location_availability[scene.location_id][date_str]['is_available']:
                                is_feasible = False
                    
                    if is_feasible:
                        # Heuristic value (e.g., prioritize earlier dates)
                        heuristic = 1.0 / (1 + (date - start_date).days)
                        
                        # Calculate probability based on pheromone and heuristic
                        prob = (pheromone[scene.id][date_str] ** alpha) * (heuristic ** beta)
                        probabilities.append(prob)
                        valid_dates.append(date)
                
                # If no valid date, pick randomly
                if not valid_dates:
                    selected_date = random.choice(available_dates)
                else:
                    # Select date based on probabilities
                    total = sum(probabilities)
                    if total == 0:
                        selected_date = random.choice(valid_dates)
                    else:
                        normalized_probs = [p/total for p in probabilities]
                        selected_idx = np.random.choice(len(valid_dates), p=normalized_probs)
                        selected_date = valid_dates[selected_idx]
                
                # Assign start/end times
                start_time = datetime.time(9, 0)  # Default 9:00 AM
                estimated_duration = scene.estimated_duration or 1.0  # Hours
                
                # Calculate end time
                hours = int(estimated_duration)
                minutes = int((estimated_duration - hours) * 60)
                end_hour = start_time.hour + hours
                end_minute = start_time.minute + minutes
                
                # Adjust for overflow
                if end_minute >= 60:
                    end_hour += 1
                    end_minute -= 60
                
                end_time = datetime.time(min(23, end_hour), end_minute)
                
                # Add to solution
                solution[scene.id] = {
                    'date': selected_date,
                    'start_time': start_time,
                    'end_time': end_time
                }
            
            # Check for conflicts and repair solution
            solution = repair_solution(solution, scenes, actor_scenes, actor_availability, location_availability)
            
            # Evaluate solution
            cost = evaluate_solution(solution, scenes, actors, locations, actor_scenes)
            
            solutions.append({
                'solution': solution,
                'cost': cost
            })
            
            # Update best solution if better
            if cost < best_cost:
                best_solution = copy.deepcopy(solution)
                best_cost = cost
        
        # Update pheromone trails
        # First, apply evaporation to all trails
        for scene_id in pheromone:
            for date_str in pheromone[scene_id]:
                pheromone[scene_id][date_str] *= (1 - evaporation_rate)
        
        # Add new pheromone based on solutions
        for sol in solutions:
            solution = sol['solution']
            cost = sol['cost']
            
            # Higher quality solutions deposit more pheromone
            deposit = 1.0 / (cost + 0.1)  # Avoid division by zero
            
            for scene_id, scene_data in solution.items():
                date_str = scene_data['date'].strftime('%Y-%m-%d')
                pheromone[scene_id][date_str] += deposit
    
    logging.info(f"ACO completed after {max_iterations} iterations")
    
    # If no solution found, generate a random one
    if not best_solution:
        best_solution = generate_initial_solution(scenes, available_dates, actor_scenes, actor_availability, location_availability)
    
    # Convert solution to the expected return format
    return format_solution(best_solution, scenes, actors, locations)

def generate_initial_solution(scenes, available_dates, actor_scenes, actor_availability, location_availability):
    """Generate a random initial solution."""
    solution = {}
    
    for scene in scenes:
        # Select a random date
        selected_date = random.choice(available_dates)
        
        # Assign start/end times
        start_time = datetime.time(9, 0)  # Default 9:00 AM
        estimated_duration = scene.estimated_duration or 1.0  # Hours
        
        # Calculate end time
        hours = int(estimated_duration)
        minutes = int((estimated_duration - hours) * 60)
        end_hour = start_time.hour + hours
        end_minute = start_time.minute + minutes
        
        # Adjust for overflow
        if end_minute >= 60:
            end_hour += 1
            end_minute -= 60
        
        end_time = datetime.time(min(23, end_hour), end_minute)
        
        # Add to solution
        solution[scene.id] = {
            'date': selected_date,
            'start_time': start_time,
            'end_time': end_time
        }
    
    # Repair solution to fix conflicts
    return repair_solution(solution, scenes, actor_scenes, actor_availability, location_availability)

def repair_solution(solution, scenes, actor_scenes, actor_availability, location_availability):
    """Repair a solution by resolving conflicts."""
    # Get scene objects by ID
    scene_dict = {scene.id: scene for scene in scenes}
    
    # Group scenes by date
    scenes_by_date = defaultdict(list)
    for scene_id, scene_data in solution.items():
        date_str = scene_data['date'].strftime('%Y-%m-%d')
        scenes_by_date[date_str].append(scene_id)
    
    # For each date, check for actor/location conflicts
    for date_str, date_scenes in scenes_by_date.items():
        # Skip if only one scene on this date
        if len(date_scenes) <= 1:
            continue
        
        # Map of actors to scenes they're in on this date
        actor_schedule = defaultdict(list)
        location_schedule = defaultdict(list)
        
        # Map scenes to their assigned times
        scene_times = {}
        
        for scene_id in date_scenes:
            scene = scene_dict.get(scene_id)
            if not scene:
                continue
            
            scene_times[scene_id] = (solution[scene_id]['start_time'], solution[scene_id]['end_time'])
            
            # Track actors in this scene
            for actor_id in actor_scenes.get(scene_id, []):
                actor_schedule[actor_id].append(scene_id)
            
            # Track location
            if scene.location_id:
                location_schedule[scene.location_id].append(scene_id)
        
        # Check for actor conflicts
        for actor_id, actor_scenes_list in actor_schedule.items():
            if len(actor_scenes_list) <= 1:
                continue
            
            # Sort by start time
            actor_scenes_list.sort(key=lambda x: scene_times[x][0])
            
            # Check for overlaps
            for i in range(len(actor_scenes_list) - 1):
                curr_scene = actor_scenes_list[i]
                next_scene = actor_scenes_list[i + 1]
                
                curr_end = scene_times[curr_scene][1]
                next_start = scene_times[next_scene][0]
                
                # If overlap, adjust next scene start time
                if curr_end > next_start:
                    new_start = datetime.time(curr_end.hour, curr_end.minute)
                    
                    # Calculate new end time
                    scene = scene_dict.get(next_scene)
                    if not scene:
                        continue
                    
                    estimated_duration = scene.estimated_duration or 1.0
                    
                    hours = int(estimated_duration)
                    minutes = int((estimated_duration - hours) * 60)
                    end_hour = new_start.hour + hours
                    end_minute = new_start.minute + minutes
                    
                    # Adjust for overflow
                    if end_minute >= 60:
                        end_hour += 1
                        end_minute -= 60
                    
                    new_end = datetime.time(min(23, end_hour), end_minute)
                    
                    # Update solution
                    solution[next_scene]['start_time'] = new_start
                    solution[next_scene]['end_time'] = new_end
                    
                    # Update scene_times
                    scene_times[next_scene] = (new_start, new_end)
        
        # Check for location conflicts
        for location_id, location_scenes_list in location_schedule.items():
            if len(location_scenes_list) <= 1:
                continue
            
            # Sort by start time
            location_scenes_list.sort(key=lambda x: scene_times[x][0])
            
            # Check for overlaps
            for i in range(len(location_scenes_list) - 1):
                curr_scene = location_scenes_list[i]
                next_scene = location_scenes_list[i + 1]
                
                curr_end = scene_times[curr_scene][1]
                next_start = scene_times[next_scene][0]
                
                # If overlap, move next scene to next day
                if curr_end > next_start:
                    current_date = solution[next_scene]['date']
                    new_date = current_date + datetime.timedelta(days=1)
                    
                    # Update solution
                    solution[next_scene]['date'] = new_date
                    
                    # This might create new conflicts, but we'll catch them in the next iteration
    
    return solution

def evaluate_solution(solution, scenes, actors, locations, actor_scenes):
    """
    Evaluate a solution based on various cost factors.
    
    Costs include:
    - Actor costs (based on days scheduled)
    - Location costs
    - Travel costs (when switching locations)
    - Penalties for unavailability
    """
    import logging
    
    # Safety check for empty solution
    if not solution:
        logging.warning("Empty solution being evaluated")
        return 1000000  # Return a very high cost as penalty
    
    try:    
        scene_dict = {scene.id: scene for scene in scenes}
        actor_dict = {actor.id: actor for actor in actors}
        location_dict = {location.id: location for location in locations}
        
        # Track total cost
        total_cost = 0
        
        # Track which actors and locations are used on each day
        actors_by_date = defaultdict(set)
        locations_by_date = defaultdict(set)
    
        # Process each scheduled scene
        for scene_id, scene_data in solution.items():
            # Get scene object - convert string ID to int if needed
            scene_id_int = int(scene_id) if isinstance(scene_id, str) else scene_id
            scene = scene_dict.get(scene_id_int)
            if not scene:
                continue
            
            # Check if the date field exists and is valid
            if 'date' not in scene_data or not scene_data['date']:
                continue
                
            date_str = scene_data['date'].strftime('%Y-%m-%d')
            
            # Add actors to daily schedule - handle both string and int scene IDs
            scene_actors = actor_scenes.get(scene_id_int, [])
            if not scene_actors and str(scene_id_int) in actor_scenes:
                scene_actors = actor_scenes[str(scene_id_int)]
                
            for actor_id in scene_actors:
                actors_by_date[date_str].add(actor_id)
            
            # Add location to daily schedule
            if scene.location_id:
                locations_by_date[date_str].add(scene.location_id)
        
        # Calculate actor costs
        for date_str, actor_ids in actors_by_date.items():
            for actor_id in actor_ids:
                actor = actor_dict.get(actor_id)
                if actor:
                    actor_cost = actor.cost_per_day or 0
                    total_cost += actor_cost
        
        # Calculate location costs
        for date_str, location_ids in locations_by_date.items():
            for location_id in location_ids:
                location = location_dict.get(location_id)
                if location:
                    location_cost = location.cost_per_day or 0
                    total_cost += location_cost
        
        # Calculate location transition costs (simplified)
        prev_date = None
        prev_locations = set()
        
        for date in sorted(locations_by_date.keys()):
            current_locations = locations_by_date[date]
            
            if prev_date:
                # Calculate days between shoots
                date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
                prev_date_obj = datetime.datetime.strptime(prev_date, '%Y-%m-%d').date()
                days_between = (date_obj - prev_date_obj).days
                
                # If consecutive days with different locations, add transition cost
                if days_between == 1 and prev_locations != current_locations:
                    # Approximate transition cost based on number of location changes
                    transition_cost = len(prev_locations.symmetric_difference(current_locations)) * 500
                    total_cost += transition_cost
            
            prev_date = date
            prev_locations = current_locations
        
        # Add scheduling efficiency factor
        # Prefer schedules with fewer total days
        unique_days = len(actors_by_date)
        efficiency_penalty = unique_days * 100  # Penalty per shooting day
        
        total_cost += efficiency_penalty
        
        return max(1, total_cost)  # Ensure we don't return zero cost
        
    except Exception as e:
        logging.error(f"Error evaluating solution: {e}")
        return 1000000  # Return a very high cost as penalty for invalid solutions

def format_solution(solution, scenes, actors, locations):
    """Format the solution for the expected return structure."""
    import logging
    
    try:
        # Safety check for empty or invalid solution
        if not solution:
            logging.warning("Empty solution being formatted")
            return {
                'scenes': {},
                'total_cost': 0,
                'total_duration': 0
            }
            
        scene_dict = {scene.id: scene for scene in scenes}
        
        # Calculate total cost and duration
        try:
            actor_scenes = {}  # We'll need to provide this for evaluation
            for scene in scenes:
                actor_scene_relations = [as_rel for as_rel in scene.actor_scenes]
                actor_scenes[scene.id] = [rel.actor_id for rel in actor_scene_relations]
                
            total_cost = evaluate_solution(solution, scenes, actors, locations, actor_scenes)
        except Exception as e:
            logging.error(f"Error calculating total cost: {e}")
            total_cost = 0
        
        # Find the min and max dates to determine duration
        min_date = None
        max_date = None
        
        for scene_id, scene_data in solution.items():
            date = scene_data.get('date')
            if not date:
                continue
                
            if min_date is None or date < min_date:
                min_date = date
            
            if max_date is None or date > max_date:
                max_date = date
        
        total_duration = (max_date - min_date).days + 1 if min_date and max_date else 0
        
        # Format scenes
        formatted_scenes = {}
        
        for scene_id, scene_data in solution.items():
            scene_id_int = int(scene_id) if isinstance(scene_id, str) else scene_id
            scene = scene_dict.get(scene_id_int)
            if not scene:
                continue
            
            # Calculate scene cost
            scene_cost = 0
            
            # Location cost
            if scene.location_id:
                location = next((loc for loc in locations if loc.id == scene.location_id), None)
                if location:
                    scene_cost += location.cost_per_day or 0
            
            # Actor costs will be factored in the total schedule cost, not per scene
            
            # Ensure all required fields exist
            if not all(key in scene_data for key in ['date', 'start_time', 'end_time']):
                logging.warning(f"Missing required data for scene {scene_id}")
                continue
                
            formatted_scenes[str(scene_id_int)] = {
                'date': scene_data['date'],
                'start_time': scene_data['start_time'],
                'end_time': scene_data['end_time'],
                'cost': scene_cost
            }
        
        return {
            'scenes': formatted_scenes,
            'total_cost': total_cost,
            'total_duration': total_duration
        }
    except Exception as e:
        logging.error(f"Error formatting solution: {e}")
        # Return a basic valid structure
        return {
            'scenes': {},
            'total_cost': 0,
            'total_duration': 0
        }
