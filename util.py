import re

def extract_timestamp(file_path):
    match = re.search(r'_(\d{10})', file_path)
    return int(match.group(1)) if match else 0  # Use 0 if no timestamp found