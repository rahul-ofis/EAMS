document.addEventListener('DOMContentLoaded', function() {
    const formToggleSwitch = document.getElementById('form-toggle-switch');

    // Fetch initial status from MongoDB
    fetch('/get_form_status')
        .then(response => response.json())
        .then(data => {
            formToggleSwitch.checked = data.form_active;
        })
        .catch(error => console.error('Error fetching form status', error));

    // Handle toggle change
    formToggleSwitch.addEventListener('change', function() {
        fetch('/toggle_form', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ active: this.checked })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(this.checked ? 'Form activated for users' : 'Form deactivated for users');
            } else {
                alert('Error updating form status');
                this.checked = !this.checked; // Revert toggle if failed
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error updating form status');
            this.checked = !this.checked; 
        });
    });
});