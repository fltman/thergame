from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
import json
import os
import uuid
import requests
from dotenv import load_dotenv
import logging
import bleach
import hashlib
import random

# Load environment variables and setup logging
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Initialize Flask app and database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///game.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

elevenlabs_api_key = os.getenv("ELEVENLABS_KEY")

# Initialize OpenAI client
client = OpenAI()

CACHE_DIR = "audio_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Models
class Scene(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('scene.id'), nullable=True)
    text = db.Column(db.String(1000), nullable=False)
    image_path = db.Column(db.String(300), nullable=True)
    option_1_text = db.Column(db.String(300), nullable=True)
    option_1_id = db.Column(db.Integer, db.ForeignKey('scene.id'), nullable=True)
    option_2_text = db.Column(db.String(300), nullable=True)
    option_2_id = db.Column(db.Integer, db.ForeignKey('scene.id'), nullable=True)
    option_3_text = db.Column(db.String(300), nullable=True)
    option_3_id = db.Column(db.Integer, db.ForeignKey('scene.id'), nullable=True)

    def __repr__(self):
        return f'<Scene {self.id}>'

class Setup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scene_id = db.Column(db.Integer, db.ForeignKey('scene.id'), nullable=False)
    prompt = db.Column(db.String(1000), nullable=False)
    
    scene = db.relationship('Scene', backref='setup', lazy=True)
    
    def __repr__(self):
        return f'<Setup {self.id}>'

# Routes
@app.route('/')
def index():
    start_scenes = Scene.query.filter_by(parent_id=None).all()
    setup_prompt = generate_random_setup_prompt()
    start_prompt = generate_random_start_prompt()
    
    # Check for existing images in the static/images folder
    static_img_path = os.path.join(app.static_folder, 'images')
    background_image_path = get_random_image(static_img_path)
    
    if not background_image_path:
        # If no images are available, generate a new one
        background_prompt = "A mystical and atmospheric landscape for an adventure game background"
        background_image_path = generate_and_save_image(background_prompt)
        
    return render_template('index.html', 
                           start_scenes=start_scenes, 
                           start_prompt=start_prompt, 
                           setup_prompt=setup_prompt,
                           background_image=background_image_path)

def get_random_image(folder_path):
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    if image_files:
        return os.path.join('images', random.choice(image_files))
    return None

@app.route('/create_adventure', methods=['POST'])
def create_adventure():
    try:
        setup_prompt = request.form['setup_prompt']
        start_prompt = request.form['start_prompt']
        
        logging.info(f"Creating new adventure with setup_prompt: {setup_prompt[:50]}... and start_prompt: {start_prompt[:50]}...")
        
        new_scene, new_setup = generate_first_scene(setup_prompt, start_prompt)
        
        logging.info(f"Successfully created new adventure. Scene ID: {new_scene.id}, Setup ID: {new_setup.id}")
        
        # Redirect to the URL for the newly created scene
        return redirect(url_for('scene', scene_id=new_scene.id))
    except Exception as e:
        logging.error(f"Error in create_adventure: {str(e)}", exc_info=True)
        db.session.rollback()  # Rollback the session in case of error
        return "An error occurred while creating the adventure. Please try again.", 500

@app.route('/scene/<int:scene_id>')
def scene(scene_id):
    scene = Scene.query.get_or_404(scene_id)
    return render_template('scene.html', scene=scene)

@app.route('/scene/<int:scene_id>/<int:choice>')
def scene_choice(scene_id, choice):
    current_scene = Scene.query.get_or_404(scene_id)
    
    if choice not in [1, 2, 3]:
        return "Invalid choice", 400
    
    next_scene_id = getattr(current_scene, f'option_{choice}_id')
    
    if next_scene_id:
        return redirect(url_for('scene', scene_id=next_scene_id))
    else:
        new_scene = generate_new_scene(current_scene, choice)
        db.session.add(new_scene)
        setattr(current_scene, f'option_{choice}_id', new_scene.id)
        db.session.commit()
        return redirect(url_for('scene', scene_id=new_scene.id))

def generate_checksum(text):
    return hashlib.md5(text.encode()).hexdigest()

@app.route('/play', methods=['POST'])
def play_audio():
    data = request.json
    text = data.get('text', '')
    
    checksum = generate_checksum(text)
    cache_file = os.path.join(CACHE_DIR, f"{checksum}.mp3")
    
    if os.path.exists(cache_file):
        return send_file(cache_file, mimetype="audio/mpeg")
    
    url = "https://api.elevenlabs.io/v1/text-to-speech/YREPt7KOziuJoYyc1RTB"
    
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "language_code": "sv",
        "voice_settings": {
            "stability": 0.31,
            "similarity_boost": 0.97,
            "style": 0.50,
            "use_speaker_boost": True
        },
        "seed": 123,
    }
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": f"{elevenlabs_api_key}"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        with open(cache_file, "wb") as f:
            f.write(response.content)
        return send_file(cache_file, mimetype="audio/mpeg")
    else:
        return jsonify({"error": f"Error: {response.status_code}"}), response.status_code
    
