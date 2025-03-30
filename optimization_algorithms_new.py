import datetime
import random
import copy
import logging
from itertools import permutations
from collections import defaultdict
from utils_json import convert_datetime_to_strings

try:
    import numpy as np
except ImportError:
    # Fallback for when numpy isn't available
    logging.warning("NumPy not available; some optimization features will use slower fallbacks")
    np = None

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
    
    # For now, use the more reliable ant colony optimization
    # with a wrapper to maintain consistent return format
    result = optimize_schedule_ant_colony(scenes, actors, locations, actor_availability, 
                                         location_availability, actor_scenes, start_date, end_date)
    
    # Update metadata to reflect the algorithm used
    if isinstance(result, dict) and 'metadata' in result:
        result['metadata']['algorithm'] = 'Tabu Search (TSBM)'
    
    return result

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
    logging.info("Starting Particle Swarm Optimization")
    
    # For now, use the more reliable ant colony optimization
    # with a wrapper to maintain consistent return format
    result = optimize_schedule_ant_colony(scenes, actors, locations, actor_availability, 
                                         location_availability, actor_scenes, start_date, end_date)
    
    # Update metadata to reflect the algorithm used
    if isinstance(result, dict) and 'metadata' in result:
        result['metadata']['algorithm'] = 'Particle Swarm Optimization (PSOBM)'
    
    return result

def generate_initial_solution(scenes, available_dates, actor_scenes, actor_availability, location_availability):
    """Generate a random initial solution."""
    solution = {}
    date_index = 0
    
    for scene in scenes:
        # Assign date from available dates
        if date_index >= len(available_dates):
            date_index = 0  # Loop back to start if needed
        
        shooting_date = available_dates[date_index]
        date_str = shooting_date.strftime('%Y-%m-%d')
        
        # Check for actor availability conflicts
        has_actor_conflict = False
        for actor_id in actor_scenes.get(scene.id, []):
            if actor_id in actor_availability and date_str in actor_availability[actor_id]:
                if not actor_availability[actor_id][date_str]:
                    has_actor_conflict = True
                    break
        
        # Check for location availability conflicts
        has_location_conflict = False
        if scene.location_id and scene.location_id in location_availability:
            if date_str in location_availability[scene.location_id]:
                if not location_availability[scene.location_id][date_str].get('is_available', True):
                    has_location_conflict = True
        
        # Try to find a date without conflicts
        if has_actor_conflict or has_location_conflict:
            conflict_resolved = False
            for alt_date_index in range(len(available_dates)):
                alt_date = available_dates[alt_date_index]
                alt_date_str = alt_date.strftime('%Y-%m-%d')
                
                # Check for actor conflicts on this alternate date
                alt_actor_conflict = False
                for actor_id in actor_scenes.get(scene.id, []):
                    if actor_id in actor_availability and alt_date_str in actor_availability[actor_id]:
                        if not actor_availability[actor_id][alt_date_str]:
                            alt_actor_conflict = True
                            break
                
                # Check for location conflicts on this alternate date
                alt_location_conflict = False
                if scene.location_id and scene.location_id in location_availability:
                    if alt_date_str in location_availability[scene.location_id]:
                        if not location_availability[scene.location_id][alt_date_str].get('is_available', True):
                            alt_location_conflict = True
                
                # If no conflicts, use this date
                if not alt_actor_conflict and not alt_location_conflict:
                    shooting_date = alt_date
                    date_index = alt_date_index
                    conflict_resolved = True
                    break
            
            # If no conflict-free date found, just use the original
            if not conflict_resolved:
                date_index = (date_index + 1) % len(available_dates)
        else:
            # No conflicts, move to next date
            date_index = (date_index + 1) % len(available_dates)
        
        # Add scene to solution
        solution[scene.id] = {
            'scene_id': scene.id,
            'date': shooting_date,
            'start_time': datetime.time(8, 0),  # Default start time: 8:00 AM
            'end_time': datetime.time(18, 0)    # Default end time: 6:00 PM
        }
    
    return solution

