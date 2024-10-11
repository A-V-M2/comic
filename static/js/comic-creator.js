let comicId = null;
let sortable = null;

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    comicId = urlParams.get('id');
    
    if (comicId) {
        loadComic(comicId);
    }
    
    document.getElementById('comic-form').addEventListener('submit', handleComicCreation);
    document.getElementById('save-comic').addEventListener('click', saveComic);
    document.getElementById('back-to-dashboard').addEventListener('click', () => {
        window.location.href = '/dashboard';
    });
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
});

async function handleComicCreation(e) {
    e.preventDefault();
    const prompt = document.getElementById('prompt').value;
    
    try {
        const response = await fetch('/create-comic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt }),
        });
        
        const result = await response.json();
        if (result.success) {
            comicId = result.comic_id;
            displayComic(result);
            document.getElementById('save-comic').style.display = 'block';
            initSortable();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('An error occurred. Please try again.', 'error');
    }
}

function displayComic(comicData) {
    const storyContainer = document.getElementById('story-container');
    const tilesContainer = document.getElementById('tiles-container');
    
    storyContainer.innerHTML = `
        <h3>Story:</h3>
        <p>${comicData.story}</p>
    `;
    
    tilesContainer.innerHTML = '';
    comicData.tiles.forEach((tile, index) => {
        const tileElement = document.createElement('div');
        tileElement.className = 'comic-tile';
        tileElement.dataset.index = index;
        tileElement.innerHTML = `
            <h4>Tile ${index + 1}</h4>
            <img src="${tile.image}" alt="Tile ${index + 1}" width="512" height="384">
            <p>${tile.scene}</p>
        `;
        tilesContainer.appendChild(tileElement);
    });
    
    const inspirationElement = document.createElement('div');
    inspirationElement.innerHTML = `
        <h3>Inspiration:</h3>
        <p>${comicData.inspiration}</p>
    `;
    document.getElementById('comic-output').appendChild(inspirationElement);
}

function initSortable() {
    const tilesContainer = document.getElementById('tiles-container');
    sortable = new Sortable(tilesContainer, {
        animation: 150,
        direction: 'horizontal',
        onEnd: handleTileReorder
    });
}

async function handleTileReorder(event) {
    const tiles = Array.from(document.querySelectorAll('.comic-tile')).map(tile => ({
        scene: tile.querySelector('p').textContent,
        image: tile.querySelector('img').src
    }));
    
    try {
        const response = await fetch('/update-comic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ comic_id: comicId, tiles }),
        });
        
        const result = await response.json();
        if (result.success) {
            showMessage('Comic updated successfully!', 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('An error occurred while updating the comic.', 'error');
    }
}

async function saveComic() {
    try {
        const response = await fetch('/update-comic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ comic_id: comicId }),
        });
        
        const result = await response.json();
        if (result.success) {
            showMessage('Comic saved successfully!', 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('An error occurred while saving the comic.', 'error');
    }
}

async function loadComic(id) {
    try {
        const response = await fetch(`/load-comic/${id}`);
        const comic = await response.json();
        displayComic(comic);
        document.getElementById('save-comic').style.display = 'block';
        initSortable();
    } catch (error) {
        showMessage('Error loading comic. Please try again.', 'error');
    }
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