document.addEventListener('DOMContentLoaded', function() {
    const saveButton = document.getElementById('save-note');
    const categorySelect = document.getElementById('category');
    const messageTextarea = document.getElementById('message');
    const notesList = document.getElementById('notes');

    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const category = categorySelect.value;
            const message = messageTextarea.value;

            if (message.trim() === '') {
                alert('Please enter a note');
                return;
            }

            fetch('/save_note', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({category, message}),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Note saved successfully');
                    messageTextarea.value = '';
                    loadNotes();
                }
            })
            .catch((error) => {
                console.error('Error:', error);
            });
        });
    }

    function loadNotes() {
        fetch('/get_notes')
        .then(response => response.json())
        .then(notes => {
            notesList.innerHTML = '';
            notes.forEach(note => {
                const li = document.createElement('li');
                li.textContent = `${note.category}: ${note.message}`;
                notesList.appendChild(li);
            });
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }

    if (notesList) {
        loadNotes();
    }
});