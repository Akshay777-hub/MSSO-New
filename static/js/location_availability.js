document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const locationSelect = document.getElementById('location-select');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const generateBtn = document.getElementById('generate-calendar-btn');
    const calendarContainer = document.getElementById('availability-calendar');
    const markUnavailableBtn = document.getElementById('mark-unavailable-btn');
    const markAvailableBtn = document.getElementById('mark-available-btn');
    const startTimeInput = document.getElementById('start-time');
    const endTimeInput = document.getElementById('end-time');
    
    // Global variables
    let selectedLocationId = null;
    let availabilityData = {};
    let selectedDates = [];
    
    // Initialize
    try {
        // Parse availability data from server
        const availabilityDataStr = document.querySelector('[data-availability]')?.getAttribute('data-availability');
        if (availabilityDataStr) {
            availabilityData = JSON.parse(availabilityDataStr);
        }
    } catch (error) {
        console.error('Error parsing availability data:', error);
    }
    
    // Location selection
    if (locationSelect) {
        locationSelect.addEventListener('change', function() {
            selectedLocationId = this.value;
            clearSelectedDates();
        });
    }
    
    // Location list items
    const locationListItems = document.querySelectorAll('.location-list-item');
    
    locationListItems.forEach(item => {
        item.addEventListener('click', function(event) {
            event.preventDefault();
            
            // Update selected location
            const locationId = this.getAttribute('data-location-id');
            if (locationSelect) {
                locationSelect.value = locationId;
                selectedLocationId = locationId;
                clearSelectedDates();
            }
            
            // Highlight selected item
            locationListItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Generate calendar
    if (generateBtn) {
        generateBtn.addEventListener('click', function() {
            if (!selectedLocationId) {
                showAlert('Please select a location first.', 'warning');
                return;
            }
            
            const startDate = startDateInput.value;
            const endDate = endDateInput.value;
            
            if (!startDate || !endDate) {
                showAlert('Please select start and end dates.', 'warning');
                return;
            }
            
            generateCalendar(selectedLocationId, startDate, endDate);
        });
    }
    
    // Generate calendar function
    function generateCalendar(locationId, startDateStr, endDateStr) {
        // Parse dates
        const startDate = new Date(startDateStr);
        const endDate = new Date(endDateStr);
        
        // Validate date range
        if (startDate > endDate) {
            showAlert('Start date must be before end date.', 'warning');
            return;
        }
        
        // Clear previous calendar
        calendarContainer.innerHTML = '';
        
        // Create calendar table
        const table = document.createElement('table');
        table.className = 'table table-bordered calendar-table';
        
        // Create header row with month names
        const thead = document.createElement('thead');
        const monthRow = document.createElement('tr');
        
        // Create day headers (Mon, Tue, etc.)
        const dayRow = document.createElement('tr');
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        
        dayNames.forEach(day => {
            const th = document.createElement('th');
            th.textContent = day;
            dayRow.appendChild(th);
        });
        
        thead.appendChild(monthRow);
        thead.appendChild(dayRow);
        table.appendChild(thead);
        
        // Create calendar body
        const tbody = document.createElement('tbody');
        
        // Create date cells
        let currentDate = new Date(startDate);
        let currentRow = document.createElement('tr');
        
        // Add empty cells for days before the start date
        const firstDayOfWeek = currentDate.getDay();
        for (let i = 0; i < firstDayOfWeek; i++) {
            const emptyCell = document.createElement('td');
            emptyCell.className = 'empty-cell';
            currentRow.appendChild(emptyCell);
        }
        
        // Fill in dates until end date
        while (currentDate <= endDate) {
            // Start a new row at the beginning of a week
            if (currentDate.getDay() === 0 && currentDate > startDate) {
                tbody.appendChild(currentRow);
                currentRow = document.createElement('tr');
            }
            
            // Create date cell
            const dateCell = document.createElement('td');
            const dateStr = formatDate(currentDate);
            
            // Set availability classes
            let isAvailable = true;
            let timeRange = '';
            
            if (availabilityData[locationId] && availabilityData[locationId][dateStr] !== undefined) {
                isAvailable = availabilityData[locationId][dateStr].is_available;
                
                // Show time range if available
                if (isAvailable && availabilityData[locationId][dateStr].start_time && availabilityData[locationId][dateStr].end_time) {
                    timeRange = `${availabilityData[locationId][dateStr].start_time} - ${availabilityData[locationId][dateStr].end_time}`;
                }
            }
            
            dateCell.className = isAvailable ? 'available' : 'unavailable';
            dateCell.setAttribute('data-date', dateStr);
            
            // Add date number
            const dateNumber = document.createElement('div');
            dateNumber.className = 'date-number';
            dateNumber.textContent = currentDate.getDate();
            dateCell.appendChild(dateNumber);
            
            // Add time range if available
            if (timeRange) {
                const timeRangeDiv = document.createElement('div');
                timeRangeDiv.className = 'time-range';
                timeRangeDiv.textContent = timeRange;
                dateCell.appendChild(timeRangeDiv);
            }
            
            // Add click event
            dateCell.addEventListener('click', function(event) {
                // Toggle selection with Ctrl key
                if (event.ctrlKey || event.metaKey) {
                    this.classList.toggle('selected');
                    
                    const dateStr = this.getAttribute('data-date');
                    
                    if (this.classList.contains('selected')) {
                        // Add to selected dates
                        if (!selectedDates.includes(dateStr)) {
                            selectedDates.push(dateStr);
                        }
                    } else {
                        // Remove from selected dates
                        const index = selectedDates.indexOf(dateStr);
                        if (index !== -1) {
                            selectedDates.splice(index, 1);
                        }
                    }
                } else {
                    // Clear all selections and select just this one
                    document.querySelectorAll('.calendar-table td').forEach(cell => {
                        cell.classList.remove('selected');
                    });
                    
                    this.classList.add('selected');
                    selectedDates = [this.getAttribute('data-date')];
                }
            });
            
            currentRow.appendChild(dateCell);
            
            // Move to next day
            currentDate.setDate(currentDate.getDate() + 1);
        }
        
        // Add empty cells for days after the end date
        const lastDayOfWeek = currentDate.getDay();
        if (lastDayOfWeek > 0) {
            for (let i = lastDayOfWeek; i < 7; i++) {
                const emptyCell = document.createElement('td');
                emptyCell.className = 'empty-cell';
                currentRow.appendChild(emptyCell);
            }
        }
        
        // Add the last row
        tbody.appendChild(currentRow);
        
        table.appendChild(tbody);
        calendarContainer.appendChild(table);
        
        // Show tools
        const toolsContainer = document.createElement('div');
        toolsContainer.className = 'calendar-tools mt-3 d-flex justify-content-between';
        
        const helpText = document.createElement('p');
        helpText.className = 'mb-0 text-muted';
        helpText.innerHTML = 'Use <kbd>Ctrl+Click</kbd> to select multiple dates';
        
        toolsContainer.appendChild(helpText);
        calendarContainer.appendChild(toolsContainer);
    }
    
    // Mark available/unavailable buttons
    if (markAvailableBtn) {
        markAvailableBtn.addEventListener('click', function() {
            updateAvailability(true);
        });
    }
    
    if (markUnavailableBtn) {
        markUnavailableBtn.addEventListener('click', function() {
            updateAvailability(false);
        });
    }
    
    // Update availability function
    function updateAvailability(isAvailable) {
        if (!selectedLocationId) {
            showAlert('Please select a location first.', 'warning');
            return;
        }
        
        if (selectedDates.length === 0) {
            showAlert('Please select dates first.', 'warning');
            return;
        }
        
        // Get time range if available
        let startTime = null;
        let endTime = null;
        
        if (isAvailable && startTimeInput && endTimeInput) {
            startTime = startTimeInput.value;
            endTime = endTimeInput.value;
            
            if (startTime && endTime && startTime >= endTime) {
                showAlert('Start time must be before end time.', 'warning');
                return;
            }
        }
        
        // Update each date
        let updateCount = 0;
        const totalUpdates = selectedDates.length;
        
        selectedDates.forEach(date => {
            // Prepare data
            const data = {
                location_id: selectedLocationId,
                date: date,
                is_available: isAvailable,
                start_time: startTime,
                end_time: endTime
            };
            
            // Send AJAX request
            fetch('/api/location-availability', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    updateCount++;
                    
                    // Update local data
                    if (!availabilityData[selectedLocationId]) {
                        availabilityData[selectedLocationId] = {};
                    }
                    
                    availabilityData[selectedLocationId][date] = {
                        is_available: isAvailable,
                        start_time: startTime,
                        end_time: endTime
                    };
                    
                    // Update UI
                    const dateCell = document.querySelector(`.calendar-table td[data-date="${date}"]`);
                    if (dateCell) {
                        dateCell.className = isAvailable ? 'available selected' : 'unavailable selected';
                        
                        // Update time range
                        const existingTimeRange = dateCell.querySelector('.time-range');
                        if (existingTimeRange) {
                            existingTimeRange.remove();
                        }
                        
                        if (isAvailable && startTime && endTime) {
                            const timeRangeDiv = document.createElement('div');
                            timeRangeDiv.className = 'time-range';
                            timeRangeDiv.textContent = `${startTime} - ${endTime}`;
                            dateCell.appendChild(timeRangeDiv);
                        }
                    }
                    
                    // Show success message when all updates are done
                    if (updateCount === totalUpdates) {
                        showAlert(`Successfully updated availability for ${updateCount} dates.`, 'success');
                    }
                } else {
                    showAlert(`Error updating date ${date}: ${result.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('Failed to update availability. See console for details.', 'danger');
            });
        });
    }
    
    // Helper functions
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    function clearSelectedDates() {
        selectedDates = [];
        document.querySelectorAll('.calendar-table td').forEach(cell => {
            cell.classList.remove('selected');
        });
    }
    
    function showAlert(message, type = 'info') {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Find alert container or use calendar container
        const alertContainer = document.querySelector('.alert-container') || calendarContainer;
        
        // Insert at the beginning
        alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
});