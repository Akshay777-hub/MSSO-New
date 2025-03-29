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
                    
                    # Skip dates where constraints aren't met
                    if not is_date_valid_for_scene(scene, date, solution, actor_scenes, actor_availability, location_availability):
                        continue
                    
                    # Calculate heuristic value (inverse of conflicts)
                    heuristic = 1.0 / (1 + count_conflicts(scene, date, solution, actor_scenes))
                    
                    # Calculate probability based on pheromone and heuristic
                    probability = (pheromone[scene.id][date_str] ** alpha) * (heuristic ** beta)
                    
                    probabilities.append(probability)
                    valid_dates.append(date)
                
                # If no valid dates, pick a random one
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
                
                # Assign time slots
                start_time = datetime.time(9, 0)  # Default start at 9 AM
                
                # Check if other scenes are already scheduled for this date
                scenes_on_date = [s for s_id, s in solution.items() if s['date'] == selected_date]
                if scenes_on_date:
                    # Find the latest end time
                    latest_end = max(s['end_time'] for s in scenes_on_date)
                    start_time = latest_end
                
                # Calculate end time based on scene duration
                duration_hours = int(scene.estimated_duration)
                duration_minutes = int((scene.estimated_duration - duration_hours) * 60)
                
                start_hour = start_time.hour
                start_minute = start_time.minute
                
                end_hour = start_hour + duration_hours
                end_minute = start_minute + duration_minutes
                
                # Handle minute overflow
                if end_minute >= 60:
                    end_hour += 1
                    end_minute -= 60
                
                # Ensure we don't go past end of day
                if end_hour >= 19:
                    end_hour = 19
                    end_minute = 0
                
                end_time = datetime.time(end_hour, end_minute)
                
                # Add scene to solution
                solution[scene.id] = {
                    'date': selected_date,
                    'start_time': start_time,
                    'end_time': end_time,
                }
            
            # Evaluate solution
            cost = evaluate_solution(solution, scenes, actors, locations, actor_scenes)
            solutions.append((solution, cost))
            
            # Update best solution
            if cost < best_cost:
                best_solution = copy.deepcopy(solution)
                best_cost = cost
        
        # Update pheromone levels
        # First, evaporate
        for scene_id in pheromone:
            for date_str in pheromone[scene_id]:
                pheromone[scene_id][date_str] *= (1 - evaporation_rate)
        
        # Then, deposit new pheromone based on solution quality
        for solution, cost in solutions:
            # Inverse of cost determines amount of pheromone
            deposit = 1.0 / (cost if cost > 0 else 0.1)
            
            for scene_id, details in solution.items():
                date_str = details['date'].strftime('%Y-%m-%d')
                pheromone[scene_id][date_str] += deposit
    
    logging.info(f"ACO completed after {max_iterations} iterations")
    
    # Convert solution to the expected return format
    return format_solution(best_solution, scenes, actors, locations)

# Helper Functions
def generate_initial_solution(scenes, available_dates, actor_scenes, actor_availability, location_availability):
    """Generate an initial feasible solution."""
    solution = {}
    
    # Assign scenes to dates
    for scene in scenes:
        # Find a valid date
        valid_date = None
        for date in available_dates:
            if is_date_valid_for_scene(scene, date, solution, actor_scenes, actor_availability, location_availability):
                valid_date = date
                break
        
        # If no valid date, just pick the first one
        if not valid_date:
            valid_date = available_dates[0]
        
        # Assign time slots
        start_time = datetime.time(9, 0)  # Default start at 9 AM
        
        # Check if other scenes are already scheduled for this date
        scenes_on_date = [s for s_id, s in solution.items() if s['date'] == valid_date]
        if scenes_on_date:
            # Find the latest end time
            latest_end = max(s['end_time'] for s in scenes_on_date)
            start_time = latest_end
        
        # Calculate end time based on scene duration
        duration_hours = int(scene.estimated_duration)
        duration_minutes = int((scene.estimated_duration - duration_hours) * 60)
        
        start_hour = start_time.hour
        start_minute = start_time.minute
        
        end_hour = start_hour + duration_hours
        end_minute = start_minute + duration_minutes
        
        # Handle minute overflow
        if end_minute >= 60:
            end_hour += 1
            end_minute -= 60
        
        # Ensure we don't go past end of day
        if end_hour >= 19:
            end_hour = 19
            end_minute = 0
        
        end_time = datetime.time(end_hour, end_minute)
        
        # Add scene to solution
        solution[scene.id] = {
            'date': valid_date,
            'start_time': start_time,
            'end_time': end_time,
        }
    
    return solution

