"""
File conversion file formats to Markdown
"""
import csv
import json
import io
from datetime import datetime


def is_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read first 1024 bytes as text
            f.read(1024)
        return True
    except (UnicodeDecodeError, UnicodeError):
        return False


def convert_txt_to_note(content):
    return content


def convert_csv_to_note(content):
    csv_reader = csv.reader(io.StringIO(content))
    rows = list(csv_reader)
    
    if not rows:
        return "Empty CSV file"
    
    max_cols = max(len(row) for row in rows)
    markdown = ''
    
    header_row = rows[0]
    markdown += '| '
    for i in range(max_cols):
        cell = header_row[i] if i < len(header_row) else ''
        markdown += escape_markdown(cell) + ' | '
    markdown += '\n'
    
    markdown += '| '
    for i in range(max_cols):
        markdown += '--- | '
    markdown += '\n'
    
    for row in rows[1:]:
        markdown += '| '
        for i in range(max_cols):
            cell = row[i] if i < len(row) else ''
            markdown += escape_markdown(cell) + ' | '
        markdown += '\n'
    
    return markdown


def convert_json_to_note(content):
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {str(e)}"
    
    # Check list with multiple items
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict):
            all_keys = set()
            for item in data:
                if isinstance(item, dict):
                    all_keys.update(item.keys())
            all_keys = sorted(all_keys)
            
            markdown = ''
            
            markdown += '| '
            for key in all_keys:
                markdown += escape_markdown(str(key)) + ' | '
            markdown += '\n'
            
            markdown += '| '
            for key in all_keys:
                markdown += '--- | '
            markdown += '\n'
            
            for item in data:
                markdown += '| '
                if isinstance(item, dict):
                    for key in all_keys:
                        value = item.get(key, '')
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value, indent=2)
                        markdown += escape_markdown(str(value)) + ' | '
                else:
                    markdown += escape_markdown(str(item)) + ' | '
                    for i in range(len(all_keys) - 1):
                        markdown += ' | '
                markdown += '\n'
            
            return markdown
    # Fallback
    return f'```json\n{json.dumps(data, indent=2)}\n```'


def escape_markdown(text):
    if text is None:
        return ''
    text = str(text)
    text = text.replace('|', '\|')
    text = text.replace('\n', ' ')
    text = text.replace('\r', '')
    return text


def convert_file_to_note_content(file_path, file_extension, filename=None):
    if not is_text_file(file_path):
        return False, "File is not a text file"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading file: {str(e)}"
    
    try:
        ext = file_extension.lower().lstrip('.')
        
        if ext == 'txt':
            converted_content = convert_txt_to_note(content)
        elif ext == 'csv':
            converted_content = convert_csv_to_note(content)
        elif ext == 'json':
            converted_content = convert_json_to_note(content)
        else:
            return False, f"Unsupported file extension: {file_extension}"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"""### Note imported from a file

File: **{filename or 'Unknown'}**
Date: {timestamp}

### Converted file

"""
        final_content = header + converted_content
        
        return True, final_content
    except Exception as e:
        return False, f"Error converting file: {str(e)}"
