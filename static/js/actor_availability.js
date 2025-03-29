document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const actorSelect = document.getElementById('actor-select');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const generateBtn = document.getElementById('generate-calendar-btn');
    const calendarContainer = document.getElementById('availability-calendar');
    const markUnavailableBtn = document.getElementById('mark-unavailable-btn');
    const markAvailableBtn = document.getElementById('mark-available-btn');
    
    // Global variables
    let selectedActorId = null;
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
    
    // Actor selection
    if (actorSelect) {
        actorSelect.addEventListener('change', function() {
            selectedActorId = this.value;
            clearSelectedDates();
        });
    }
    
    // Actor list items
    const actorListItems = document.querySelectorAll('.actor-list-item');
    
    actorListItems.forEach(item => {
        item.addEventListener('click', function(event) {
            event.preventDefault();
            
            // Update selected actor
            const actorId = this.getAttribute('data-actor-id');
            if (actorSelect) {
                actorSelect.value = actorId;
                selectedActorId = actorId;
                clearSelectedDates();
            }
            
            // Highlight selected item
            actorListItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Generate calendar
    if (generateBtn) {
        generateBtn.addEventListener('click', function() {
            if (!selectedActorId) {
                showAlert('Please select an actor first.', 'warning');
                return;
            }
            
            const startDate = startDateInput.value;
            const endDate = endDateInput.value;
            
            if (!startDate || !endDate) {
                showAlert('Please select start and end dates.', 'warning');
                return;
            }
            
            generateCalendar(selectedActorId, startDate, endDate);
        });
    }
    
    // Generate calendar function
    function generateCalendar(actorId, startDateStr, endDateStr) {
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
            
            if (availabilityData[actorId] && availabilityData[actorId][dateStr] !== undefined) {
                isAvailable = availabilityData[actorId][dateStr];
            }
            
            dateCell.className = isAvailable ? 'available' : 'unavailable';
            dateCell.setAttribute('data-date', dateStr);
            
            // Add date number
            const dateNumber = document.createElement('div');
            dateNumber.className = 'date-number';
            dateNumber.textContent = currentDate.getDate();
            dateCell.appendChild(dateNumber);
            
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
        if (!selectedActorId) {
            showAlert('Please select an actor first.', 'warning');
            return;
        }
        
        if (selectedDates.length === 0) {
            showAlert('Please select dates first.', 'warning');
            return;
        }
        
        // Update each date
        let updateCount = 0;
        const totalUpdates = selectedDates.length;
        
        selectedDates.forEach(date => {
            // Prepare data
            const data = {
                actor_id: selectedActorId,
                date: date,
                is_available: isAvailable
            };
            
            // Send AJAX request
            fetch('/api/actor-availability', {
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
                    if (!availabilityData[selectedActorId]) {
                        availabilityData[selectedActorId] = {};
                    }
                    
                    availabilityData[selectedActorId][date] = isAvailable;
                    
                    // Update UI
                    const dateCell = document.querySelector(`.calendar-table td[data-date="${date}"]`);
                    if (dateCell) {
                        dateCell.className = isAvailable ? 'available selected' : 'unavailable selected';
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