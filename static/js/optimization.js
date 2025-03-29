document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const algorithmCards = document.querySelectorAll('.algorithm-card');
    const optimizeForm = document.getElementById('optimize-form');
    const algorithmInput = document.getElementById('algorithm');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const actorWeightSlider = document.getElementById('actor-weight');
    const locationWeightSlider = document.getElementById('location-weight');
    const travelWeightSlider = document.getElementById('travel-weight');
    const scheduleContainer = document.getElementById('schedule-result');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Weight value displays
    const actorWeightValue = document.getElementById('actor-weight-value');
    const locationWeightValue = document.getElementById('location-weight-value');
    const travelWeightValue = document.getElementById('travel-weight-value');
    
    // Update displayed weight values when sliders change
    if (actorWeightSlider && actorWeightValue) {
        actorWeightSlider.addEventListener('input', function() {
            actorWeightValue.textContent = this.value;
        });
    }
    
    if (locationWeightSlider && locationWeightValue) {
        locationWeightSlider.addEventListener('input', function() {
            locationWeightValue.textContent = this.value;
        });
    }
    
    if (travelWeightSlider && travelWeightValue) {
        travelWeightSlider.addEventListener('input', function() {
            travelWeightValue.textContent = this.value;
        });
    }
    
    // Algorithm card selection
    if (algorithmCards.length > 0) {
        algorithmCards.forEach(card => {
            card.addEventListener('click', function() {
                // Remove selected class from all cards
                algorithmCards.forEach(c => c.classList.remove('selected'));
                
                // Add selected class to clicked card
                this.classList.add('selected');
                
                // Update hidden input with selected algorithm
                if (algorithmInput) {
                    algorithmInput.value = this.getAttribute('data-algorithm');
                }
            });
        });
        
        // Select first algorithm by default
        algorithmCards[0].click();
    }
    
    // Form submission
    if (optimizeForm) {
        optimizeForm.addEventListener('submit', function(event) {
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
            if (scheduleContainer) {
                scheduleContainer.innerHTML = '';
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
            .then(response => response.json())
            .then(data => {
                // Hide loading indicator
                if (loadingIndicator) {
                    loadingIndicator.classList.add('d-none');
                }
                
                if (data.success) {
                    displaySchedule(data.result, data.metadata);
                } else {
                    showAlert(data.message || 'Optimization failed', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                
                // Hide loading indicator
                if (loadingIndicator) {
                    loadingIndicator.classList.add('d-none');
                }
                
                showAlert('An error occurred during optimization. See console for details.', 'danger');
            });
        });
    }
    
    // Validate form inputs
    function validateOptimizationForm() {
        let isValid = true;
        
        // Check if algorithm is selected
        if (!algorithmInput || !algorithmInput.value) {
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
        if (!scheduleContainer) return;
        
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
        scheduleContainer.appendChild(scheduleHeader);
        
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
                <input type="hidden" name="algorithm" value="${algorithmInput ? algorithmInput.value : ''}">
                <input type="hidden" name="name" value="Schedule - ${new Date().toLocaleDateString()}">
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save me-1"></i> Save This Schedule
                </button>
            </form>
        `;
        
        // Add elements to container
        scheduleContainer.appendChild(scheduleTimeline);
        scheduleContainer.appendChild(saveButtonContainer);
        
        // Scroll to results
        scheduleContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
        } else if (scheduleContainer) {
            // Insert before schedule container
            scheduleContainer.parentNode.insertBefore(alertDiv, scheduleContainer);
        }
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
});