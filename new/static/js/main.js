document.addEventListener('DOMContentLoaded', function() {
    // Form toggling for HR
    const toggleFormButton = document.getElementById('toggle-form');
    if (toggleFormButton) {
        toggleFormButton.addEventListener('click', function() {
            fetch('/toggle_form', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ is_enabled: this.textContent === 'Enable Form' }),
            })
            .then(response => response.text())
            .then(result => {
                if (result === 'OK') {
                    this.textContent = this.textContent === 'Enable Form' ? 'Disable Form' : 'Enable Form';
                }
            });
        });
    }

    // Notification check for regular users
    const notification = document.getElementById('notification');
    if (notification) {
        setInterval(function() {
            fetch('/get_form_status')
                .then(response => response.json())
                .then(data => {
                    if (data.enabled) {
                        notification.classList.remove('hidden');
                    } else {
                        notification.classList.add('hidden');
                    }
                });
        }, 5000); // Check every 5 seconds
    }

    // Dynamic form handling
    const dynamicForm = document.getElementById('dynamic-form');
    if (dynamicForm) {
        fetch('/get_form_status')
            .then(response => response.json())
            .then(data => {
                if (!data.enabled) {
                    dynamicForm.innerHTML = '<p>The form is currently disabled by HR.</p>';
                }
            });
    }

    // Fetch critical incidents for form
    const fetchCriticalIncidentsButtons = document.querySelectorAll('.fetch-critical-incidents');
    fetchCriticalIncidentsButtons.forEach(button => {
        button.addEventListener('click', function() {
            const category = this.dataset.category;
            fetch(`/get_critical-incidents/${category}`)
                .then(response => response.json())
                .then(critical_incidents => {
                    const input = document.getElementById(category);
                    if (critical_incidents.length > 0) {
                        input.value = critical_incidents[critical_incidents.length - 1]; // Set the most recent critical incident
                    }
                });
        });
    });

    // Handle goal form submission
    const goalForm = document.getElementById('goal-form');
    if (goalForm) {
        goalForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const formData = new FormData(goalForm);
            const data = {
                description: formData.get('description'),
                weightage: formData.get('weightage'),
                time_period: formData.get('time_period'),
                ranking: formData.get('ranking'),
                feedback: formData.get('feedback')
            };
            fetch('/api/goals', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    location.reload();
                }
            });
        });
    }
});
