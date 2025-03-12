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

# Initialize APIs
def init_apis():
    try:
        # Gemini API
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            logger.info("Gemini API initialized successfully")
        else:
            logger.warning("Gemini API key not found")
        
        # ElevenLabs API
        elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        if elevenlabs_api_key:
            set_api_key(elevenlabs_api_key)
            logger.info("ElevenLabs API initialized successfully")
        else:
            logger.warning("ElevenLabs API key not found")
    except Exception as e:
        logger.error(f"Error initializing APIs: {str(e)}")

# Initialize APIs on startup
init_apis()

@app.route('/')
def index():
    logger.info("Homepage accessed")
    return render_template('index.html')

@app.route('/generate-text', methods=['POST'])
def generate_text():
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            logger.warning("No prompt provided for text generation")
            return jsonify({'error': 'No prompt provided'}), 400

        logger.info(f"Generating text for prompt: {prompt[:50]}...")
        
        # Using gemini-2.0-flash model for faster responses
        model = genai.GenerativeModel('gemini-2.0-flash')
        generation_config = {
            'temperature': 0.9,
            'top_p': 1,
            'top_k': 1,
            'max_output_tokens': 2048,
        }
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        if response.text:
            logger.info("Text generated successfully")
            return jsonify({'text': response.text.strip()})
        else:
            logger.error("No text generated from Gemini API")
            return jsonify({'error': 'No text generated'}), 500
    except Exception as e:
        logger.error(f"Error in text generation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download-video', methods=['POST'])
def download_video():
    try:
        query = request.json.get('query')
        if not query:
            logger.warning("No search query provided for video download")
            return jsonify({'error': 'No search query provided'}), 400

        logger.info(f"Searching video for query: {query}")
        headers = {'Authorization': os.getenv('PEXELS_API_KEY')}
        response = requests.get(
            f'https://api.pexels.com/videos/search?query={query}&per_page=1',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['videos']:
                video_file = data['videos'][0]['video_files'][0]
                video_url = video_file['link']
                
                logger.info(f"Downloading video from: {video_url}")
                video_response = requests.get(video_url)
                if video_response.status_code == 200:
                    video_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_video.mp4')
                    with open(video_path, 'wb') as f:
                        f.write(video_response.content)
                    logger.info("Video downloaded successfully")
                    return jsonify({'path': video_path})
            
            logger.warning("No videos found in Pexels response")
            return jsonify({'error': 'No videos found'}), 404
        else:
            logger.error(f"Failed to fetch video: {response.status_code}")
            return jsonify({'error': 'Failed to fetch video'}), response.status_code
    except Exception as e:
        logger.error(f"Error in video download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate-speech', methods=['POST'])
def generate_speech():
    try:
        text = request.json.get('text')
        if not text:
            logger.warning("No text provided for speech generation")
            return jsonify({'error': 'No text provided'}), 400

        logger.info("Generating speech from text")
        audio = generate(
            text=text,
            voice="21m00Tcm4TlvDq8ikWAM",
            model="eleven_monolingual_v1"
        )
        
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_audio.mp3')
        save(audio, audio_path)
        logger.info("Speech generated successfully")
        
        return jsonify({'path': audio_path})
    except Exception as e:
        logger.error(f"Error in speech generation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/create-video', methods=['POST'])
def create_video():
    try:
        video_path = request.json.get('video_path')
        audio_path = request.json.get('audio_path')
        text_content = request.json.get('text_content')
        use_background_music = request.json.get('background_music') == 'yes'
        background_volume = float(request.json.get('background_volume', 0.3))

        if not all([video_path, audio_path, text_content]):
            logger.warning("Missing required parameters for video creation")
            return jsonify({'error': 'Missing required parameters'}), 400

        logger.info("Starting video creation process")
        
        # Load video and audio
        logger.info("Loading video and audio files")
        video = VideoFileClip(video_path)
        voiceover = AudioFileClip(audio_path)

        # Handle background music if selected
        if use_background_music and os.path.exists('static/music/background.mp3'):
            try:
                logger.info("Adding background music")
                bg_music = AudioFileClip('static/music/background.mp3')
                
                # Loop background music if needed
                if bg_music.duration < voiceover.duration:
                    loops_needed = int(voiceover.duration / bg_music.duration) + 1
                    logger.info(f"Looping background music {loops_needed} times")
                    bg_music = concatenate_audioclips([bg_music] * loops_needed)
                
                # Set duration and volume
                bg_music = bg_music.subclip(0, voiceover.duration)
                bg_music = bg_music.volumex(background_volume)
                logger.info(f"Background music volume set to {background_volume}")
                
                # Mix background music with voiceover
                final_audio = CompositeAudioClip([voiceover, bg_music])
                logger.info("Audio mixing completed")
            except Exception as e:
                logger.error(f"Error processing background music: {str(e)}")
                final_audio = voiceover
        else:
            final_audio = voiceover

        # Resize video to 720p
        logger.info("Resizing video to 720p")
        video = video.resize(height=720)
        
        # Create text clips
        logger.info("Creating text overlays")
        clips = [video]
        sentences = [s.strip() for s in text_content.split('.') if s.strip()]
        
        for i, text in enumerate(sentences):
            try:
                # Create background for text
                bg_clip = ColorClip(
                    size=(video.w, 80),
                    color=(0, 0, 0)
                ).set_opacity(0.5)
                bg_clip = bg_clip.set_position(('center', 'bottom'))
                bg_clip = bg_clip.set_start(i * 3).set_duration(3)
                
                # Create text
                txt_clip = TextClip(
                    text,
                    fontsize=30,
                    color='white',
                    size=(video.w - 40, None),
                    method='caption'
                )
                txt_clip = txt_clip.set_position(('center', 'bottom'))
                txt_clip = txt_clip.set_start(i * 3).set_duration(3)
                
                clips.extend([bg_clip, txt_clip])
                logger.info(f"Added text overlay {i+1}/{len(sentences)}")
            except Exception as e:
                logger.error(f"Error creating text clip: {str(e)}")
                continue

        try:
            # Combine all clips
            logger.info("Combining video clips")
            final_video = CompositeVideoClip(clips)
            
            # Add final audio
            logger.info("Adding audio to video")
            final_video = final_video.set_audio(final_audio)
            
            # Set duration
            final_duration = min(video.duration, voiceover.duration)
            final_video = final_video.set_duration(final_duration)
            logger.info(f"Final video duration: {final_duration} seconds")

            # Export
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'final_video.mp4')
            logger.info("Exporting final video")
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

            # Clean up
            logger.info("Cleaning up resources")
            video.close()
            voiceover.close()
            if use_background_music and 'bg_music' in locals():
                bg_music.close()
            final_video.close()

            logger.info("Video creation completed successfully")
            return jsonify({'path': output_path})
        except Exception as e:
            logger.error(f"Error in video processing: {str(e)}")
            return jsonify({'error': f'Video processing error: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Error in create_video: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        logger.info(f"Downloading file: {filename}")
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], filename),
            as_attachment=True
        )
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=8080, debug=True)
