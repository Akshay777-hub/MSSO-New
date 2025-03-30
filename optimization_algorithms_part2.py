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
