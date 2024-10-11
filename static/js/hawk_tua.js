let comicId = null;
let autosaveInterval;

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
    document.getElementById('preview-comic').addEventListener('click', generateComicPreview);
    
    initializeSortable();
    startAutosave();
    setupKeyboardShortcuts();
});

function initializeSortable() {
    new Sortable(document.getElementById('comic-tiles'), {
        animation: 150,
        onEnd: function() {
            // You can add logic here to update the order of tiles if needed
        }
    });
}

function showLoadingOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.innerHTML = '<div class="spinner"></div><p>Creating your comic...</p>';
    document.body.appendChild(overlay);
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

async function handleApiResponse(response) {
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'An error occurred');
    }
    return response.json();
}

async function handleComicCreation(e) {
    e.preventDefault();
    const title = document.getElementById('comic-title').value || generateAutoTitle();
    const prompt = document.getElementById('prompt').value;
    
    showLoadingOverlay();
    
    try {
        const result = await fetch('/create-comic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ title, prompt }),
        }).then(handleApiResponse);

        if (result.success) {
            comicId = result.comic_id;
            displayTiles(result.tiles);
            document.getElementById('comic-title').value = result.title;
            document.getElementById('comic-story').textContent = result.story;
            document.getElementById('comic-inspiration').textContent = result.inspiration;
            showMessage('Comic created successfully!');
            startAutosave();
        } else {
            showError(result.message);
        }
    } catch (error) {
        showError(error.message || 'An error occurred. Please try again.');
    } finally {
        hideLoadingOverlay();
    }
}

function displayTiles(tiles) {
    const tilesContainer = document.getElementById('comic-tiles');
    tilesContainer.innerHTML = '';
    tiles.forEach((tile, index) => {
        const tileElement = document.createElement('div');
        tileElement.classList.add('comic-tile');
        tileElement.innerHTML = `
            <h3>Tile ${index + 1}</h3>
            <p contenteditable="true">${tile.scene}</p>
            <img src="${tile.image}" alt="Scene ${index + 1}" onerror="this.src='/placeholder-image.jpg'">
            <button onclick="regenerateImage(${index})">Regenerate Image</button>
        `;
        tilesContainer.appendChild(tileElement);
    });
    paginateTiles(Array.from(tilesContainer.children));
}

async function regenerateImage(tileIndex) {
    const tile = document.querySelectorAll('.comic-tile')[tileIndex];
    const scene = tile.querySelector('p').textContent;
    try {
        const result = await fetch('/generate-image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ scene }),
        }).then(handleApiResponse);

        if (result.success) {
            tile.querySelector('img').src = result.image_url;
        } else {
            showError('Failed to regenerate image. Please try again.');
        }
    } catch (error) {
        showError(error.message || 'An error occurred while regenerating the image.');
    }
}

async function saveComic() {
    const title = document.getElementById('comic-title').value || generateAutoTitle();
    const tiles = Array.from(document.querySelectorAll('.comic-tile')).map(tile => ({
        scene: tile.querySelector('p').textContent,
        image: tile.querySelector('img').src
    }));
    
    try {
        const result = await fetch('/update-comic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ comic_id: comicId, title, tiles }),
        }).then(handleApiResponse);

        if (result.success) {
            showMessage('Comic saved successfully!');
        } else {
            showError(result.message);
        }
    } catch (error) {
        showError(error.message || 'An error occurred while saving the comic.');
    }
}

async function loadComic(id) {
    try {
        const comic = await fetch(`/load-comic/${id}`).then(handleApiResponse);
        document.getElementById('comic-title').value = comic.title;
        document.getElementById('prompt').value = comic.prompt;
        document.getElementById('comic-story').textContent = comic.story;
        document.getElementById('comic-inspiration').textContent = comic.inspiration;
        displayTiles(comic.tiles);
    } catch (error) {
        showError(error.message || 'Error loading comic. Please try again.');
    }
}

function generateAutoTitle() {
    const date = new Date();
    return `Untitled Comic - ${date.toLocaleDateString()}`;
}

async function handleLogout() {
    try {
        const data = await fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        }).then(handleApiResponse);

        if (data.success) {
            window.location.href = '/login';
        } else {
            showError(data.message);
        }
    } catch (error) {
        showError(error.message || 'Error logging out. Please try again.');
    }
}

