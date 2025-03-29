document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const approveScheduleBtn = document.getElementById('approve-schedule-btn');
    const notifyActorsBtn = document.getElementById('notify-actors-btn');
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const printScheduleBtn = document.getElementById('print-schedule-btn');
    
    // Initialize any tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Approve schedule button
    if (approveScheduleBtn) {
        approveScheduleBtn.addEventListener('click', function(event) {
            event.preventDefault();
            
            const scheduleId = this.getAttribute('data-schedule-id');
            if (!scheduleId) return;
            
            // Show confirmation dialog
            if (confirm('Are you sure you want to approve this schedule? This action cannot be undone.')) {
                // Send API request
                fetch(`/approve-schedule/${scheduleId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert('Schedule approved successfully!', 'success');
                        
                        // Disable button
                        approveScheduleBtn.disabled = true;
                        approveScheduleBtn.classList.remove('btn-primary');
                        approveScheduleBtn.classList.add('btn-secondary');
                        
                        // Enable notify button if it exists
                        if (notifyActorsBtn) {
                            notifyActorsBtn.disabled = false;
                        }
                    } else {
                        showAlert(data.message || 'Failed to approve schedule', 'danger');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('An error occurred while approving the schedule', 'danger');
                });
            }
        });
    }
    
    // Notify actors button
    if (notifyActorsBtn) {
        notifyActorsBtn.addEventListener('click', function(event) {
            event.preventDefault();
            
            const scheduleId = this.getAttribute('data-schedule-id');
            if (!scheduleId) return;
            
            // Show confirmation dialog
            if (confirm('Are you sure you want to send notifications to all actors? They will be notified by email about their shooting dates.')) {
                // Show loading state
                const originalText = this.innerHTML;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...';
                this.disabled = true;
                
                // Send API request
                fetch(`/notify-actors/${scheduleId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    // Reset button
                    this.innerHTML = originalText;
                    this.disabled = false;
                    
                    if (data.success) {
                        showAlert(`Notifications sent successfully to ${data.count} actors`, 'success');
                    } else {
                        showAlert(data.message || 'Failed to send notifications', 'danger');
                    }
                })
                .catch(error => {
                    // Reset button
                    this.innerHTML = originalText;
                    this.disabled = false;
                    
                    console.error('Error:', error);
                    showAlert('An error occurred while sending notifications', 'danger');
                });
            }
        });
    }
    
    // Export PDF button
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function(event) {
            event.preventDefault();
            
            const scheduleId = this.getAttribute('data-schedule-id');
            if (!scheduleId) return;
            
            // Redirect to PDF export URL
            window.location.href = `/export-schedule-pdf/${scheduleId}`;
        });
    }
    
    // Print schedule button
    if (printScheduleBtn) {
        printScheduleBtn.addEventListener('click', function(event) {
            event.preventDefault();
            window.print();
        });
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
        } else {
            // Create alert container if it doesn't exist
            const mainContent = document.querySelector('main');
            const newAlertContainer = document.createElement('div');
            newAlertContainer.className = 'container alert-container mt-3';
            newAlertContainer.appendChild(alertDiv);
            
            if (mainContent && mainContent.firstChild) {
                mainContent.insertBefore(newAlertContainer, mainContent.firstChild);
            }
        }
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
});