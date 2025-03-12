import os
from dotenv import load_dotenv
from src.text_generator import generate_text
from src.video_downloader import download_stock_footage
from src.speech_generator import generate_speech
from src.video_editor import create_final_video

# Load environment variables
load_dotenv()

def main():
    try:
        print("🎬 Starting video creation process...")
        
        # 1. Generate text content using Gemini
        print("📝 Generating text content...")
        text_content = generate_text("Create an inspiring 30-second message about nature")
        
        # 2. Download relevant stock footage
        print("🎥 Downloading stock footage...")
        video_path = download_stock_footage("nature beautiful landscape")
        
        # 3. Generate speech from text
        print("🗣️ Generating speech...")
        audio_path = generate_speech(text_content)
        
        # 4. Combine everything into final video
        print("🎨 Creating final video...")
        output_path = create_final_video(video_path, audio_path, text_content)
        
        print(f"✨ Video created successfully! Output saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    main()