function showError(message) {
    hideLoadingOverlay();
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    document.body.appendChild(errorElement);
    setTimeout(() => {
        errorElement.remove();
    }, 5000);
}

function showMessage(message) {
    hideLoadingOverlay();
    const messageElement = document.createElement('div');
    messageElement.className = 'success-message';
    messageElement.textContent = message;
    document.body.appendChild(messageElement);
    setTimeout(() => {
        messageElement.remove();
    }, 5000);
}

function generateComicPreview() {
    const title = document.getElementById('comic-title').value;
    const story = document.getElementById('comic-story').textContent;
    const inspiration = document.getElementById('comic-inspiration').textContent;
    const tiles = Array.from(document.querySelectorAll('.comic-tile'));

    const previewContainer = document.createElement('div');
    previewContainer.className = 'comic-preview';

    previewContainer.innerHTML = `
        <h2>${title}</h2>
        <h3>Story</h3>
        <p>${story}</p>
        <h3>Inspiration</h3>
        <p>${inspiration}</p>
        <h3>Tiles</h3>
        <div class="tiles-preview">
            ${tiles.map((tile, index) => `
                <div class="tile-preview">
                    <h4>Tile ${index + 1}</h4>
                    <img src="${tile.querySelector('img').src}" alt="Tile ${index + 1}">
                    <p>${tile.querySelector('p').textContent}</p>
                </div>
            `).join('')}
        </div>
    `;

    // You can either append this to the document or use it to create a modal
    document.body.appendChild(previewContainer);
}

function paginateTiles(tiles, tilesPerPage = 5) {
    const totalPages = Math.ceil(tiles.length / tilesPerPage);
    let currentPage = 1;

    function showPage(page) {
        const start = (page - 1) * tilesPerPage;
        const end = start + tilesPerPage;
        const pageItems = tiles.slice(start, end);

        const tilesContainer = document.getElementById('comic-tiles');
        tilesContainer.innerHTML = '';
        pageItems.forEach(tile => tilesContainer.appendChild(tile));

        updatePaginationControls();
    }

    function updatePaginationControls() {
        const controls = document.getElementById('pagination-controls');
        controls.innerHTML = `
            <button ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(-1)">Previous</button>
            <span>Page ${currentPage} of ${totalPages}</span>
            <button ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(1)">Next</button>
        `;
    }

    window.changePage = function(delta) {
        currentPage = Math.max(1, Math.min(totalPages, currentPage + delta));
        showPage(currentPage);
    }

    showPage(1);
}

function startAutosave() {
    stopAutosave(); // Clear any existing interval
    autosaveInterval = setInterval(saveComic, 60000); // Autosave every minute
}

function stopAutosave() {
    clearInterval(autosaveInterval);
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 's':
                    e.preventDefault();
                    saveComic();
                    break;
                case 'p':
                    e.preventDefault();
                    generateComicPreview();
                    break;
                // Add more shortcuts as needed
            }
        }
    });
}
let scene, camera, renderer, particles;

function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    renderer = new THREE.WebGLRenderer({ alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    // Set canvas as background
    renderer.domElement.style.position = 'fixed';
    renderer.domElement.style.top = '0';
    renderer.domElement.style.left = '0';
    renderer.domElement.style.zIndex = '-1';

    createParticles();

    camera.position.z = 5;

    window.addEventListener('resize', onWindowResize, false);
    document.addEventListener('mousemove', onMouseMove, false);

    animate();
}

function createParticles() {
    const geometry = new THREE.BufferGeometry();
    const vertices = [];

    for (let i = 0; i < 5000; i++) {
        const x = Math.random() * 2000 - 1000;
        const y = Math.random() * 2000 - 1000;
        const z = Math.random() * 2000 - 1000;

        vertices.push(x, y, z);
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

    const material = new THREE.PointsMaterial({
        color: 0x00ffff,
        size: 2,
        transparent: true
    });

    particles = new THREE.Points(geometry, material);
    scene.add(particles);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function onMouseMove(event) {
    const mouseX = (event.clientX / window.innerWidth) * 2 - 1;
    const mouseY = -(event.clientY / window.innerHeight) * 2 + 1;

    particles.rotation.x += mouseY * 0.005;
    particles.rotation.y += mouseX * 0.005;
}

function animate() {
    requestAnimationFrame(animate);

    particles.rotation.x += 0.001;
    particles.rotation.y += 0.001;

    renderer.render(scene, camera);
}

init();