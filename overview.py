import os
import time
import signal
import re

def process_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    title = os.path.basename(file_path).replace('.md', '')
    one_sentence_takeaway = ''
    summary = ''
    ideas = ''

    # Search for the sections
    takeaway_match = re.search(r'# ONE-SENTENCE TAKEAWAY\s*([\s\S]+?)(?=\n#|$)', content)
    summary_match = re.search(r'# SUMMARY\s*([\s\S]+?)(?=\n#|$)', content)
    ideas_match = re.search(r'# IDEAS\s*([\s\S]+?)(?=\n#|$)', content)

    if takeaway_match:
        one_sentence_takeaway = takeaway_match.group(1).strip()
    if summary_match:
        summary = summary_match.group(1).strip()
    if ideas_match:
        ideas = ideas_match.group(1).strip()

    return title, one_sentence_takeaway, summary, ideas

def update_overview(overview_path, title, one_sentence_takeaway, summary, ideas):
    with open(overview_path, 'a') as overview_file:
        overview_file.write(f'# {title}\n')
        overview_file.write(f'- Summary:\n    - {summary}\n')
        overview_file.write(f'- One line takeaway:\n    - {one_sentence_takeaway}\n')
        overview_file.write(f'- Ideas:\n')
        for idea in ideas.split('\n'):
            overview_file.write(f'    - {idea}\n')
        overview_file.write('\n')

def update_processed(processed_path, filename):
    with open(processed_path, 'a') as processed_file:
        processed_file.write(f'{filename}\n')

def load_processed_files(processed_path):
    if os.path.exists(processed_path):
        with open(processed_path, 'r') as file:
            return set(file.read().splitlines())
    return set()

def main(directory):
    overview_path = os.path.join(directory, 'Overview.md')
    processed_path = os.path.join(directory, 'processed.txt')

    processed_files = load_processed_files(processed_path)

    def signal_handler(sig, frame):
        print('Exiting...')
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        for filename in os.listdir(directory):
            if filename in processed_files or filename in ['Overview.md', 'processed.txt']:
                continue
            
            if filename.endswith('.md'):
                file_path = os.path.join(directory, filename)
                title, one_sentence_takeaway, summary, ideas = process_file(file_path)
                update_overview(overview_path, title, one_sentence_takeaway, summary, ideas)
                update_processed(processed_path, filename)
                processed_files.add(filename)
                print(f'Processed {filename}')
        
        time.sleep(1)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Process Markdown files and update Overview.md.')
    parser.add_argument('--directory', type=str, required=True, help='Directory to monitor for new Markdown files.')

    args = parser.parse_args()
    main(args.directory)