def is_date_valid_for_scene(scene, date, solution, actor_scenes, actor_availability, location_availability):
    """Check if a date is valid for scheduling a scene."""
    date_str = date.strftime('%Y-%m-%d')
    
    # Check location availability
    if scene.location_id and scene.location_id in location_availability:
        location_avail = location_availability[scene.location_id]
        if date_str in location_avail and not location_avail[date_str]['is_available']:
            return False
    
    # Check actor availability
    if scene.id in actor_scenes:
        for actor_id in actor_scenes[scene.id]:
            if actor_id in actor_availability:
                actor_avail = actor_availability[actor_id]
                if date_str in actor_avail and not actor_avail[date_str]:
                    return False
    
    # Check for location conflicts
    if scene.location_id:
        for s_id, s in solution.items():
            if s['date'] == date:
                other_scene = next((sc for sc in scene if sc.id == s_id), None)
                if other_scene and other_scene.location_id == scene.location_id:
                    # Check for time overlap (simplified)
                    return False
    
    return True

def count_conflicts(scene, date, solution, actor_scenes):
    """Count number of conflicts if scene is scheduled on date."""
    conflicts = 0
    
    # Check for actor conflicts
    if scene.id in actor_scenes:
        scene_actors = actor_scenes[scene.id]
        
        for s_id, s in solution.items():
            if s['date'] == date and s_id in actor_scenes:
                other_actors = actor_scenes[s_id]
                conflicts += len(set(scene_actors).intersection(other_actors))
    
    # Check for location conflicts
    if scene.location_id:
        for s_id, s in solution.items():
            if s['date'] == date:
                other_scene = next((sc for sc in scene if sc.id == s_id), None)
                if other_scene and other_scene.location_id == scene.location_id:
                    conflicts += 1
    
    return conflicts

def evaluate_solution(solution, scenes, actors, locations, actor_scenes):
    """
    Evaluate a solution based on various criteria:
    - Total cost
    - Schedule length
    - Actor utilization
    - Location utilization
    - Conflicts
    """
    total_cost = 0
    schedule_days = set()
    actor_days = defaultdict(set)
    location_days = defaultdict(set)
    conflicts = 0
    
    # Scene lookup
    scene_map = {scene.id: scene for scene in scenes}
    
    # Calculate metrics
    for scene_id, details in solution.items():
        if scene_id not in scene_map:
            continue
            
        scene = scene_map[scene_id]
        date = details['date']
        date_str = date.strftime('%Y-%m-%d')
        
        # Add to schedule days
        schedule_days.add(date_str)
        
        # Actor utilization
        if scene_id in actor_scenes:
            for actor_id in actor_scenes[scene_id]:
                actor_days[actor_id].add(date_str)
        
        # Location utilization
        if scene.location_id:
            location_days[scene.location_id].add(date_str)
        
        # Cost calculations
        scene_cost = 0
        
        # Actor costs
        if scene_id in actor_scenes:
            for actor_id in actor_scenes[scene_id]:
                actor = next((a for a in actors if a.id == actor_id), None)
                if actor:
                    scene_cost += actor.cost_per_day
        
        # Location costs
        if scene.location_id:
            location = next((l for l in locations if l.id == scene.location_id), None)
            if location:
                scene_cost += location.cost_per_day
        
        total_cost += scene_cost
        
        # Check for conflicts
        for other_id, other_details in solution.items():
            if other_id != scene_id and other_details['date'] == date:
                # Check for actor conflicts
                if scene_id in actor_scenes and other_id in actor_scenes:
                    scene_actors = set(actor_scenes[scene_id])
                    other_actors = set(actor_scenes[other_id])
                    
                    # Count overlapping actors as conflicts
                    overlap = scene_actors.intersection(other_actors)
                    conflicts += len(overlap)
                
                # Check for location conflicts
                if scene.location_id and scene.location_id == scene_map.get(other_id, None).location_id:
                    # Check for time overlap
                    start1 = datetime.datetime.combine(date, details['start_time'])
                    end1 = datetime.datetime.combine(date, details['end_time'])
                    start2 = datetime.datetime.combine(date, other_details['start_time'])
                    end2 = datetime.datetime.combine(date, other_details['end_time'])
                    
                    if start1 < end2 and start2 < end1:
                        conflicts += 1
    
    # Calculate final cost
    # Weight the different components
    w_cost = 0.4
    w_length = 0.2
    w_conflicts = 0.4
    
    cost_score = total_cost
    length_score = len(schedule_days) * 1000  # Make comparable to cost
    conflict_score = conflicts * 5000  # Heavy penalty for conflicts
    
    final_score = (w_cost * cost_score) + (w_length * length_score) + (w_conflicts * conflict_score)
    
    return final_score

