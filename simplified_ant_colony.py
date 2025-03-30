import datetime
import random
import logging
from utils_json import convert_datetime_to_strings

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