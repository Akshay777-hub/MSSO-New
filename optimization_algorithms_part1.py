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
