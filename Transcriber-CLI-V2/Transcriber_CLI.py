from art import *
from transcribers.FirstShot import First_Shot
from transcribers.SecondShot import Second_Shot
from helpers.cost_analysis import cost_tracker
from helpers.txt_to_csv import convert_json_to_csv
import os
from pathlib import Path
import requests
from urllib.parse import urlparse
import shutil

def select_shots():
    while True:
        choice = input("\nChoose processing mode:\n1. One shot\n2. Two shots\nEnter choice (1-2): ")
        if choice in ['1', '2']:
            return int(choice)
        print("Please enter 1 or 2")

def select_image_source():
    while True:
        choice = input("\nChoose image source:\n1. Local images\n2. URL download\nEnter choice (1-2): ")
        if choice in ['1', '2']:
            return choice == '2'  # Returns True for URL, False for local
        print("Please enter 1 or 2")



def get_run_name():
    run_name = input("\nEnter a name for this run (or press Enter for default): ").strip()
    if not run_name:
        from datetime import datetime
        run_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Sanitize filename for cross-platform compatibility
    import re
    # Remove characters that are problematic on both Windows and Unix
    run_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', run_name)
    # Remove trailing dots and spaces (Windows issue)
    run_name = run_name.rstrip('. ')
    # Ensure it's not empty after sanitization
    if not run_name:
        from datetime import datetime
        run_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return run_name

def safe_rmtree(path):
    """Safely remove directory tree, handling Windows permission issues"""
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

def download_images_from_urls(url_file_path, download_dir):
    """Download images from URLs in a text file"""
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
            
            print(f"Downloaded {i}/{len(urls)}: {filename}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")
    
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
            
            while True:
                try:
                    choice = int(input(f"\nSelect prompt (1-{len(prompt_files) + 1}): "))
                    if 1 <= choice <= len(prompt_files):
                        return os.path.join(prompts_dir, prompt_files[choice-1])
                    elif choice == len(prompt_files) + 1:
                        return input("Enter custom prompt filepath: ")
                    print(f"Please enter a number between 1 and {len(prompt_files) + 1}")
                except ValueError:
                    print("Please enter a valid number")
    
    return input("Enter prompt filepath: ")

def get_output_base_path():
    """Get the base output path, cross-platform compatible"""
    home_dir = Path(os.path.expanduser("~"))
    
    # On Windows, prefer Desktop if it exists
    if os.name == 'nt':  # Windows
        desktop_path = home_dir / "Desktop"
        if desktop_path.exists():
            return desktop_path / "Finished Transcriptions"
    
    # On Unix systems or if Desktop doesn't exist, use a directory in home
    return home_dir / "Transcriber_Output"

def get_images_folder(use_urls):
    if use_urls:
        url_file = input("\nEnter path to .txt file containing image URLs: ")
        # Use cross-platform path for downloads
        downloads_dir = get_output_base_path() / "Downloaded_Images"
        download_dir = str(downloads_dir)
        
        if download_images_from_urls(url_file, download_dir):
            return download_dir, "downloaded_images"
        else:
            return None, None
    else:
        folder_path = input("\nEnter path to local images folder: ")
        if not os.path.exists(folder_path):
            print(f"Error: Folder not found at {folder_path}")
            return None, None
        return folder_path, os.path.basename(folder_path)

def main():
    tprint("Transcriber-CLI-V2")
    print("Created by: Riley Herbst")
    print(85*"=")
    print("Welcome to the Field Museum transcriber-cli, this is an all-purpose image transcriber.")
    
    # Create the folder structure for finished transcriptions using cross-platform path
    desktop_path = get_output_base_path()
    single_shot_folder = desktop_path / "Single shot"
    dual_shot_folder = desktop_path / "Dual shot"
    
    # Create the folders if they don't exist
    single_shot_folder.mkdir(parents=True, exist_ok=True)
    dual_shot_folder.mkdir(parents=True, exist_ok=True)
    
    print(f"Finished transcriptions will be saved to: {desktop_path}")
    
    
    # Get run name
    run_name = get_run_name()
    print(f"Run name: {run_name}")
    
    # Select number of shots
    num_shots = select_shots()
    
    # Get prompt file
    prompt_path = select_prompt()
    print(f"Using: {prompt_path}")
    if not os.path.exists(prompt_path):
        print(f"Error: Prompt file not found at {prompt_path}")
        return
    
    try:
        if num_shots == 1:
            # One shot - user chooses image source
            use_urls = select_image_source()
            base_folder, folder_name = get_images_folder(use_urls)
            if not base_folder:
                print("Exiting due to folder selection error.")
                return
            
            print("\nSelect model for image processing:")
            model = First_Shot.select_model()
            
            output_dir = Path("FirstShot_results") / run_name
            output_dir.mkdir(exist_ok=True, parents=True)
            First_Shot.process_images(base_folder, prompt_path, output_dir, run_name, model_id=model)
            
            # Convert JSON files to CSV
            print("\n=== Converting JSON files to CSV ===")
            convert_json_to_csv(str(output_dir))
        
        else:  # Two shots
            print("\nTwo shots mode: Running first pass, then second pass using first pass results")
            
            # Get images (either local or from URLs)
            use_urls = select_image_source()
            base_folder, folder_name = get_images_folder(use_urls)
            if not base_folder:
                print("Exiting due to folder selection error.")
                return
            
            # Create output directories
            output_dir1 = Path("FirstShot_results") / run_name
            output_dir1.mkdir(exist_ok=True, parents=True)
            output_dir2 = Path("SecondShot_results") / run_name
            output_dir2.mkdir(exist_ok=True, parents=True)
            
            # Create the dual shot folder using cross-platform path
            dual_shot_folder = get_output_base_path() / "Dual shot" / run_name
            dual_shot_folder.mkdir(parents=True, exist_ok=True)
            
            # Run first shot
            print("\n=== Running First Pass ===")
            print("\nSelect model for first pass processing:")
            model1 = First_Shot.select_model()
            First_Shot.process_images(base_folder, prompt_path, output_dir1, run_name, model_id=model1)
            print("\n=== Converting First Pass JSON files to CSV ===")
            convert_json_to_csv(str(output_dir1))
            
            # Find the batch JSON file from first shot
            batch_file = list(output_dir1.glob(f"{run_name}_first_shot_transcriptions_batch.json"))
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
                output_dir2, 
                run_name, 
                model_id=model2
            )
            
            # Convert second shot JSON files to CSV
            print("\n=== Converting Second Pass JSON files to CSV ===")
            convert_json_to_csv(str(output_dir2))
        
        print("\nTranscription and CSV conversion completed, Thank you!")
        
        # Generate and save cost analysis report
        print("\n=== Generating Cost Analysis Report ===")
        cost_tracker.save_report_to_desktop(run_name)
        
    except Exception as e:
        print(f"\nError during transcription process: {str(e)}")
        # Still generate cost report even if there was an error
        print("\n=== Generating Cost Analysis Report ===")
        cost_tracker.save_report_to_desktop(run_name)

if __name__ == "__main__":
    main()
