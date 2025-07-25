import boto3
from PIL import Image
import io
import os
import re
import json
import tempfile
from pathlib import Path
from datetime import datetime
from cost_analysis import cost_tracker
from json_output import save_json_transcription, create_batch_json_file, create_json_response

"""Second Shot verification module - verifies and corrects first shot transcription results"""

AVAILABLE_MODELS = [
    "us.anthropic.claude-3-sonnet-20240229-v1:0",
    "us.anthropic.claude-opus-4-20250514-v1:0",
    "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "us.meta.llama3-2-90b-instruct-v1:0",
    "us.meta.llama4-maverick-17b-instruct-v1:0",
    "us.amazon.nova-premier-v1:0",
    "us.amazon.nova-pro-v1:0",
    "us.mistral.pixtral-large-2502-v1:0"
]

def select_model():
    print("Available models:")
    for i, model in enumerate(AVAILABLE_MODELS, 1):
        print(f"{i}. {model}")

    while True:
        try:
            selection = int(input("Select model number: "))
            if 1 <= selection <= len(AVAILABLE_MODELS):
                return AVAILABLE_MODELS[selection-1]
            print(f"Please enter a number between 1 and {len(AVAILABLE_MODELS)}")
        except ValueError:
            print("Please enter a valid number")

def standardize_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    target_size = (1120, 1120)
    
    if img.size != target_size:
        img = img.resize(target_size, Image.Resampling.LANCZOS)
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    return img_byte_arr.getvalue()

def convert_to_png(image_path):
    img = Image.open(image_path)
    png_bytes = io.BytesIO()
    img.save(png_bytes, format="PNG")
    return png_bytes.getvalue()

def _clean_response_text(response_text):
    """Clean up response text by removing common prefixes"""
    prefixes_to_remove = [
        "Here is the list of fields with the information from the herbarium label:",
        "Here are the fields extracted from the herbarium label:",
        "Here is the transcription of the herbarium label:",
        "Here's the transcription of the herbarium label:",
        "Based on the first pass transcription and the image, here is the verified and corrected transcription:",
        "After reviewing the first pass transcription and the image, here is the verified and corrected transcription:"
    ]
    
    for prefix in prefixes_to_remove:
        if response_text.startswith(prefix):
            response_text = response_text[len(prefix):].lstrip()
            break
    
    # Handle cases where response contains the prompt
    if "## 🌿 Herbarium Label Transcription" in response_text or "**Herbarium Label Transcription**" in response_text:
        print("Warning: Response contains the prompt instead of structured data. Extracting only the field list...")
        field_list_start = response_text.find("verbatimCollectors:")
        if field_list_start != -1:
            response_text = response_text[field_list_start:]
        else:
            print("Could not find field list in response. Please check the model output.")
    
    return response_text

def process_image(image_path, prompt_path, model_id):
    """Process a single image with the given prompt"""
    bedrock_runtime = boto3.client("bedrock-runtime")
    
    # Convert and standardize image
    image = convert_to_png(image_path)
    image = standardize_image(image)
    
    # Read prompt
    with open(prompt_path, "r") as f:
        user_message = f.read().strip()
    
    # Prepare message for model
    messages = [{
        "role": "user",
        "content": [
            {"image": {"format": "png", "source": {"bytes": image}}},
            {"text": user_message},
        ],
    }]
    
    # Call Bedrock
    response = bedrock_runtime.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={"temperature": 0.25}
    )
    
    response_text = response["output"]["message"]["content"][0]["text"]
    
    # Track cost
    input_tokens = cost_tracker.estimate_tokens(user_message)
    output_tokens = cost_tracker.estimate_tokens(response_text, is_output=True)
    cost_tracker.track_request(model_id, input_tokens, output_tokens)
    
    response_text = _clean_response_text(response_text)
    print(response_text)
    return response_text

def verify_first_shot(base_folder, first_shot_json_path, output_dir, run_name, model_id=None):
    """Verify and correct first shot transcription results"""
    if model_id is None:
        model_id = select_model()
    
    # Load first shot data
    with open(first_shot_json_path, 'r') as f:
        first_shot_data = json.load(f)
    
    transcriptions = first_shot_data['transcriptions']
    print(f"\nVerifying {len(transcriptions)} first shot transcriptions")
    
    all_transcriptions = []
    for i, transcription in enumerate(transcriptions, 1):
        image_name = transcription['image_name']
        first_shot_text = transcription['content'][0]['text']
        
        print(f"\n{'='*50}")
        print(f"Verifying transcription {i}/{len(transcriptions)}: {image_name}")
        
        # Find image file
        image_path = None
        for ext in ['.png', '.jpg', '.jpeg']:
            possible_paths = list(Path(base_folder).glob(f"**/*{image_name}"))
            if possible_paths:
                image_path = possible_paths[0]
                break
        
        if not image_path:
            print(f"Error: Could not find image file for {image_name}. Skipping.")
            continue
        
        try:
            # Create verification prompt
            verification_prompt = f"""You are an expert verifier reviewing a herbarium label transcription.

Please verify the following transcription against the image and correct any errors:

{first_shot_text}

Return the corrected transcription in the same format. If the transcription is accurate, return it unchanged.
If you find information that is not entered or can be applied to new fields such as first and second political unit. Please enter the information"""
            
            # Create temporary prompt file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_prompt:
                temp_prompt.write(verification_prompt)
                temp_prompt_path = temp_prompt.name
            
            try:
                response_text = process_image(image_path, temp_prompt_path, model_id)
                
                # Calculate tokens
                input_tokens = cost_tracker.estimate_tokens(verification_prompt)
                output_tokens = cost_tracker.estimate_tokens(response_text, is_output=True)
                
                # Save individual JSON
                json_filepath = save_json_transcription(
                    output_dir, run_name, "second_shot_verification", 
                    image_name, response_text, model_id, 
                    input_tokens, output_tokens
                )
                
                # Create response for batch
                json_response = create_json_response(
                    image_name, response_text, model_id, 
                    input_tokens, output_tokens
                )
                
                print(f"Verification JSON saved to: {json_filepath}")
                all_transcriptions.append(json_response)
                
            finally:
                os.unlink(temp_prompt_path)
                
        except Exception as e:
            print(f"Error verifying {image_name}: {str(e)}")
            error_response = {
                "error": str(e),
                "image_name": image_name,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            all_transcriptions.append(error_response)

    # Create batch file
    if all_transcriptions:
        batch_filepath = create_batch_json_file(output_dir, run_name, "second_shot_verification", all_transcriptions)
        print(f"\nBatch verification JSON file created: {batch_filepath}")
    
    print(f"Second Shot verification completed! JSON files saved to {output_dir}")
    return all_transcriptions

# Backward compatibility alias
def process_with_first_shot(base_folder, prompt_path, first_shot_json_path, output_dir, run_name, model_id=None):
    """Backward compatibility wrapper for verify_first_shot"""
    return verify_first_shot(base_folder, first_shot_json_path, output_dir, run_name, model_id)

if __name__ == "__main__":
    print("Taking Another Look...")