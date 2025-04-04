document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const optimizationForm = document.getElementById('optimization-form');
    const algorithmSelect = document.getElementById('algorithm');
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    const actorCostFactorSlider = document.getElementById('actor-cost-factor');
    const locationCostFactorSlider = document.getElementById('location-cost-factor');
    const travelCostFactorSlider = document.getElementById('travel-cost-factor');
    const durationCostFactorSlider = document.getElementById('duration-cost-factor');
    const optimizationResult = document.getElementById('optimization-result');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Cost factor value displays
    const actorCostFactorValue = document.getElementById('actor-cost-factor-value');
    const locationCostFactorValue = document.getElementById('location-cost-factor-value');
    const travelCostFactorValue = document.getElementById('travel-cost-factor-value');
    const durationCostFactorValue = document.getElementById('duration-cost-factor-value');
    
    // Update displayed cost factor values when sliders change
    if (actorCostFactorSlider && actorCostFactorValue) {
        actorCostFactorSlider.addEventListener('input', function() {
            actorCostFactorValue.textContent = this.value;
        });
    }
    
    if (locationCostFactorSlider && locationCostFactorValue) {
        locationCostFactorSlider.addEventListener('input', function() {
            locationCostFactorValue.textContent = this.value;
        });
    }
    
    if (travelCostFactorSlider && travelCostFactorValue) {
        travelCostFactorSlider.addEventListener('input', function() {
            travelCostFactorValue.textContent = this.value;
        });
    }
    
    if (durationCostFactorSlider && durationCostFactorValue) {
        durationCostFactorSlider.addEventListener('input', function() {
            durationCostFactorValue.textContent = this.value;
        });
    }
    
    // Update algorithm description based on selection
    if (algorithmSelect) {
        const algorithmDescription = document.getElementById('algorithm-description');
        
        algorithmSelect.addEventListener('change', function() {
            if (algorithmDescription) {
                const selectedAlgorithm = this.value;
                
                if (selectedAlgorithm === 'ant_colony') {
                    algorithmDescription.innerHTML = '<strong>Ant Colony Optimization</strong>: Simulates ant behavior to find the optimal path through a graph. Best for complex scheduling with many constraints.';
                } else if (selectedAlgorithm === 'tabu_search') {
                    algorithmDescription.innerHTML = '<strong>Tabu Search</strong>: Uses memory structures to avoid revisiting recent solutions. Good for avoiding local optima in complex problems.';
                } else if (selectedAlgorithm === 'particle_swarm') {
                    algorithmDescription.innerHTML = '<strong>Particle Swarm Optimization</strong>: Inspired by bird flocking behavior. Balanced approach that works well for many scheduling scenarios.';
                }
            }
        });
    }
    
    // Form submission
    if (optimizationForm) {
        optimizationForm.addEventListener('submit', function(event) {
            // Prevent default form submission
            event.preventDefault();
            
            // Validate form inputs
            if (!validateOptimizationForm()) {
                return;
            }
            
            // Show loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.remove('d-none');
            }
            
            // Clear previous results
            if (optimizationResult) {
                optimizationResult.innerHTML = '';
            }
            
            // Get form data
            const formData = new FormData(this);
            const formDataObj = {};
            
            formData.forEach((value, key) => {
                formDataObj[key] = value;
            });
            
            // Send API request
            fetch('/api/optimize-schedule', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formDataObj),
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 400 || response.status === 500) {
                        // Try to parse the error response as JSON
                        return response.text().then(text => {
                            try {
                                return { success: false, message: JSON.parse(text).message || 'Server error occurred' };
                            } catch (e) {
                                // If parsing fails, return the HTML directly for debugging
                                console.error("Response is not valid JSON:", text);
                                return { success: false, message: 'Server returned non-JSON response' };
                            }
                        });
                    }
                    throw new Error(`Server error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Hide loading indicator
                if (loadingIndicator) {
                    loadingIndicator.classList.add('d-none');
                }
                
                if (data.success) {
                    // The expected path for success
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                        return;
                    }
                    // Handle both old and new response formats
                    if (data.result && data.metadata) {
                        // Old format with separate result and metadata
                        displaySchedule(data.result, data.metadata);
                    } else if (data.schedule && data.schedule.scenes) {
                        // New format with schedule.scenes and schedule.metadata
                        displaySchedule(data.schedule.scenes, data.schedule.metadata || {});
                    } else {
                        console.error("Unexpected data structure:", data);
                        showAlert('Received unexpected data structure from server', 'warning');
                    }
                } else {
                    showAlert(data.message || 'Optimization failed', 'danger');
                }
            })
            .catch(error => {
                console.error('Error during optimization:', error);
                
                // Hide loading indicator
                if (loadingIndicator) {
                    loadingIndicator.classList.add('d-none');
                }
                
                showAlert('An error occurred during optimization. Please try again or check the console for details.', 'danger');
            });
        });
    }
    
    // Validate form inputs
    function validateOptimizationForm() {
        let isValid = true;
        
        // Check if algorithm is selected
        if (!algorithmSelect || !algorithmSelect.value) {
            showAlert('Please select an optimization algorithm.', 'warning');
            isValid = false;
        }
        
        // Check date range
        if (startDateInput && endDateInput && startDateInput.value && endDateInput.value) {
            const startDate = new Date(startDateInput.value);
            const endDate = new Date(endDateInput.value);
            
            if (startDate > endDate) {
                showAlert('Start date must be before end date.', 'warning');
                isValid = false;
            }
        } else if (startDateInput && !startDateInput.value) {
            showAlert('Please select a start date.', 'warning');
            isValid = false;
        }
        
        return isValid;
    }
    
    // Display schedule results
    function displaySchedule(scheduleData, metadata) {
        if (!optimizationResult) return;
        
        // Create schedule header
        const scheduleHeader = document.createElement('div');
        scheduleHeader.className = 'schedule-header mb-4';
        
        // Add schedule summary
        const summaryHTML = `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">Schedule Summary</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <div class="stat-card bg-primary-subtle text-center p-3">
                                <div class="stat-value">$${metadata.total_cost.toLocaleString()}</div>
                                <div class="stat-label">Total Cost</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="stat-card bg-success-subtle text-center p-3">
                                <div class="stat-value">${metadata.total_days} days</div>
                                <div class="stat-label">Shooting Duration</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="stat-card bg-info-subtle text-center p-3">
                                <div class="stat-value">${metadata.total_scenes}</div>
                                <div class="stat-label">Total Scenes</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        scheduleHeader.innerHTML = summaryHTML;
        optimizationResult.appendChild(scheduleHeader);
        
        // Group scenes by date
        const scenesByDate = {};
        
        Object.values(scheduleData).forEach(scene => {
            if (!scenesByDate[scene.shooting_date]) {
                scenesByDate[scene.shooting_date] = [];
            }
            scenesByDate[scene.shooting_date].push(scene);
        });
        
        // Create schedule timeline
        const scheduleTimeline = document.createElement('div');
        scheduleTimeline.className = 'schedule-timeline';
        
        // Sort dates
        const sortedDates = Object.keys(scenesByDate).sort();
        
        // Create day elements
        sortedDates.forEach(date => {
            const dayElement = document.createElement('div');
            dayElement.className = 'timeline-day';
            
            // Format date for display
            const dateObj = new Date(date);
            const dateDisplay = dateObj.toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric'
            });
            
            // Create date indicator
            const dateIndicator = document.createElement('div');
            dateIndicator.className = 'timeline-date';
            dateIndicator.textContent = dateDisplay;
            dayElement.appendChild(dateIndicator);
            
            // Create timeline dot
            const timelineDot = document.createElement('div');
            timelineDot.className = 'timeline-dot';
            dayElement.appendChild(timelineDot);
            
            // Add scenes for this day
            scenesByDate[date].forEach(scene => {
                const sceneElement = document.createElement('div');
                sceneElement.className = 'timeline-scene';
                
                // Calculate scene duration
                const durationDisplay = scene.estimated_duration ? `${scene.estimated_duration}h` : 'N/A';
                
                // Scene HTML
                sceneElement.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h5 class="mb-0">Scene ${scene.scene_number}</h5>
                        <span class="badge bg-secondary">${scene.int_ext}</span>
                    </div>
                    <div class="scene-location mb-2">
                        <i class="fas fa-map-marker-alt me-1"></i>
                        ${scene.location_name || 'No Location'}
                    </div>
                    <div class="row">
                        <div class="col-md-4">
                            <div class="mb-2">
                                <strong>Time:</strong> ${scene.time_of_day || 'N/A'}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-2">
                                <strong>Duration:</strong> ${durationDisplay}
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-2">
                                <strong>Cost:</strong> $${scene.estimated_cost?.toLocaleString() || 'N/A'}
                            </div>
                        </div>
                    </div>
                    <div class="scene-description text-muted small">
                        ${scene.description || 'No description available'}
                    </div>
                `;
                
                dayElement.appendChild(sceneElement);
            });
            
            scheduleTimeline.appendChild(dayElement);
        });
        
        // Add save button
        const saveButtonContainer = document.createElement('div');
        saveButtonContainer.className = 'text-center mt-4';
        saveButtonContainer.innerHTML = `
            <form action="/save-schedule" method="post">
                <input type="hidden" name="schedule_data" value='${JSON.stringify(scheduleData)}'>
                <input type="hidden" name="algorithm" value="${algorithmSelect ? algorithmSelect.value : ''}">
                <input type="hidden" name="name" value="Schedule - ${new Date().toLocaleDateString()}">
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save me-1"></i> Save This Schedule
                </button>
            </form>
        `;
        
        // Add elements to container
        optimizationResult.appendChild(scheduleTimeline);
        optimizationResult.appendChild(saveButtonContainer);
        
        // Scroll to results
        optimizationResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Show alert message
    function showAlert(message, type = 'info') {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Find alert container
        const alertContainer = document.querySelector('.alert-container');
        if (alertContainer) {
            // Insert at the beginning
            alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
        } else if (optimizationResult) {
            // Insert before schedule container
            optimizationResult.parentNode.insertBefore(alertDiv, optimizationResult);
        }
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
});