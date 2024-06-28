# fabric_tools


```process_channel.py```

Given either a user id or channel id for a you tube user, this script downloads the transcript for all the videos and runs then through
fabric to ```extract+wisdom```.  That wisdom is saved as a markdown file, which is later pushed to another of my github repos ```https://github.com/osok/arXiv_papers```.  
Then an embedding is create using a local LM Studio instance with ```nomic-ai/nomic-embed-text-v1.5-GGUF``` of the entire markdown file.
details of the video including the summary are stored in the metadata.   This can then be searched and display using the tool in ```https://github.com/osok/arXiv_flask```

You will need API Keyys for 
- PineCone
- YouTube

```
usage: process_channel.py [-h] [--channel_id CHANNEL_ID] [--user_id USER_ID] --out_dir OUT_DIR --index_name INDEX_NAME [--count COUNT]

Process YouTube videos.

options:
  -h, --help            show this help message and exit
  --channel_id CHANNEL_ID
                        YouTube channel ID
  --user_id USER_ID     YouTube user ID
  --out_dir OUT_DIR     Output directory
  --index_name INDEX_NAME
                        Pinecone index name
  --count COUNT         Number of videos to process
```
