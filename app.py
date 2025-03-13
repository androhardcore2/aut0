from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
import google.generativeai as genai
from elevenlabs import generate, save, set_api_key
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ColorClip, concatenate_audioclips, CompositeAudioClip
import tempfile
import logging
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/music', exist_ok=True)

# Global variables
model = None

def initialize_gemini():
    """Initialize Gemini model with proper error handling"""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("Gemini API key not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        global model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Test the model with a simple prompt
        test_response = model.generate_content("Hello")
        if not test_response.text:
            raise Exception("Model test failed - empty response")
            
        logger.info("Gemini model initialized and tested successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def initialize_elevenlabs():
    """Initialize ElevenLabs with proper error handling"""
    try:
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            raise ValueError("ElevenLabs API key not found in environment variables")
        
        set_api_key(api_key)
        logger.info("ElevenLabs initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize ElevenLabs: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# Initialize APIs
if not initialize_gemini():
    logger.error("Failed to initialize Gemini - text generation will be unavailable")

if not initialize_elevenlabs():
    logger.error("Failed to initialize ElevenLabs - speech generation will be unavailable")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-text', methods=['POST'])
def generate_text():
    try:
        if not model:
            raise Exception("Gemini model not initialized")

        data = request.get_json()
        if not data:
            raise ValueError("No JSON data received")

        prompt = data.get('prompt')
        if not prompt:
            raise ValueError("No prompt provided")

        if len(prompt) > 500:
            raise ValueError("Prompt too long (max 500 characters)")

        logger.info(f"Generating text for prompt: {prompt[:50]}...")

        # Configure generation parameters
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]

        generation_config = {
            "temperature": 0.9,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 2048,
        }

        # Generate content
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if not response:
            raise Exception("No response from Gemini API")

        if not response.text:
            raise Exception("Empty response from Gemini API")

        generated_text = response.text.strip()
        if not generated_text:
            raise Exception("Generated text is empty after processing")

        logger.info("Text generated successfully")
        return jsonify({
            'success': True,
            'text': generated_text
        })

    except ValueError as e:
        logger.warning(f"Validation error in generate_text: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in generate_text: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': "Failed to generate text. Please try again."
        }), 500

@app.route('/download-video', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data received")

        query = data.get('query')
        if not query:
            raise ValueError("No search query provided")

        orientation = data.get('orientation', 'landscape')
        if orientation not in ['landscape', 'portrait']:
            raise ValueError("Invalid orientation specified")

        api_key = os.getenv('PEXELS_API_KEY')
        if not api_key:
            raise Exception("Pexels API key not configured")

        headers = {'Authorization': api_key}
        
        logger.info(f"Searching for {orientation} video: {query}")
        
        response = requests.get(
            f'https://api.pexels.com/videos/search?query={query}&per_page=10&orientation={orientation}',
            headers=headers
        )

        if response.status_code != 200:
            raise Exception(f"Pexels API error: {response.status_code}")

        data = response.json()
        if not data.get('videos'):
            raise Exception("No videos found")

        # Find suitable video
        selected_video = None
        for video in data['videos']:
            video_files = video.get('video_files', [])
            if not video_files:
                continue

            # Get the highest quality MP4 file under 10MB
            suitable_files = [
                f for f in video_files
                if f['file_type'] == 'video/mp4' and f.get('width', 0) >= 720
            ]
            
            if suitable_files:
                selected_video = suitable_files[0]
                break

        if not selected_video:
            raise Exception("No suitable video found")

        # Download video
        video_url = selected_video['link']
        logger.info(f"Downloading video from: {video_url}")
        
        video_response = requests.get(video_url, stream=True)
        if video_response.status_code != 200:
            raise Exception("Failed to download video file")

        video_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_video.mp4')
        with open(video_path, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info("Video downloaded successfully")
        return jsonify({
            'success': True,
            'path': video_path
        })

    except ValueError as e:
        logger.warning(f"Validation error in download_video: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in download_video: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': "Failed to download video. Please try again."
        }), 500

@app.route('/generate-speech', methods=['POST'])
def generate_speech():
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data received")

        text = data.get('text')
        if not text:
            raise ValueError("No text provided")

        if len(text) > 5000:
            raise ValueError("Text too long (max 5000 characters)")

        logger.info("Generating speech from text")
        
        audio = generate(
            text=text,
            voice="21m00Tcm4TlvDq8ikWAM",
            model="eleven_monolingual_v1"
        )
        
        if not audio:
            raise Exception("Failed to generate audio")

        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_audio.mp3')
        save(audio, audio_path)
        
        logger.info("Speech generated successfully")
        return jsonify({
            'success': True,
            'path': audio_path
        })

    except ValueError as e:
        logger.warning(f"Validation error in generate_speech: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in generate_speech: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': "Failed to generate speech. Please try again."
        }), 500

@app.route('/create-video', methods=['POST'])
def create_video():
    try:
        data = request.get_json()
        if not data:
            raise ValueError("No JSON data received")

        required_fields = ['video_path', 'audio_path', 'text_content']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        video_path = data['video_path']
        audio_path = data['audio_path']
        text_content = data['text_content']
        use_background_music = data.get('background_music') == 'yes'
        background_volume = float(data.get('background_volume', 0.3))
        orientation = data.get('orientation', 'landscape')

        if not os.path.exists(video_path):
            raise ValueError("Video file not found")
        if not os.path.exists(audio_path):
            raise ValueError("Audio file not found")

        logger.info("Starting video creation process")

        # Load video and audio
        video = VideoFileClip(video_path)
        voiceover = AudioFileClip(audio_path)

        # Process background music if requested
        if use_background_music:
            try:
                bg_music = AudioFileClip('static/music/background.mp3')
                if bg_music.duration < voiceover.duration:
                    loops_needed = int(voiceover.duration / bg_music.duration) + 1
                    bg_music = concatenate_audioclips([bg_music] * loops_needed)
                bg_music = bg_music.subclip(0, voiceover.duration)
                bg_music = bg_music.volumex(background_volume)
                final_audio = CompositeAudioClip([voiceover, bg_music])
            except Exception as e:
                logger.error(f"Background music processing failed: {str(e)}")
                final_audio = voiceover
        else:
            final_audio = voiceover

        # Resize video
        if orientation == 'portrait':
            video = video.resize(width=720)
        else:
            video = video.resize(height=720)

        # Create text overlays
        clips = [video]
        sentences = [s.strip() for s in text_content.split('.') if s.strip()]
        
        text_width = int(video.w * 0.8)
        text_y_position = 0.8 if orientation == 'landscape' else 0.9

        for i, text in enumerate(sentences):
            try:
                bg_height = 80 if orientation == 'landscape' else 100
                bg_clip = ColorClip(
                    size=(video.w, bg_height),
                    color=(0, 0, 0)
                ).set_opacity(0.5)
                bg_clip = bg_clip.set_position(('center', text_y_position), relative=True)
                bg_clip = bg_clip.set_start(i * 3).set_duration(3)
                
                txt_clip = TextClip(
                    text,
                    fontsize=30 if orientation == 'landscape' else 25,
                    color='white',
                    size=(text_width, None),
                    method='caption'
                )
                txt_clip = txt_clip.set_position(('center', text_y_position), relative=True)
                txt_clip = txt_clip.set_start(i * 3).set_duration(3)
                
                clips.extend([bg_clip, txt_clip])
            except Exception as e:
                logger.error(f"Error creating text overlay: {str(e)}")
                continue

        # Combine clips and audio
        final_video = CompositeVideoClip(clips)
        final_video = final_video.set_audio(final_audio)
        final_duration = min(video.duration, voiceover.duration)
        final_video = final_video.set_duration(final_duration)

        # Export video
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'final_video.mp4')
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            threads=2,
            preset='ultrafast'
        )

        # Cleanup
        video.close()
        voiceover.close()
        if use_background_music and 'bg_music' in locals():
            bg_music.close()
        final_video.close()

        logger.info("Video created successfully")
        return jsonify({
            'success': True,
            'path': output_path
        })

    except ValueError as e:
        logger.warning(f"Validation error in create_video: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in create_video: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': "Failed to create video. Please try again."
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        if not filename:
            raise ValueError("No filename provided")

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            raise ValueError("File not found")

        return send_file(file_path, as_attachment=True)

    except ValueError as e:
        logger.warning(f"Validation error in download_file: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error in download_file: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': "Failed to download file. Please try again."
        }), 500

@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Unhandled error: {str(error)}")
    logger.error(traceback.format_exc())
    return jsonify({
        'success': False,
        'error': "An unexpected error occurred. Please try again."
    }), 500

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=8080, debug=True)
