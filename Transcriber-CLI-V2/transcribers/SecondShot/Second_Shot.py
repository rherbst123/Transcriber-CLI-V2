import boto3
from PIL import Image
import io
import os
import re
import json
import tempfile
from pathlib import Path
from datetime import datetime
from helpers.cost_analysis import cost_tracker
from helpers.json_output import save_json_transcription, create_batch_json_file, create_json_response

"""Second Shot verification module - verifies and corrects first shot transcription results"""

AVAILABLE_MODELS = [
    "us.anthropic.claude-3-sonnet-20240229-v1:0",
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
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
    #Bad way of doing this but this is how it goes sometimes
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
    with open(prompt_path, "r", encoding="utf-8") as f:
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
        #I like to think creatively
        inferenceConfig={"temperature": 0.15}
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
    with open(first_shot_json_path, 'r', encoding='utf-8') as f:
        first_shot_data = json.load(f)
    
    transcriptions = first_shot_data['transcriptions']
    print(f"\nVerifying {len(transcriptions)} first shot transcriptions")
    
    all_transcriptions = []
    for i, transcription in enumerate(transcriptions, 1):
        image_name = transcription['image_name']
        image_url = transcription.get('image_url')  # carry over if present
        
        # Check if this transcription has an error
        if 'error' in transcription:
            print(f"\n{'='*50}")
            print(f"Skipping transcription {i}/{len(transcriptions)}: {image_name}")
            print(f"First shot error: {transcription['error']}")
            
            # Add error to second shot results
            error_response = {
                "error": f"First shot failed: {transcription['error']}",
                "image_name": image_name,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            all_transcriptions.append(error_response)
            continue
        
        # Extract successful transcription text
        if 'content' not in transcription or not transcription['content']:
            print(f"\n{'='*50}")
            print(f"Skipping transcription {i}/{len(transcriptions)}: {image_name}")
            print("No content found in first shot transcription")
            
            error_response = {
                "error": "No content found in first shot transcription",
                "image_name": image_name,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            all_transcriptions.append(error_response)
            continue
            
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
            # Ensure first_shot_text is properly encoded and sanitized
            if isinstance(first_shot_text, bytes):
                first_shot_text = first_shot_text.decode('utf-8', errors='replace')
            
            # Sanitize the text to remove any problematic characters
            import unicodedata
            first_shot_text = unicodedata.normalize('NFKD', first_shot_text)
            
            # Replace any remaining problematic characters
            first_shot_text = first_shot_text.encode('utf-8', errors='replace').decode('utf-8')
            
            # Create verification prompt
            verification_prompt = f"""You are an expert Botanist and Geography with a P.H.D level understanding verifier reviewing a herbarium label transcription.

Please verify the following transcription against the image and correct any errors:

{first_shot_text}

Return the corrected transcription in the same format. If the transcription is accurate, return it unchanged.
If you find information that is not entered or can be applied to new fields such as first and second political unit and Municipality. 
If you find that one of the fields for location is in an incorrect field please move it to the correct field. 
If There is a lower level location such as municipality, but no country. Please work your way up and insert all higher level locations.
Correct any mispelled locations of all ranges. Use georefrenced knowledge.
The Locality field contains a lot of clues as to detailed locations
Please enter the information
Do not Create any new Fields, The fields set are as standard and dont need to be expanded upon
Do not say anything else, please just return the corrected transcription"""
            
            # Create temporary prompt file with explicit UTF-8 encoding
            temp_prompt_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_prompt:
                    temp_prompt.write(verification_prompt)
                    temp_prompt_path = temp_prompt.name
                
                response_text = process_image(image_path, temp_prompt_path, model_id)
                
                # Calculate tokens
                input_tokens = cost_tracker.estimate_tokens(verification_prompt)
                output_tokens = cost_tracker.estimate_tokens(response_text, is_output=True)
                
                # Save individual JSON, keep original image_url if any
                json_filepath = save_json_transcription(
                    output_dir, run_name, "second_shot_verification", 
                    image_name, response_text, model_id, 
                    input_tokens, output_tokens, image_url=image_url
                )
                
                # Create response for batch, include image_url
                json_response = create_json_response(
                    image_name, response_text, model_id, 
                    input_tokens, output_tokens, image_url=image_url
                )
                
                print(f"Verification JSON saved to: {json_filepath}")
                all_transcriptions.append(json_response)
                
            finally:
                # Clean up temporary file
                if temp_prompt_path and os.path.exists(temp_prompt_path):
                    try:
                        os.unlink(temp_prompt_path)
                    except (OSError, PermissionError) as cleanup_error:
                        print(f"Warning: Could not delete temporary file {temp_prompt_path}: {cleanup_error}")
                
        except UnicodeDecodeError as e:
            print(f"Unicode decode error verifying {image_name}: {str(e)}")
            print(f"Error details: {e.encoding} codec can't decode byte {hex(e.object[e.start])} at position {e.start}")
            error_response = {
                "error": f"Unicode decode error: {str(e)}",
                "image_name": image_name,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            all_transcriptions.append(error_response)
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
    """Backward compatibility wrapper for verify_first_shot
    
    Args:
        base_folder: Path to the base folder containing images
        prompt_path: Path to the prompt file (not used in verification, but kept for compatibility)
        first_shot_json_path: Path to the first shot batch JSON file
        output_dir: Output directory for second shot results
        run_name: Name of the run
        model_id: Model ID to use for verification
    """
    return verify_first_shot(base_folder, first_shot_json_path, output_dir, run_name, model_id)

if __name__ == "__main__":
    print("Taking Another Look...")