def generate_neighbors(current_solution, scenes, available_dates, actor_scenes, actor_availability, location_availability):
    """Generate neighboring solutions by making small changes."""
    neighbors = []
    
    # For each scene, try scheduling it on a different date
    for scene_id, details in current_solution.items():
        current_date = details['date']
        
        for date in available_dates:
            if date != current_date:
                # Create a new solution with this scene moved
                new_solution = copy.deepcopy(current_solution)
                
                # Update date
                new_solution[scene_id]['date'] = date
                
                # Update times if needed
                # Find scenes already scheduled on this date
                scenes_on_date = [(s_id, s) for s_id, s in new_solution.items() 
                               if s_id != scene_id and s['date'] == date]
                
                if scenes_on_date:
                    # Find a suitable time slot
                    # For simplicity, just add it at the end
                    latest_end = max(s['end_time'] for _, s in scenes_on_date)
                    
                    duration = (new_solution[scene_id]['end_time'].hour - new_solution[scene_id]['start_time'].hour) + \
                              (new_solution[scene_id]['end_time'].minute - new_solution[scene_id]['start_time'].minute) / 60
                    
                    start_hour = latest_end.hour
                    start_minute = latest_end.minute
                    
                    end_hour = start_hour + int(duration)
                    end_minute = start_minute + int((duration - int(duration)) * 60)
                    
                    # Handle minute overflow
                    if end_minute >= 60:
                        end_hour += 1
                        end_minute -= 60
                    
                    # If it goes past end of day, skip this neighbor
                    if end_hour >= 19:
                        continue
                    
                    new_solution[scene_id]['start_time'] = datetime.time(start_hour, start_minute)
                    new_solution[scene_id]['end_time'] = datetime.time(end_hour, end_minute)
                else:
                    # First scene of the day, start at 9 AM
                    new_solution[scene_id]['start_time'] = datetime.time(9, 0)
                    
                    duration = (new_solution[scene_id]['end_time'].hour - new_solution[scene_id]['start_time'].hour) + \
                              (new_solution[scene_id]['end_time'].minute - new_solution[scene_id]['start_time'].minute) / 60
                    
                    end_hour = 9 + int(duration)
                    end_minute = int((duration - int(duration)) * 60)
                    
                    new_solution[scene_id]['end_time'] = datetime.time(end_hour, end_minute)
                
                neighbors.append({
                    'scene_id': scene_id,
                    'date': date,
                    'solution': new_solution
                })
    
    return neighbors

def repair_solution(solution, scenes, actor_scenes, actor_availability, location_availability):
    """Repair a solution to ensure feasibility."""
    # Group scenes by date
    scenes_by_date = defaultdict(list)
    
    for scene_id, details in solution.items():
        date = details['date']
        scenes_by_date[date].append((scene_id, details))
    
    # For each date, adjust time slots to avoid overlaps
    for date, scheduled_scenes in scenes_by_date.items():
        # Sort by start time
        scheduled_scenes.sort(key=lambda x: x[1]['start_time'])
        
        # Adjust times to avoid overlaps
        current_end_time = datetime.time(9, 0)  # Start at 9 AM
        
        for scene_id, details in scheduled_scenes:
            scene = next((s for s in scenes if s.id == scene_id), None)
            if not scene:
                continue
                
            # Set start time to current end time
            details['start_time'] = current_end_time
            
            # Calculate end time based on scene duration
            duration_hours = int(scene.estimated_duration)
            duration_minutes = int((scene.estimated_duration - duration_hours) * 60)
            
            start_hour = current_end_time.hour
            start_minute = current_end_time.minute
            
            end_hour = start_hour + duration_hours
            end_minute = start_minute + duration_minutes
            
            # Handle minute overflow
            if end_minute >= 60:
                end_hour += 1
                end_minute -= 60
            
            # Ensure we don't go past end of day
            if end_hour >= 19:
                end_hour = 19
                end_minute = 0
            
            end_time = datetime.time(end_hour, end_minute)
            details['end_time'] = end_time
            
            # Update current end time
            current_end_time = end_time

def format_solution(solution, scenes, actors, locations):
    """Format solution for return."""
    formatted_solution = {}
    
    # Scene lookup
    scene_map = {scene.id: scene for scene in scenes}
    
    for scene_id, details in solution.items():
        if scene_id not in scene_map:
            continue
            
        scene = scene_map[scene_id]
        
        # Calculate cost for this scene
        cost = 0
        
        # Actor costs
        scene_actors = []
        for actor in actors:
            for rel in actor.actor_scenes:
                if rel.scene_id == scene_id:
                    cost += actor.cost_per_day
                    scene_actors.append(actor.id)
                    break
        
        # Location cost
        if scene.location_id:
            location = next((l for l in locations if l.id == scene.location_id), None)
            if location:
                cost += location.cost_per_day
        
        # Format dates and times
        date_str = details['date'].strftime('%Y-%m-%d')
        start_time_str = details['start_time'].strftime('%H:%M')
        end_time_str = details['end_time'].strftime('%H:%M')
        
        formatted_solution[scene_id] = {
            'date': date_str,
            'start_time': start_time_str,
            'end_time': end_time_str,
            'cost': cost,
            'actors': scene_actors,
            'location_id': scene.location_id
        }
    
    return formatted_solution