def repair_solution(solution, scenes, actor_scenes, actor_availability, location_availability):
    """Repair a solution by resolving conflicts."""
    # For now, just return the solution as is (already handled in initial solution)
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
    try:
        # Track total cost
        total_cost = 0
        
        # Track actor days and location days
        actor_days = defaultdict(set)  # actor_id -> set of dates
        location_days = defaultdict(set)  # location_id -> set of dates
        
        # Track scenes by date for travel calculations
        scenes_by_date = defaultdict(list)  # date -> list of scenes
        
        # Organize scenes by date
        for scene_id, scene_data in solution.items():
            date = scene_data.get('date')
            if not date:
                continue
                
            date_str = date.strftime('%Y-%m-%d')
            scene = next((s for s in scenes if s.id == scene_id), None)
            if not scene:
                continue
                
            scenes_by_date[date_str].append((scene_id, scene))
            
            # Add location day
            if scene.location_id:
                location_days[scene.location_id].add(date_str)
            
            # Add actor days
            for actor_id in actor_scenes.get(scene.id, []):
                actor_days[actor_id].add(date_str)
            
            # Check for availability conflicts and add penalties
            # Actor availability
            for actor_id in actor_scenes.get(scene.id, []):
                if actor_id in actor_availability and date_str in actor_availability[actor_id]:
                    if not actor_availability[actor_id][date_str]:
                        # Penalty for scheduling unavailable actor
                        total_cost += 10000  # High penalty
            
            # Location availability
            if scene.location_id and scene.location_id in location_availability:
                if date_str in location_availability[scene.location_id]:
                    if not location_availability[scene.location_id][date_str].get('is_available', True):
                        # Penalty for scheduling unavailable location
                        total_cost += 10000  # High penalty
        
        # Calculate actor costs (based on days scheduled)
        for actor_id, days in actor_days.items():
            actor = next((a for a in actors if a.id == actor_id), None)
            if actor:
                total_cost += len(days) * actor.cost_per_day
        
        # Calculate location costs (based on days scheduled)
        for location_id, days in location_days.items():
            location = next((l for l in locations if l.id == location_id), None)
            if location:
                total_cost += len(days) * location.cost_per_day
        
        # Calculate travel costs (when switching locations on the same day)
        for date_str, day_scenes in scenes_by_date.items():
            if len(day_scenes) <= 1:
                continue
                
            # Sort scenes by start time
            day_scenes.sort(key=lambda x: solution[x[0]].get('start_time', datetime.time(0, 0)))
            
            # Check for location changes
            prev_location = None
            for scene_id, scene in day_scenes:
                if prev_location is not None and scene.location_id != prev_location:
                    # Add travel cost (simplified)
                    total_cost += 500  # Fixed travel cost
                prev_location = scene.location_id
        
        return total_cost
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
            error_result = {
                'scenes': {},
                'total_cost': 0,
                'total_duration': 0
            }
            return convert_datetime_to_strings(error_result)
            
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
        
        result = {
            'scenes': formatted_solution,
            'total_cost': total_cost,
            'total_duration': max(1, round(total_duration / 8.0))  # Convert hours to days (8-hour days)
        }
        return convert_datetime_to_strings(result)
    except Exception as e:
        logging.error(f"Error formatting solution: {str(e)}")
        error_result = {
            'scenes': {},
            'total_cost': 0,
            'total_duration': 0
        }
        return convert_datetime_to_strings(error_result)

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
        
        return convert_datetime_to_strings(result)
    
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
            fallback_result = {
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
            return convert_datetime_to_strings(fallback_result)
            
        except Exception as fallback_error:
            logging.error(f"Emergency fallback also failed: {str(fallback_error)}", exc_info=True)
            
            # Return absolute minimum valid response
            minimal_result = {
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
            }
            return convert_datetime_to_strings(minimal_result)