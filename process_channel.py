import requests
import subprocess
import os
import argparse
import re
import numpy as np
from openai import OpenAI, OpenAIError
from pinecone import Pinecone, ServerlessSpec
import time

# Retrieve API keys from environment variables
pinecone_api_key = os.getenv('PINECONE_API_KEY')

# Initialize LM Studio client
client = OpenAI(base_url="http://localhost:5000/v1", api_key="lm-studio")

# Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)

def clean_title(title):
    return re.sub(r'[^A-Za-z0-9]+', '_', title)  # Replace any non-alphanumeric character with '_'

def get_embedding(text, model="nomic-ai/nomic-embed-text-v1.5-GGUF"):
    try:
        text = text.replace("\n", " ")
        response = client.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except OpenAIError as e:
        print(f"Error getting embedding: {e}")
        return None

def add_to_vector_db(metadata, content):
    # Split content into smaller chunks and get embeddings
    embeddings = [get_embedding(chunk) for chunk in split_text(content) if get_embedding(chunk) is not None]
    if not embeddings:
        print("No valid embeddings found.")
        return
    
    # Average the embeddings
    avg_embedding = np.mean(embeddings, axis=0).tolist()
    
    # Store the embedding in the vector database with metadata
    index.upsert([(metadata['file_name'], avg_embedding, metadata)])

def split_text(text, max_chunk_size=2048):
    words = text.split()
    for i in range(0, len(words), max_chunk_size):
        yield ' '.join(words[i:i + max_chunk_size])

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

def load_processed_urls(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return set(line.strip().split(',')[0] for line in file)
    return set()

def save_processed_url(file_path, short_url, title):
    with open(file_path, 'a') as file:
        file.write(f"{short_url},{title}\n")

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

def extract_summary(output_file):
    with open(output_file, 'r') as file:
        lines = file.readlines()
    
    summary_line = None
    for i, line in enumerate(lines):
        if line.strip() == "# SUMMARY":
            summary_line = lines[i + 1].strip() if i + 1 < len(lines) else "No summary found."
            break
    return summary_line

def main(api_key, channel_id, user_id, output_path, index_name, video_limit):
    # Resolve channel ID if user ID is provided
    if user_id:
        try:
            channel_id = get_channel_id(api_key, user_id)
            print(f"Resolved user ID '{user_id}' to channel ID: {channel_id}")
        except ValueError as e:
            print(e)
            return
    
    if not channel_id:
        raise ValueError("Either --channel_id or --user_id must be provided.")
    
    # Sanitize index_name to conform to Pinecone requirements
    index_name = index_name.replace('_', '-')
    processed_file_path = f"{index_name}-processed.txt"
    
    # Load processed URLs
    processed_urls = load_processed_urls(processed_file_path)

    # Initialize Pinecone index
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=768,  # Updated dimension to match the embedding model
            metric='euclidean',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
    global index
    index = pc.Index(index_name)

    processed_count = 0
    next_page_token = ''
    
    output_path = os.path.join(output_path, index_name)
    os.makedirs(output_path, exist_ok=True)

    while processed_count < video_limit:
        url = f'https://www.googleapis.com/youtube/v3/search?key={api_key}&channelId={channel_id}&part=snippet,id&order=viewCount&maxResults=50&pageToken={next_page_token}'
        print(f"Requesting URL: {url}")
        response = requests.get(url)
        
        if response.status_code == 403:
            error_message = response.json().get('error', {}).get('message', 'Quota exceeded or access denied')
            print(f"Error: {error_message}")
            return True  # Return True to indicate a rate limit error

        data = response.json()
        
        # Print the raw response data for debugging
        print(f"Response Data: {data}")
        
        if 'items' not in data:
            print("No items found in the response.")
            break
        
        for item in data.get('items', []):
            if item['id']['kind'] == 'youtube#video':
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                short_url = f'https://youtu.be/{video_id}'

                if short_url in processed_urls:
                    print(f"Skipping already processed URL: {short_url}")
                    continue
                
                video_date = item['snippet']['publishedAt']
                
                video_details_url = f'https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={api_key}'
                video_details_response = requests.get(video_details_url)
                video_details = video_details_response.json()
                
                if 'items' not in video_details:
                    print("No video details found.")
                    continue
                
                stats = video_details['items'][0]['statistics']
                views = stats.get('viewCount', 'N/A')
                likes = stats.get('likeCount', 'N/A')
                dislikes = stats.get('dislikeCount', 'N/A')
                
                # Run the command to extract wisdom and save the markdown file
                if run_command(video_id, title, output_path):
                    output_file = os.path.join(output_path, f'{clean_title(title)}.md')
                    with open(output_file, 'r') as file:
                        content = file.read()
                    
                    summary = extract_summary(output_file)
                    
                    metadata = {
                        "title": title,
                        "short_url": short_url,
                        "file_name": video_id,  # Using video ID as file name since we're not saving files
                        "video_date": video_date,
                        "views": views,
                        "likes": likes,
                        "dislikes": dislikes,
                        "summary": summary
                    }
                    
                    add_to_vector_db(metadata, content)
                    save_processed_url(processed_file_path, short_url, title)
                    processed_urls.add(short_url)
                    processed_count += 1
                
                if processed_count >= video_limit:
                    break
        
        if 'nextPageToken' in data and processed_count < video_limit:
            next_page_token = data['nextPageToken']
        else:
            break

    print(f"Processed {processed_count} videos.")
    return False  # Return False to indicate no rate limit error

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process YouTube videos.')
    parser.add_argument('--channel_id', type=str, help='YouTube channel ID')
    parser.add_argument('--user_id', type=str, help='YouTube user ID')
    parser.add_argument('--out_dir', type=str, required=True, help='Output directory')
    parser.add_argument('--index_name', type=str, required=True, help='Pinecone index name')
    parser.add_argument('--count', type=int, default=2, help='Number of videos to process')

    args = parser.parse_args()

    if not args.channel_id and not args.user_id:
        raise ValueError("Either --channel_id or --user_id must be provided.")

    # Get the API key from the environment variable
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise ValueError("The environment variable YOUTUBE_API_KEY is not set")

    rate_limit_reached = False
    
    while not rate_limit_reached:
        try:
            rate_limit_reached = main(api_key, args.channel_id, args.user_id, args.out_dir, args.index_name, args.count)
            if rate_limit_reached:
                print("API rate limit reached. Stopping the application.")
                break
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Restarting the application in 10 seconds...")
            time.sleep(10)

