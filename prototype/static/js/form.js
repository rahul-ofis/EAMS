document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('category-form');
    const addInputButtons = document.querySelectorAll('.add-input');

    // Function to add a new input field
    function addInputField(category) {
        const inputsContainer = document.getElementById(`${category}-inputs`);
        const newInput = document.createElement('input');
        newInput.type = 'text';
        newInput.name = `${category}[]`;
        inputsContainer.appendChild(newInput);
    }

    // Add event listeners to "Add Input" buttons
    addInputButtons.forEach(button => {
        button.addEventListener('click', function() {
            const category = this.dataset.category;
            addInputField(category);
        });
    });

    // Fetch notes by category and populate the form
    fetch('/get_notes_by_category')
        .then(response => response.json())
        .then(data => {
            for (const [category, messages] of Object.entries(data)) {
                const inputsContainer = document.getElementById(`${category}-inputs`);
                inputsContainer.innerHTML = ''; // Clear existing inputs
                messages.forEach((message, index) => {
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.name = `${category}[]`;
                    input.value = message;
                    input.required = index === 0; // Make only the first input required
                    inputsContainer.appendChild(input);
                });
                // Add an empty input if there are no messages
                if (messages.length === 0) {
                    addInputField(category);
                }
            }
        })
        .catch(error => console.error('Error:', error));

    // Handle form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = {
            category1: Array.from(document.getElementsByName('category1[]')).map(input => input.value),
            category2: Array.from(document.getElementsByName('category2[]')).map(input => input.value),
            category3: Array.from(document.getElementsByName('category3[]')).map(input => input.value)
        };

        fetch('/save_form', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Form saved successfully');
            } else {
                alert('Error saving form');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving form');
        });
    });
});

