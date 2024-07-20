# Adventure Game Application

This is an interactive adventure game application that generates unique stories and scenes using AI. It features dynamic scene generation, image creation, and text-to-speech capabilities.

## Prerequisites

- Python 3.7+
- pip (Python package installer)
- OpenAI API key
- ElevenLabs API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/fltman/thergame.git
   cd thergame
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ELEVENLABS_KEY=your_elevenlabs_api_key_here
   ```

## Project Structure

```
.
├── .env
├── app.py
├── audio_cache/
├── instance/
├── static/
│   ├── audio/
│   ├── css/
│   │   └── style.css
│   └── images/
├── templates/
│   ├── index.html
│   └── scene.html
└── requirements.txt
```

## Database Setup

The application uses SQLite as its database. To initialize the database, run:

```
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

## Running the Application

To start the application, run:

```
python app.py
```

The application will be available at `http://127.0.0.1:5000/`.

## Features

- Dynamic scene generation using OpenAI's GPT-4
- Image generation for scenes using DALL-E 3
- Text-to-speech functionality using ElevenLabs API
- Caching of audio files for improved performance
- Interactive web interface for game progression

## Customization

- Modify the `generate_random_setup_prompt()` and `generate_random_start_prompt()` functions in `app.py` to change the game's initial setup and starting prompts.
- Adjust the temperature and other parameters in the `get_openai_response()` function to control the AI's creativity level.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Creative Commons Attribution (CC-BY) license.

Copyright (c) 2024 Anders Bjarby

This work is licensed under the Creative Commons Attribution 4.0 International License. To view a copy of this license, visit http://creativecommons.org/licenses/by/4.0/ or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

