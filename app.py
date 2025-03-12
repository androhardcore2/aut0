from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
import google.generativeai as genai
from elevenlabs import generate, save, set_api_key
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ColorClip
import tempfile

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure output directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize APIs
def init_apis():
    # Gemini API
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
    
    # ElevenLabs API
    elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
    if elevenlabs_api_key:
        set_api_key(elevenlabs_api_key)

# Initialize APIs on startup
init_apis()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-text', methods=['POST'])
def generate_text():
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

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
            return jsonify({'text': response.text.strip()})
        else:
            return jsonify({'error': 'No text generated'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-video', methods=['POST'])
def download_video():
    try:
        query = request.json.get('query')
        if not query:
            return jsonify({'error': 'No search query provided'}), 400

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
                
                video_response = requests.get(video_url)
                if video_response.status_code == 200:
                    video_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_video.mp4')
                    with open(video_path, 'wb') as f:
                        f.write(video_response.content)
                    return jsonify({'path': video_path})
            
            return jsonify({'error': 'No videos found'}), 404
        else:
            return jsonify({'error': 'Failed to fetch video'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate-speech', methods=['POST'])
def generate_speech():
    try:
        text = request.json.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        audio = generate(
            text=text,
            voice="21m00Tcm4TlvDq8ikWAM",
            model="eleven_monolingual_v1"
        )
        
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_audio.mp3')
        save(audio, audio_path)
        
        return jsonify({'path': audio_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create-video', methods=['POST'])
def create_video():
    try:
        video_path = request.json.get('video_path')
        audio_path = request.json.get('audio_path')
        text_content = request.json.get('text_content')

        if not all([video_path, audio_path, text_content]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Load video and audio
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)

        # Resize video to 720p
        video = video.resize(height=720)
        
        # Create text clips
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
            except Exception as e:
                print(f"Error creating text clip: {str(e)}")
                continue

        try:
            # Combine all clips
            final_video = CompositeVideoClip(clips)
            
            # Add audio
            final_video = final_video.set_audio(audio)
            
            # Set duration
            final_duration = min(video.duration, audio.duration)
            final_video = final_video.set_duration(final_duration)

            # Export
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

            # Clean up
            video.close()
            audio.close()
            final_video.close()

            return jsonify({'path': output_path})
        except Exception as e:
            print(f"Error in video processing: {str(e)}")
            return jsonify({'error': f'Video processing error: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Error in create_video: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], filename),
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
