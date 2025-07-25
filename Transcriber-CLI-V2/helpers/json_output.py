import json
import os
import uuid
from datetime import datetime
from pathlib import Path

def create_json_response(image_name, transcription_text, model_id, input_tokens=0, output_tokens=0):
    """Create a JSON response in the specified format"""
    
    # Generate a unique message ID
    msg_id = f"msg_bdrk_{uuid.uuid4().hex[:24]}"
    
    # Create the JSON structure
    json_response = {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "model": model_id,
        "content": [
            {
                "type": "text",
                "text": transcription_text
            }
        ],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "output_tokens": output_tokens
        },
        "image_name": image_name,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    return json_response

def save_json_transcription(output_dir, date_folder, shot_type, image_name, transcription_text, model_id, input_tokens=0, output_tokens=0):
    """Save individual JSON transcription file"""
    
    # Create JSON response
    json_response = create_json_response(image_name, transcription_text, model_id, input_tokens, output_tokens)
    
    # Create individual JSON file for this transcription
    json_filename = f"{Path(image_name).stem}_transcription.json"
    json_filepath = output_dir / json_filename
    
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(json_response, f, indent=2, ensure_ascii=False)
    
    return json_filepath

def create_batch_json_file(output_dir, date_folder, shot_type, all_transcriptions):
    """Create a single JSON file containing all transcriptions"""
    
    batch_filename = f"{date_folder}_{shot_type}_transcriptions_batch.json"
    batch_filepath = output_dir / batch_filename
    
    batch_data = {
        "batch_id": f"batch_{uuid.uuid4().hex[:16]}",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "shot_type": shot_type,
        "date_folder": date_folder,
        "total_transcriptions": len(all_transcriptions),
        "transcriptions": all_transcriptions
    }
    
    with open(batch_filepath, 'w', encoding='utf-8') as f:
        json.dump(batch_data, f, indent=2, ensure_ascii=False)
    
    return batch_filepath