# Helper functions
def get_openai_response(messages, response_format=None):
    """
    Helper function to get a response from the OpenAI API.
    """
    kwargs = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0.7
    }
    if response_format:
        kwargs["response_format"] = response_format

    chat_completion = client.chat.completions.create(**kwargs)
    return chat_completion.choices[0].message.content

def build_history_array(scene):
    history = []
    current = scene
    
    while current:
        history.append({"role": "assistant", "content": current.text})
        
        if current.parent_id:
            parent_scene = Scene.query.get(current.parent_id)
            option_text = get_option_text_that_led_to_scene(parent_scene, current.id)
            history.append({"role": "user", "content": option_text})
            current = parent_scene
        else:
            if current.setup:
                setup_prompt = current.setup[0].prompt
                history.append({"role": "system", "content": setup_prompt})
            break
    
    return list(reversed(history))

def get_option_text_that_led_to_scene(parent_scene, child_scene_id):
    for i in range(1, 4):
        if getattr(parent_scene, f'option_{i}_id') == child_scene_id:
            return getattr(parent_scene, f'option_{i}_text')
    return "Unknown option"

# AI functions
def generate_new_scene(current_scene, choice):
    messages = build_history_array(current_scene)
    choice_text = getattr(current_scene, f'option_{choice}_text')
    messages.append({
        "role": "user", 
        "content": f"User selected ```{choice_text}```. Generate this scene description. The user shall have also be given three options and you should take your original instructions in consideration when designing those options. Generate a detailed description of what the scene looks like. Reply with a json with the parameters: scene_description, image_description, user_option_1, user_option_2, user_option_3. the descriptions should be no longer that 300 characters. The description can be formatted using html tags such as <p> <i> <b>. The options no longer than 100 characters."
    })
    
    response = get_openai_response(messages, response_format={"type": "json_object"})
    data = json.loads(response)
    image_path = generate_and_save_image(data['image_description'])
    
    # Sanitize the HTML content
    allowed_tags = ['p', 'i', 'b', 'em', 'strong']
    sanitized_description = bleach.clean(data['scene_description'], tags=allowed_tags, strip=True)
    
    new_scene = Scene(
        text=sanitized_description,
        image_path=image_path,
        parent_id=current_scene.id,
        option_1_text=data['user_option_1'],
        option_2_text=data['user_option_2'],
        option_3_text=data['user_option_3']
    )
    
    return new_scene

def generate_first_scene(setup_prompt, start_prompt):
    messages = [
        {"role": "system", "content": setup_prompt},
        {"role": "assistant", "content": start_prompt},
        {"role": "user", "content": "Generate the first scene description and welcome the user to the game. The user shall have also be given three options and you should take your original instructions in consideration when designing those options. Generate a detailed description of what the scene looks like. Reply with a json with the parameters: scene_description, image_description, user_option_1, user_option_2, user_option_3. the descriptions should be no longer that 400 characters. The options no longer than 100 characters."}
    ]
    
    response = get_openai_response(messages, response_format={"type": "json_object"})
    data = json.loads(response)
    image_path = generate_and_save_image(data['image_description'])
    
    new_scene = Scene(
        text=data['scene_description'],
        image_path=image_path,
        option_1_text=data['user_option_1'],
        option_2_text=data['user_option_2'],
        option_3_text=data['user_option_3']
    )
    db.session.add(new_scene)
    db.session.flush()  # This will assign an ID to new_scene without committing the transaction
    
    new_setup = Setup(scene_id=new_scene.id, prompt=setup_prompt)
    db.session.add(new_setup)
    
    try:
        db.session.commit()  # Commit both new_scene and new_setup in a single transaction
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in generate_first_scene: {str(e)}")
        raise
    
    return new_scene, new_setup

def generate_random_start_prompt():
    messages = [
        {"role": "user", "content": "Generate a short mysterious setup for an adventure game, no more that 150 characters."},
    ]
    return get_openai_response(messages)

def generate_random_setup_prompt():
    messages = [
        {"role": "user", "content": "Generate a short set of instructions to the game master about the point of this game and how it can act, don't mention anything about where or how or when it takes place or what the story is about. Use no more than 400 characters. EXAMPLE: You will act as an exciting adventure game. Questions to the user shall be about learning about math."}
    ]
    return get_openai_response(messages)

# Image and audio functions
def generate_and_save_image(prompt):
    print (f"DEBUG: generating image: {prompt}")
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    
    image_url = response.data[0].url
    image_response = requests.get(image_url)
    
    image_filename = f"background_{uuid.uuid4()}.png"
    image_path = os.path.join("static", "images", image_filename)
    
    with open(image_path, "wb") as file:
        file.write(image_response.content)
        
    return f"images/{image_filename}"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)