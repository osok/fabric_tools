import requests
import subprocess
import os
import argparse
import re

def get_video_details(api_key, channel_id, limit=2):
    base_url = 'https://www.googleapis.com/youtube/v3'
    url = f'{base_url}/search?key={api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults=50'
    
    videos = []
    
    while True:
        response = requests.get(url)
        data = response.json()
        
        for item in data.get('items', []):
            if item['id']['kind'] == 'youtube#video':
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                videos.append((video_id, title))
                if len(videos) >= limit:
                    return videos
        
        if 'nextPageToken' in data:
            url = f'{base_url}/search?key={api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults=50&pageToken={data["nextPageToken"]}'
        else:
            break
    
    return videos

def clean_title(title):
    return re.sub(r'[^A-Za-z0-9]+', '_', title)  # Replace any non-alphanumeric character with '_'

def run_command(video_id, title, output_path):
    url = f'https://youtu.be/{video_id}'
    safe_title = clean_title(title)  # Clean the title
    output_file = os.path.join(output_path, f'{safe_title}.md')  # Set the file extension to .md
    
    # Check if the file already exists
    if os.path.exists(output_file):
        print(f"File '{output_file}' already exists. Skipping.")
        return False
    else:
        command = f'yt --transcript {url} | fabric -sp extract_wisdom -o {output_file}'
        subprocess.run(command, shell=True)
        return True

def main(api_key, channel_id, output_path, video_limit):
    processed_count = 0
    next_page_token = ''
    
    while processed_count < video_limit:
        url = f'https://www.googleapis.com/youtube/v3/search?key={api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults=50&pageToken={next_page_token}'
        response = requests.get(url)
        data = response.json()
        
        for item in data.get('items', []):
            if item['id']['kind'] == 'youtube#video':
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                
                if run_command(video_id, title, output_path):
                    processed_count += 1
                
                if processed_count >= video_limit:
                    break
        
        if 'nextPageToken' in data and processed_count < video_limit:
            next_page_token = data['nextPageToken']
        else:
            break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process YouTube videos.')
    parser.add_argument('--channel', type=str, required=True, help='YouTube channel ID')
    parser.add_argument('--out_dir', type=str, required=True, help='Output directory')
    parser.add_argument('--count', type=int, default=2, help='Number of videos to process')

    args = parser.parse_args()

    # Get the API key from the environment variable
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise ValueError("The environment variable YOUTUBE_API_KEY is not set")

    main(api_key, args.channel, args.out_dir, args.count)

