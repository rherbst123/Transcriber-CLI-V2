from art import tprint
from transcribers.FirstShot import First_Shot
from transcribers.SecondShot import Second_Shot
from helpers.cost_analysis import cost_tracker
from helpers.txt_to_csv import convert_json_to_csv
from Validation.validate_scientific_names import validate_csv_scientific_names
import os
import re
import stat
from pathlib import Path
import requests
from urllib.parse import urlparse
import shutil
from datetime import datetime
import json


#Determine how many shots to do
def select_shots():
    while True:
        choice = input("\nChoose processing mode:\n1. One shot\n2. Two shots\nEnter choice (1-2) or 'back' to go back: ")
        if choice in ['1', '2']:
            return int(choice)
        elif choice.lower() == 'back':
            return 'back'
        print("Please enter 1, 2, or 'back'")


#Local or URL download Images
def select_image_source():
    while True:
        choice = input("\nChoose image source:\n1. Local images\n2. URL download\nEnter choice (1-2) or 'back' to go back: ")
        if choice in ['1', '2']:
            return choice == '2'  # Returns True for URL, False for local
        elif choice.lower() == 'back':
            return 'back'
        print("Please enter 1, 2, or 'back'")


#Name the run instead of having a bunch of dates and shitty formatting
def get_run_name():
    while True:
        run_name = input("\nEnter a name for this run (or press Enter for default): ").strip()
        if run_name.lower() == 'back':
            return 'back'
        if not run_name:
            run_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Sanitize filename for cross-platform compatibility
        # Remove characters that are problematic on both Windows and Unix
        run_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', run_name)
        # Remove trailing dots and spaces (Windows issue)
        run_name = run_name.rstrip('. ')
        # Ensure it's not empty after sanitization
        if not run_name:
            run_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return run_name


#The most stupid workaround to make this work on all platforms 
#I hate you Bill Gates, you are on that list I know it. 
def safe_rmtree(path):
    if not os.path.exists(path):
        return
    
    try:
        shutil.rmtree(path)
    except PermissionError:
        # Windows sometimes has permission issues, try to fix them
        if os.name == 'nt':  # Windows
            import stat
            def remove_readonly(func, path, exc_info):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(path, onerror=remove_readonly)
        else:
            raise

