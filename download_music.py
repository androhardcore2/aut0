import os
import requests

# Create music directory if it doesn't exist
os.makedirs('static/music', exist_ok=True)

# Sample royalty-free music URLs (these are placeholder URLs - replace with actual royalty-free music URLs)
MUSIC_URLS = {
    'upbeat': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
    'relaxing': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
    'dramatic': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
    'corporate': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3'
}

def download_music():
    for style, url in MUSIC_URLS.items():
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(f'static/music/{style}.mp3', 'wb') as f:
                    f.write(response.content)
                print(f'Downloaded {style} music')
            else:
                print(f'Failed to download {style} music')
        except Exception as e:
            print(f'Error downloading {style} music: {str(e)}')

if __name__ == '__main__':
    download_music()
