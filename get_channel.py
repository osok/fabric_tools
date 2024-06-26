import requests
import os
import argparse

def get_channel_id(api_key, username):
    base_url = 'https://www.googleapis.com/youtube/v3'
    url = f'{base_url}/channels?part=id&forUsername={username}&key={api_key}'
    
    response = requests.get(url)
    data = response.json()
    
    if 'items' in data and len(data['items']) > 0:
        return data['items'][0]['id']
    else:
        # Fallback if 'forUsername' doesn't work, using 'search' instead
        url = f'{base_url}/search?part=snippet&type=channel&q={username}&key={api_key}'
        response = requests.get(url)
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            return data['items'][0]['snippet']['channelId']
        else:
            raise ValueError("Unable to find the channel ID")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get YouTube Channel ID.')
    parser.add_argument('--username', type=str, required=True, help='YouTube username')
    
    args = parser.parse_args()

    # Get the API key from the environment variable
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise ValueError("The environment variable YOUTUBE_API_KEY is not set")

    channel_id = get_channel_id(api_key, args.username)
    print(f'Channel ID for {args.username} is {channel_id}')