#Pretty self explanitory
def download_images_from_urls(url_file_path, download_dir):
    """Download images from URLs in a text file and save a filename->URL map"""
    if not os.path.exists(url_file_path):
        print(f"Error: URL file not found at {url_file_path}")
        return False
    
    # Clear existing images using safe removal
    if os.path.exists(download_dir):
        safe_rmtree(download_dir)
    
    os.makedirs(download_dir, exist_ok=True)
    
    with open(url_file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"\nDownloading {len(urls)} images...")
    url_map = {}
    for i, url in enumerate(urls, 1):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Get original filename and add index prefix
            original_filename = os.path.basename(urlparse(url).path) or f"image_{i}.jpg"
            filename = f"{i:04d}_{original_filename}"
            filepath = os.path.join(download_dir, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Track mapping of saved filename to original URL
            url_map[filename] = url
            
            print(f"Downloaded {i}/{len(urls)}: {filename}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")
    
    # Save URL map for later enrichment of JSON/CSV
    try:
        map_path = os.path.join(download_dir, 'url_map.json')
        with open(map_path, 'w', encoding='utf-8') as mf:
            json.dump(url_map, mf, indent=2, ensure_ascii=False)
        print(f"Saved URL map to {map_path}")
    except Exception as e:
        print(f"Warning: Could not save URL map: {e}")
    
    return True



def select_prompt():
    prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Prompts")
    
    if os.path.exists(prompts_dir):
        prompt_files = [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
        if prompt_files:
            print("\nAvailable prompts:")
            for i, prompt in enumerate(prompt_files, 1):
                print(f"{i}. {prompt}")
            print(f"{len(prompt_files) + 1}. Custom filepath")
            
            #Implementing Back options for if you make an oopsie 
            while True:
                choice_input = input(f"\nSelect prompt (1-{len(prompt_files) + 1}) or 'back' to go back: ")
                if choice_input.lower() == 'back':
                    return 'back'
                try:
                    choice = int(choice_input)
                    if 1 <= choice <= len(prompt_files):
                        return os.path.join(prompts_dir, prompt_files[choice-1])
                    elif choice == len(prompt_files) + 1:
                        custom_path = input("Enter custom prompt filepath (or 'back' to go back): ")
                        if custom_path.lower() == 'back':
                            continue
                        return custom_path
                    print(f"Please enter a number between 1 and {len(prompt_files) + 1}")
                except ValueError:
                    print("Please enter a valid number or 'back'")
    
    while True:
        prompt_path = input("Enter prompt filepath (or 'back' to go back): ")
        if prompt_path.lower() == 'back':
            return 'back'
        return prompt_path

#WHERE THE HELL ARE THE TRANSCRITPIONS GOING????????
def get_output_base_path():
    """Get the base output path, cross-platform compatible"""
    home_dir = Path(os.path.expanduser("~"))
    
    # Try Desktop first on all systems
    desktop_path = home_dir / "Desktop"
    if desktop_path.exists():
        #Right HERE :)
        return desktop_path / "Finished Transcriptions"
    
    # Fallback to home directory if Desktop doesn't exist
    return home_dir / "Finished Transcriptions"

#Shows the number of images in the folder just as a double check for things. 
def show_images_in_folder(folder_path):
    """Display images found in the folder"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    images = [f for f in os.listdir(folder_path) if os.path.splitext(f.lower())[1] in image_extensions]
    
    if not images:
        print("No image files found in the folder.")
        return
    
    print(f"\nFound {len(images)} image(s):")
    for i, img in enumerate(sorted(images), 1):
        print(f"{i:3d}. {img}")

#Local or URL Images entering 
def get_images_folder(use_urls):
    while True:
        #User chooses URLS
        if use_urls:
            url_file = input("\nEnter path to .txt file containing image URLs (or 'back' to go back): ")
            if url_file.lower() == 'back':
                return 'back', None
            # Use cross-platform path for downloads within temp area
            downloads_dir = get_output_base_path() / "temp_downloads"
            download_dir = str(downloads_dir)
            
            if download_images_from_urls(url_file, download_dir):
                return download_dir, "downloaded_images"
            else:
                print("Failed to download images. Please try again.")
                continue
        else:
            #User chooses Local images on Machine
            folder_path = input("\nEnter path to local images folder (or 'back' to go back): ")
            if folder_path.lower() == 'back':
                return 'back', None
            if not os.path.exists(folder_path):
                print(f"Error: Folder not found at {folder_path}")
                continue
            
            # Ask if user wants to see the images in the folder
            while True:
                show_choice = input("\nDo you want to see the images in this folder? (y/n): ").lower()
                if show_choice in ['y', 'yes']:
                    show_images_in_folder(folder_path)
                    break
                elif show_choice in ['n', 'no']:
                    break
                else:
                    print("Please enter 'y' or 'n'")
            
            return folder_path, os.path.basename(folder_path)


def rename_csv_files(source_dir, run_name, shot_type):
    """Rename CSV files with run name and shot type"""
    for csv_file in source_dir.glob('*.csv'):
        new_name = f"{run_name}_{shot_type}.csv"
        new_path = source_dir / new_name
        csv_file.rename(new_path)
        print(f"Renamed {csv_file.name} to {new_name}")
        return new_path  # Return the new path for moving

def move_json_files_to_shot_folder(source_dir, raw_dir, shot_name):
    """Move all JSON files from source directory to shot-specific folder in Raw Transcriptions"""
    shot_dir = raw_dir / shot_name
    shot_dir.mkdir(parents=True, exist_ok=True)
    
    for json_file in source_dir.glob('*.json'):
        destination = shot_dir / json_file.name
        shutil.move(str(json_file), str(destination))
        #print(f"Moved {json_file.name} to {shot_name} folder")

#Wrapper for all the stuff before
def configure_transcription():
    """Handle the configuration flow with back navigation"""
    config = {}
    step = 'run_name'
    
    while True:
        if step == 'run_name':
            run_name = get_run_name()
            if run_name == 'back':
                print("Cannot go back from the first step.")
                continue
            config['run_name'] = run_name
            print(f"Run name: {run_name}")
            step = 'shots'
            
        elif step == 'shots':
            num_shots = select_shots()
            if num_shots == 'back':
                step = 'run_name'
                continue
            config['num_shots'] = num_shots
            step = 'prompt'
            
        elif step == 'prompt':
            prompt_path = select_prompt()
            if prompt_path == 'back':
                step = 'shots'
                continue
            print(f"Using: {prompt_path}")
            if not os.path.exists(prompt_path):
                print(f"Error: Prompt file not found at {prompt_path}")
                continue
            config['prompt_path'] = prompt_path
            step = 'image_source'
            
        elif step == 'image_source':
            use_urls = select_image_source()
            if use_urls == 'back':
                step = 'prompt'
                continue
            config['use_urls'] = use_urls
            step = 'images_folder'
            
        elif step == 'images_folder':
            base_folder, folder_name = get_images_folder(config['use_urls'])
            if base_folder == 'back':
                step = 'image_source'
                continue
            config['base_folder'] = base_folder
            config['folder_name'] = folder_name
            break
    
    return config

def main():
    tprint("Transcriber-CLI-V2")
    print("Created by: Riley Herbst")
    print(85*"=")
    print("Welcome to the Field Museum transcriber-cli, this is an all-purpose image transcriber.")
    print("(You can type 'back' at any step to return to the previous choice)")
    
    # Create the main output directory
    output_base = get_output_base_path()
    output_base.mkdir(parents=True, exist_ok=True)
    
    print(f"Finished transcriptions will be saved to: {output_base}")
    
    # Configure transcription 
    config = configure_transcription()
    run_name = config['run_name']
    num_shots = config['num_shots']
    prompt_path = config['prompt_path']
    base_folder = config['base_folder']
    folder_name = config['folder_name']
    
    # Create run-specific output directory
    run_output_dir = get_output_base_path() / run_name
    run_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create Raw Transcriptions folder (.json files)
    raw_transcriptions_dir = run_output_dir / "Raw Transcriptions"
    
    try:
        if num_shots == 1:
            print("\nSelect model for image processing:")
            model = First_Shot.select_model()
            
            # Use run-specific directory for output
            output_dir = run_output_dir
            First_Shot.process_images(base_folder, prompt_path, output_dir, run_name, model_id=model)
            
            # Convert JSON files to CSV
            print("\n=== Converting JSON files to CSV ===")
            convert_json_to_csv(str(output_dir))
            
            # Validate scientific names in CSV files
            print("\n=== Validating Scientific Names ===")
            for csv_file in output_dir.glob('*.csv'):
                validate_csv_scientific_names(csv_file)
            
            # Rename CSV files
            print("\n=== Renaming CSV files ===")
            rename_csv_files(output_dir, run_name, "single_shot")
            
            # Move JSON files to Raw Transcriptions folder
            print("\n=== Moving JSON files to Raw Transcriptions folder ===")
            move_json_files_to_shot_folder(output_dir, raw_transcriptions_dir, "Single Shot")
        
        else:  # Two shots
            print("\nTwo shots mode: Running first pass, then second pass using first pass results")
            
            # Create temporary processing directories

            #Change filenames
            temp_first_dir = run_output_dir / "temp_first"
            temp_second_dir = run_output_dir / "temp_second"
            temp_first_dir.mkdir(exist_ok=True)
            temp_second_dir.mkdir(exist_ok=True)
            
            # Run first shot
            print("\n=== Running First Pass ===")
            print("\nSelect model for first pass processing:")
            model1 = First_Shot.select_model()
            First_Shot.process_images(base_folder, prompt_path, temp_first_dir, run_name, model_id=model1)
            print("\n=== Converting First Pass JSON files to CSV ===")
            convert_json_to_csv(str(temp_first_dir))
            
            # Find the batch JSON file from first shot
            batch_file = list(temp_first_dir.glob(f"{run_name}_first_shot_transcriptions_batch.json"))
            if not batch_file:
                print("Error: Could not find first shot batch JSON file. Skipping second shot.")
                return
                
            batch_json_path = batch_file[0]
            print(f"\nFound first shot batch JSON: {batch_json_path}")
            
            # Run second shot with the JSON file from first shot
            print("\n=== Running Second Pass using First Pass Results ===")
            print("\nSelect model for second pass processing:")
            model2 = Second_Shot.select_model()
            
            # Process second shot using first shot results
            Second_Shot.process_with_first_shot(
                base_folder, 
                prompt_path, 
                batch_json_path, 
                temp_second_dir, 
                run_name, 
                model_id=model2
            )
            
            # Convert second shot JSON files to CSV
            print("\n=== Converting Second Pass JSON files to CSV ===")
            convert_json_to_csv(str(temp_second_dir))
            
            # Rename and move CSV files to main run directory
            print("\n=== Renaming and moving CSV files ===")
            first_csv = rename_csv_files(temp_first_dir, run_name, "first_shot")
            second_csv = rename_csv_files(temp_second_dir, run_name, "second_shot")
            
            if first_csv:
                shutil.move(str(first_csv), str(run_output_dir / first_csv.name))
            if second_csv:
                shutil.move(str(second_csv), str(run_output_dir / second_csv.name))
            
            # Validate scientific names in CSV files
            print("\n=== Validating Scientific Names ===")
            for csv_file in run_output_dir.glob('*.csv'):
                validate_csv_scientific_names(csv_file)
                
            # Move JSON files to shot-specific folders in Raw Transcriptions
            print("\n=== Moving JSON files to Raw Transcriptions folders ===")
            move_json_files_to_shot_folder(temp_first_dir, raw_transcriptions_dir, "First Shot")
            move_json_files_to_shot_folder(temp_second_dir, raw_transcriptions_dir, "Second Shot")
            
            # Clean up temporary directories
            shutil.rmtree(temp_first_dir)
            shutil.rmtree(temp_second_dir)
        
        print("\nTranscription and CSV conversion completed, Thank you!")
        
        # Generate and save cost analysis report directly to run directory
        print("\n=== Generating Cost Analysis Report ===")
        cost_tracker.save_report_to_desktop(run_name, target_dir=str(run_output_dir))
        
    except Exception as e:
        print(f"\nError during transcription process: {str(e)}")
        # Still generate cost report even if there was an error
        print("\n=== Generating Cost Analysis Report ===")
        cost_tracker.save_report_to_desktop(run_name, target_dir=str(run_output_dir))

if __name__ == "__main__":
    main()
