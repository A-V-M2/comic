document.addEventListener('DOMContentLoaded', () => {
    loadComics();
    document.getElementById('create-new-comic').addEventListener('click', () => {
        window.location.href = '/create-comic';
    });
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
});

async function loadComics() {
    try {
        const response = await fetch('/get-comics');
        const data = await response.json();
        if (data.success) {
            displayComics(data.comics);
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Error loading comics. Please try again.', 'error');
    }
}

function displayComics(comics) {
    const comicsList = document.getElementById('comics-list');
    comicsList.innerHTML = '';
    if (comics.length === 0) {
        comicsList.innerHTML = '<p>No comics found. Create your first comic!</p>';
        return;
    }
    comics.forEach(comic => {
        const comicElement = document.createElement('div');
        comicElement.className = 'comic-item';
        comicElement.innerHTML = `
            <h3>${comic.title}</h3>
            <p>Created: ${new Date(comic.created_at).toLocaleString()}</p>
            <button onclick="editComic('${comic.id}')">Edit</button>
        `;
        comicsList.appendChild(comicElement);
    });
}

function editComic(comicId) {
    window.location.href = `/create-comic?id=${comicId}`;
}

async function handleLogout() {
    try {
        const response = await fetch('/logout', {
            method: 'POST',
        });
        const data = await response.json();
        if (data.success) {
            window.location.href = '/login';
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Error logging out. Please try again.', 'error');
    }
}

function showMessage(message, type) {
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    messageElement.className = type === 'error' ? 'error-message' : 'success-message';
    document.body.appendChild(messageElement);
    setTimeout(() => {
        messageElement.remove();
    }, 5000);
}