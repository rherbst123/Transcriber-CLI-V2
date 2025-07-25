import csv
import re
import os
import json
from pathlib import Path

def parse_json_files(json_folder):
    """Parse all JSON files in a folder and extract transcription data"""
    json_folder = Path(json_folder)
    data = []
    
    # Get all JSON files (excluding batch files)
    json_files = [f for f in json_folder.glob("*.json") if not f.name.endswith("_batch.json")]
    
    if not json_files:
        print(f"No individual JSON files found in {json_folder}")
        return data
    
    print(f"Found {len(json_files)} JSON files to process")
    
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Extract image name
            image_name = json_data.get('image_name', json_file.stem)
            
            # Extract transcription text from content
            transcription_text = ""
            if 'content' in json_data and json_data['content']:
                for content_item in json_data['content']:
                    if content_item.get('type') == 'text':
                        transcription_text = content_item.get('text', '')
                        break
            
            if not transcription_text:
                print(f"No transcription text found in {json_file.name}")
                continue
            
            # Parse the transcription text to extract fields
            records = parse_transcription_text(transcription_text, image_name)
            data.extend(records)
            
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
            continue
    
    return data

def parse_transcription_text(transcription_text, image_name):
    """Parse transcription text to extract structured data"""
    lines = transcription_text.splitlines()
    data = []
    
    # Split into multiple records if there are duplicate field names
    current_record = {"Image": image_name}
    field_counts = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if ":" in line and not line.startswith(("Looking at", "```", "#", "*")):
            # Handle JSON-like content within the text
            if line.strip().startswith('"') and line.strip().endswith('"'):
                continue
                
            key, value = line.split(":", 1)
            key = key.strip().strip('"').strip()
            value = value.strip().strip(',').strip('"').strip()
            
            # Skip empty values or common non-field content
            if not value or value.lower() in ['n/a', 'na', '']:
                value = "N/A"
            
            # If we see a field we've already seen, start a new record
            if key in field_counts and key != "Image":
                if current_record and len(current_record) > 1:  # More than just Image field
                    data.append(current_record)
                current_record = {"Image": image_name}
                field_counts = {}
            
            current_record[key] = value
            field_counts[key] = 1
    
    if current_record and len(current_record) > 1:  # More than just Image field
        data.append(current_record)
    
    return data

def get_fieldnames_in_order(data):
    fieldnames = []
    for record in data:
        for key in record.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames

def write_to_csv(data, output_filename):
    fieldnames = get_fieldnames_in_order(data)
    
    with open(output_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for record in data:
            writer.writerow(record)

def convert_json_to_csv(json_folder_path):
    """Convert JSON transcription files to CSV format"""
    print(f"Converting JSON files from folder: {json_folder_path}")
    
    if not os.path.exists(json_folder_path):
        print(f"Error: JSON folder not found at {json_folder_path}")
        return None
    
    # Create CSV filename based on folder name
    folder_name = Path(json_folder_path).name
    
    # Create the original CSV path (for backward compatibility)
    original_csv_path = Path(json_folder_path) / f"{folder_name}_transcriptions.csv"
    
    # Create the new folder structure on desktop
    desktop_path = Path(os.path.expanduser("~")) / "Desktop" / "Finished Transcriptions"
    
    # Determine if this is a first shot or second shot based on the folder path
    is_first_shot = "FirstShot_results" in str(json_folder_path)
    is_second_shot = "SecondShot_results" in str(json_folder_path)
    
    # Get the run name from the folder path
    run_name = Path(json_folder_path).name
    
    if is_first_shot and is_second_shot:
        # This shouldn't happen, but just in case
        export_folder = desktop_path / "Single shot"
        file_prefix = ""
    elif is_first_shot:
        # Check if there's a corresponding second shot folder with the same run name
        second_shot_path = Path(str(json_folder_path).replace("FirstShot_results", "SecondShot_results"))
        if second_shot_path.exists():
            # This is part of a dual shot run
            export_folder = desktop_path / "Dual shot" / run_name
            file_prefix = "first_shot_"
        else:
            # This is a single shot run
            export_folder = desktop_path / "Single shot"
            file_prefix = ""
    elif is_second_shot:
        # This is definitely part of a dual shot run
        export_folder = desktop_path / "Dual shot" / run_name
        file_prefix = "second_shot_"
    else:
        # Default to single shot if can't determine
        export_folder = desktop_path / "Single shot"
        file_prefix = ""
    
    # Create the export folder if it doesn't exist
    export_folder.mkdir(parents=True, exist_ok=True)
    
    # Set the new CSV file path with appropriate prefix
    export_csv_path = export_folder / f"{file_prefix}{folder_name}_transcriptions.csv"
    print(f"Output CSV file: {export_csv_path}")
    
    try:
        # Parse the JSON files
        data = parse_json_files(json_folder_path)
        print(f"Parsed {len(data)} records from JSON files")
        
        if not data:
            print("No data found to convert")
            return None
        
        # Write to CSV in both locations
        write_to_csv(data, original_csv_path)  # Original location for backward compatibility
        write_to_csv(data, export_csv_path)    # New location in the organized folder structure
        
        print(f"CSV conversion complete: {export_csv_path}")
        return export_csv_path
    except Exception as e:
        print(f"Error converting to CSV: {e}")
        import traceback
        traceback.print_exc()
        return None

def convert_txt_to_csv(txt_file_path):
    """Legacy function - now redirects to JSON conversion if folder is provided"""
    # Check if this is actually a folder path (for JSON files)
    if os.path.isdir(txt_file_path):
        return convert_json_to_csv(txt_file_path)
    
    print(f"TXT to CSV conversion is deprecated. Please use JSON folder conversion.")
    return None