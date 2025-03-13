# Smart Video Creator Pro

An advanced web application that leverages AI to automatically create professional videos by combining AI-generated content, stock footage, and text-to-speech synthesis.

## Features

- 🎯 AI-powered content generation using Gemini AI
- 🎥 Professional stock footage integration via Pexels API
- 🗣️ Natural text-to-speech conversion with ElevenLabs
- 🎵 Background music library with volume control
- 📱 Support for both landscape (16:9) and portrait (9:16) formats
- ✨ Modern, user-friendly interface with step-by-step guidance

## Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher (for development)
- ImageMagick (for video processing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/smart-video-creator-pro.git
cd smart-video-creator-pro
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install ImageMagick:
- On Ubuntu/Debian:
  ```bash
  sudo apt-get install imagemagick
  ```
- On macOS:
  ```bash
  brew install imagemagick
  ```
- On Windows:
  Download and install from [ImageMagick Website](https://imagemagick.org/script/download.php)

5. Set up environment variables:
```bash
cp .env.example .env
```
Edit `.env` and add your API keys:
```
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
PEXELS_API_KEY=your_pexels_api_key
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:8080
```

3. Follow the step-by-step process:
   - Generate content using AI or templates
   - Select video footage
   - Generate voice narration
   - Add background music
   - Create final video

## API Keys Setup

### Gemini AI
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `.env` as `GEMINI_API_KEY`

### ElevenLabs
1. Sign up at [ElevenLabs](https://elevenlabs.io)
2. Get your API key from the profile settings
3. Add to `.env` as `ELEVENLABS_API_KEY`

### Pexels
1. Create account at [Pexels](https://www.pexels.com/api/)
2. Get your API key
3. Add to `.env` as `PEXELS_API_KEY`

## Project Structure

```
auto_create_video/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── .env.example       # Environment variables example
├── static/
│   ├── css/
│   │   └── style.css  # Custom styles
│   ├── js/
│   │   └── main.js    # Frontend JavaScript
│   └── music/         # Background music files
└── templates/
    └── index.html     # Main application template
```

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
export FLASK_APP=app.py
flask run --port 8080
```

### Code Style

The project follows PEP 8 style guide. Format code using:
```bash
black .
flake8
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Gemini AI](https://deepmind.google/technologies/gemini/) for text generation
- [ElevenLabs](https://elevenlabs.io) for text-to-speech
- [Pexels](https://www.pexels.com) for stock footage
- [Flask](https://flask.palletsprojects.com/) web framework
- [MoviePy](https://zulko.github.io/moviepy/) for video processing
