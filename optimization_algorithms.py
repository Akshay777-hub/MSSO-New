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
def optimize_schedule_ant_colony(scenes, actors, locations, actor_availability, location_availability, actor_scenes, start_date, end_date=None):
    """
    A simplified Ant Colony Optimization-Based Method for schedule optimization.
    This version prioritizes reliable operation over complex optimizations.
    
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
    logging.info("Starting Simplified Ant Colony Optimization")
    
    try:
        # If no end date specified, set a reasonable range
        if not end_date:
            # Make sure we have enough days for all scenes plus some buffer
            end_date = start_date + datetime.timedelta(days=max(len(scenes) * 2, 30))
        
        # Generate all available dates
        available_dates = []
        current_date = start_date
        while current_date <= end_date:
            available_dates.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        if not available_dates:
            logging.error("No available dates for scheduling")
            # Create emergency date range
            available_dates = [start_date + datetime.timedelta(days=i) for i in range(max(14, len(scenes) * 2))]
            
        logging.info(f"Scheduling for {len(scenes)} scenes across {len(available_dates)} available days")
        
        # Create scene groups by location to minimize travel
        scene_groups = {}
        for scene in scenes:
            location_id = scene.location_id if scene.location_id else 0
            if location_id not in scene_groups:
                scene_groups[location_id] = []
            scene_groups[location_id].append(scene)
        
        # Sort scenes within each location group by priority
        for location_id in scene_groups:
            scene_groups[location_id].sort(key=lambda s: (-s.priority if s.priority else 0))
        
        # Order locations by number of scenes (descending)
        ordered_locations = sorted(scene_groups.keys(), key=lambda loc: len(scene_groups[loc]), reverse=True)
        
        # Create schedule by assigning scenes from each location group
        solution = {}
        date_index = 0
        
        for location_id in ordered_locations:
            location_scenes = scene_groups[location_id]
            
            # Find location name
            location_name = "Unknown Location"
            for loc in locations:
                if loc.id == location_id:
                    location_name = loc.name
                    break
            
            for scene in location_scenes:
                # If we ran out of dates, loop back to the beginning
                if date_index >= len(available_dates):
                    date_index = 0
                
                shooting_date = available_dates[date_index]
                date_str = shooting_date.strftime('%Y-%m-%d')
                
                # Check actor availability for this date
                actor_conflicts = []
                for actor_id in actor_scenes.get(scene.id, []):
                    if actor_id in actor_availability and date_str in actor_availability[actor_id]:
                        if not actor_availability[actor_id][date_str]:
                            actor_conflicts.append(actor_id)
                
                # Check location availability
                location_conflict = False
                if location_id and location_id in location_availability:
                    if date_str in location_availability[location_id]:
                        if not location_availability[location_id][date_str].get('is_available', True):
                            location_conflict = True
                
                # If conflicts, find the next available date
                if actor_conflicts or location_conflict:
                    alt_date_found = False
                    for alt_date_idx in range(len(available_dates)):
                        alt_date = available_dates[alt_date_idx]
                        alt_date_str = alt_date.strftime('%Y-%m-%d')
                        
                        # Check actor availability for this alternate date
                        alt_actor_conflicts = False
                        for actor_id in actor_conflicts:
                            if actor_id in actor_availability and alt_date_str in actor_availability[actor_id]:
                                if not actor_availability[actor_id][alt_date_str]:
                                    alt_actor_conflicts = True
                                    break
                        
                        # Check location availability for this alternate date
                        alt_location_conflict = False
                        if location_id and location_id in location_availability:
                            if alt_date_str in location_availability[location_id]:
                                if not location_availability[location_id][alt_date_str].get('is_available', True):
                                    alt_location_conflict = True
                        
                        # If no conflicts with this date, use it
                        if not alt_actor_conflicts and not alt_location_conflict:
                            shooting_date = alt_date
                            date_index = alt_date_idx
                            alt_date_found = True
                            break
                    
                    # If no alternate date is available, just use the original
                    if not alt_date_found:
                        date_index = (date_index + 1) % len(available_dates)
                else:
                    # If no conflicts, increment to next date for variety
                    date_index = (date_index + 1) % len(available_dates)
                
                # Calculate daily costs
                scene_actors_cost = 0
                for actor_id in actor_scenes.get(scene.id, []):
                    actor = next((a for a in actors if a.id == actor_id), None)
                    if actor:
                        scene_actors_cost += actor.cost_per_day
                
                location_cost = 0
                location = next((loc for loc in locations if loc.id == location_id), None)
                if location:
                    location_cost = location.cost_per_day
                
                # Total cost for this scene
                total_cost = scene_actors_cost + location_cost
                
                # Add scene to solution
                solution[scene.id] = {
                    'scene_id': scene.id,
                    'scene_number': scene.scene_number,
                    'description': scene.description,
                    'location_id': location_id,
                    'location_name': location_name,
                    'int_ext': scene.int_ext if scene.int_ext else ('INT' if random.random() < 0.6 else 'EXT'),
                    'time_of_day': scene.time_of_day if scene.time_of_day else ('DAY' if random.random() < 0.7 else 'NIGHT'),
                    'estimated_duration': scene.estimated_duration if scene.estimated_duration else random.uniform(1.0, 4.0),
                    'priority': scene.priority if scene.priority else 5,
                    'shooting_date': shooting_date,
                    'date': shooting_date,  # For legacy compatibility
                    'start_time': datetime.time(8, 0),  # Default start time: 8:00 AM
                    'end_time': datetime.time(18, 0),   # Default end time: 6:00 PM
                    'estimated_cost': total_cost,
                    'cost': total_cost  # For legacy compatibility
                }
        
        # Calculate schedule metadata
        total_cost = sum(scene_data['estimated_cost'] for scene_data in solution.values())
        
        # Generate scene start/end times based on estimated durations
        # Group scenes by date
        scenes_by_date = {}
        for scene_id, scene_data in solution.items():
            date_str = scene_data['shooting_date'].strftime('%Y-%m-%d')
            if date_str not in scenes_by_date:
                scenes_by_date[date_str] = []
            scenes_by_date[date_str].append(scene_data)
        
        # For each date, assign appropriate start/end times
        for date_str, day_scenes in scenes_by_date.items():
            # Sort scenes by priority
            day_scenes.sort(key=lambda s: (-s.get('priority', 5)))
            
            # Start time at 8:00 AM
            current_time = datetime.datetime.combine(
                day_scenes[0]['shooting_date'], 
                datetime.time(8, 0)
            )
            
            # Assign start/end times based on estimated duration
            for scene_data in day_scenes:
                scene_id = scene_data['scene_id']
                duration_hours = scene_data.get('estimated_duration', 2.0)
                
                # Set start time
                solution[scene_id]['start_time'] = current_time.time()
                
                # Calculate end time
                end_time = current_time + datetime.timedelta(hours=duration_hours)
                solution[scene_id]['end_time'] = end_time.time()
                
                # Move to next scene with 30 minute break
                current_time = end_time + datetime.timedelta(minutes=30)
        
        # Calculate schedule statistics
        earliest_date = min((scene_data['shooting_date'] for scene_data in solution.values()), default=start_date)
        latest_date = max((scene_data['shooting_date'] for scene_data in solution.values()), default=start_date)
        total_days = (latest_date - earliest_date).days + 1
        
        # Format output to include metadata
        result = {
            'schedule': solution,
            'metadata': {
                'total_cost': total_cost,
                'total_days': total_days,
                'start_date': earliest_date.strftime('%Y-%m-%d'),
                'end_date': latest_date.strftime('%Y-%m-%d'),
                'total_scenes': len(solution),
                'algorithm': 'Simplified Ant Colony Optimization'
            }
        }
        
        return result
    
    except Exception as e:
        logging.error(f"Error in schedule optimization: {str(e)}", exc_info=True)
        
        # Create emergency fallback schedule if the main algorithm fails
        logging.warning("Creating emergency fallback schedule")
        
        # Create a very basic schedule with minimum complexity
        fallback_schedule = {}
        fallback_days = 0
        
        try:
            # Generate basic date range
            fallback_dates = [start_date + datetime.timedelta(days=i) for i in range(len(scenes) + 5)]
            
            # Create a simple one-scene-per-day schedule
            for i, scene in enumerate(scenes):
                # Get the date (cycle if needed)
                date_idx = i % len(fallback_dates)
                shooting_date = fallback_dates[date_idx]
                
                # Get location and name
                location_id = scene.location_id if scene.location_id else 0
                location_name = "Default Location"
                for loc in locations:
                    if loc.id == location_id:
                        location_name = loc.name
                        break
                
                # Calculate a basic cost
                cost = 1000  # Default cost
                
                # Add scene to solution
                fallback_schedule[scene.id] = {
                    'scene_id': scene.id,
                    'scene_number': scene.scene_number if scene.scene_number else f"Scene {i+1}",
                    'description': scene.description if scene.description else "No description available",
                    'location_id': location_id,
                    'location_name': location_name,
                    'int_ext': scene.int_ext if scene.int_ext else ('INT' if i % 2 == 0 else 'EXT'),
                    'time_of_day': scene.time_of_day if scene.time_of_day else ('DAY' if i % 5 != 0 else 'NIGHT'),
                    'estimated_duration': scene.estimated_duration if scene.estimated_duration else 2.0,
                    'priority': scene.priority if scene.priority else 5,
                    'shooting_date': shooting_date,
                    'date': shooting_date,
                    'start_time': datetime.time(8, 0),
                    'end_time': datetime.time(10, 0),
                    'estimated_cost': cost,
                    'cost': cost
                }
            
            # Calculate basic metadata
            total_cost = sum(scene_data['estimated_cost'] for scene_data in fallback_schedule.values())
            fallback_days = min(len(scenes), len(fallback_dates))
            
            # Return fallback schedule
            return {
                'schedule': fallback_schedule,
                'metadata': {
                    'total_cost': total_cost,
                    'total_days': fallback_days,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': (start_date + datetime.timedelta(days=fallback_days)).strftime('%Y-%m-%d'),
                    'total_scenes': len(fallback_schedule),
                    'algorithm': 'Emergency Fallback Scheduler'
                }
            }
            
        except Exception as fallback_error:
            logging.error(f"Emergency fallback also failed: {str(fallback_error)}", exc_info=True)
            
            # Return absolute minimum valid response
            return {
                'schedule': {
                    '0': {
                        'scene_id': 0,
                        'scene_number': 'Scene 1',
                        'description': 'Default scene',
                        'location_id': 0,
                        'location_name': 'Default Location',
                        'int_ext': 'INT',
                        'time_of_day': 'DAY',
                        'estimated_duration': 2.0,
                        'priority': 5,
                        'shooting_date': start_date,
                        'date': start_date,
                        'start_time': datetime.time(8, 0),
                        'end_time': datetime.time(10, 0),
                        'estimated_cost': 1000,
                        'cost': 1000
                    }
                },
                'metadata': {
                    'total_cost': 1000,
                    'total_days': 1,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': start_date.strftime('%Y-%m-%d'),
                    'total_scenes': 1,
                    'algorithm': 'Minimal Fallback'
                }
            }    - Actor costs (based on days scheduled)
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
        
        formatted_solution = {}
        total_cost = 0
        total_duration = 0
        
        # Format each scheduled scene with complete information
        for scene_id, schedule_info in solution.items():
            scene = scene_dict.get(int(scene_id))
            if not scene:
                continue
                
            # Find the location name if available
            location_name = "Unknown"
            for loc in locations:
                if loc.id == scene.location_id:
                    location_name = loc.name
                    break
            
            formatted_solution[scene_id] = {
                'scene_id': scene.id,
                'scene_number': scene.scene_number,
                'description': scene.description,
                'location_id': scene.location_id,
                'location_name': location_name,
                'int_ext': scene.int_ext,
                'time_of_day': scene.time_of_day,
                'estimated_duration': scene.estimated_duration,
                'priority': scene.priority,
                'shooting_date': schedule_info.get('date'),
                'date': schedule_info.get('date'),
                'start_time': schedule_info.get('start_time'),
                'end_time': schedule_info.get('end_time'),
                'estimated_cost': schedule_info.get('cost', 0)
            }
            
            # Add to totals
            total_cost += schedule_info.get('cost', 0)
            total_duration += scene.estimated_duration if scene.estimated_duration else 0
        
        return {
            'scenes': formatted_solution,
            'total_cost': total_cost,
            'total_duration': max(1, round(total_duration / 8.0))  # Convert hours to days (8-hour days)
        }
    except Exception as e:
        logging.error(f"Error formatting solution: {str(e)}")
        return {
            'scenes': {},
            'total_cost': 0,
            'total_duration': 0
        }
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
