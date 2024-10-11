import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from api import ComicStoryGenerator
from model import StableDiffusionModel
import uuid
import logging
from PIL import Image
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
bcrypt = Bcrypt(app)

# Initialize Firebase
cred = credentials.Certificate("auth/comic-435406-firebase-adminsdk-a9hfu-9f39b11124.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize the Stable Diffusion model
logger.info("Loading Stable Diffusion model...")
stable_diffusion_model = StableDiffusionModel()
logger.info("Stable Diffusion model loaded successfully.")

def generate_title(prompt):
    words = prompt.split()[:3]
    return " ".join(words).capitalize() + "..."

def get_image_for_scene(scene_description):
    """
    Generate an image using Stable Diffusion based on the scene description.
    """
    try:
        # Generate image
        negative_prompt = "photorealistic, 3D rendering, smooth gradients, detailed textures, plain background"
        image = stable_diffusion_model.generate_image(
            scene_description, 
            negative_prompt=negative_prompt,
            num_inference_steps=10,
            guidance_scale=7.5,
            width=640,
            height=960
        )
        
        if image:
            # Save the image to a file
            image_id = str(uuid.uuid4())
            image_filename = f'{image_id}.png'
            image_path = os.path.join('static', 'generated_images', image_filename)
            image.save(image_path)
            
            # Return the URL to the image
            return url_for('static', filename=f'generated_images/{image_filename}', _external=True)
        else:
            logger.error("Failed to generate image")
            return "https://via.placeholder.com/300x200?text=Image+Not+Available"
    except Exception as e:
        logger.error(f"Error generating image with Stable Diffusion: {e}")
        # Return a placeholder image URL on error
        return "https://via.placeholder.com/300x200?text=Image+Not+Available"

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.json
            username = data['username']
            email = data['email']
            password = data['password']

            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1)
            if len(query.get()) > 0:
                return jsonify({'success': False, 'message': 'Email already registered'}), 400

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user_data = {
                'username': username,
                'email': email,
                'password': hashed_password
            }
            new_user = users_ref.add(user_data)
            session['user_id'] = new_user[1].id

            return jsonify({'success': True, 'message': 'User registered successfully'}), 201
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.json
            email = data['email']
            password = data['password']

            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1)
            user_docs = query.get()

            if len(user_docs) == 0:
                return jsonify({'success': False, 'message': 'User not found'}), 404

            user_data = user_docs[0].to_dict()
            if bcrypt.check_password_hash(user_data['password'], password):
                session['user_id'] = user_docs[0].id
                return jsonify({'success': True, 'message': 'Login successful'}), 200
            else:
                return jsonify({'success': False, 'message': 'Incorrect password'}), 401

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/create-comic', methods=['GET', 'POST'])
def create_comic():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            data = request.json
            prompt = data['prompt']
            title = data.get('title') or generate_title(prompt)
            
            # Use the ComicStoryGenerator to generate the story and tiles
            comic_generator = ComicStoryGenerator()
            story = comic_generator.generate_story(prompt)
            tiles = comic_generator.create_comic_tiles(story)
            inspiration = comic_generator.find_inspiration_source(story)
            
            # Limit the number of tiles if necessary
            num_tiles = min(len(tiles), 15)  # Limit to 15 tiles maximum
            tiles = tiles[:num_tiles]
            
            # Get images for each tile using Stable Diffusion
            for tile in tiles:
                tile['image'] = get_image_for_scene(tile['scene'])
            
            comic_id = str(uuid.uuid4())
            db.collection('comics').document(comic_id).set({
                'user_id': session['user_id'],
                'title': title,
                'prompt': prompt,
                'story': story,
                'tiles': tiles,
                'inspiration': inspiration,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            return jsonify({
                'success': True,
                'comic_id': comic_id,
                'title': title,
                'story': story,
                'tiles': tiles,
                'inspiration': inspiration
            })
        except Exception as e:
            logger.error(f"Error creating comic: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    return render_template('comic-creator.html')

@app.route('/update-comic', methods=['POST'])
def update_comic():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    data = request.json
    comic_id = data['comic_id']
    title = data.get('title')
    tiles = data.get('tiles')
    
    update_data = {}
    if title:
        update_data['title'] = title
    if tiles:
        update_data['tiles'] = tiles
    
    db.collection('comics').document(comic_id).update(update_data)
    
    return jsonify({'success': True})

@app.route('/get-comics', methods=['GET'])
def get_comics():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    comics = db.collection('comics').where('user_id', '==', session['user_id']).get()
    comics_list = [{
        'id': doc.id,
        'title': doc.to_dict().get('title', 'Untitled'),
        'created_at': doc.to_dict().get('created_at')
    } for doc in comics]
    return jsonify({'success': True, 'comics': comics_list})

@app.route('/load-comic/<comic_id>')
def load_comic(comic_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comic = db.collection('comics').document(comic_id).get().to_dict()
    return jsonify(comic)

if __name__ == '__main__':
    app.run(debug=True)