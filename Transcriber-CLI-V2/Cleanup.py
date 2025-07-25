import os
import re
import csv
from pathlib import Path

def remove_special_chars(input_file, output_file=None):
    """
    Remove special characters (*,#,@,&,') from a text file.
    """
    if output_file is None:
        output_file = input_file
    
    try:
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove the specified characters
        for char in ['*', '#', '@', '&', ',', "'"]:
            content = content.replace(char, '')
        
        # Write the modified content
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error processing file {input_file}: {e}")
        return False


def remove_duplicates(input_file, output_file=None):
    """
    Remove duplicate entries in transcription files.
    """
    if output_file is None:
        output_file = input_file
    
    try:
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split the content by the separator
        sections = re.split(r'={80,}\n+', content)
        processed_content = ""
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
                
            # Check if this section contains duplicated content
            # Split by double newlines to identify potential duplicate blocks
            blocks = section.strip().split('\n\n')
            
            # If there's only one block or empty section, keep it as is
            if len(blocks) <= 1:
                processed_section = section
            else:
                # Check if blocks are duplicated
                unique_blocks = []
                for block in blocks:
                    if block.strip() and block.strip() not in [b.strip() for b in unique_blocks]:
                        unique_blocks.append(block)
                
                processed_section = '\n\n'.join(unique_blocks)
            
            # Add separator except for the last section
            if i < len(sections) - 1:
                processed_content += processed_section + "\n\n" + "=" * 80 + "\n\n"
            else:
                processed_content += processed_section
        
        # Write the modified content
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        return True
    except Exception as e:
        print(f"Error removing duplicates in file {input_file}: {e}")
        return False


def batch_process_files(file_list):
    """
    Process multiple files to remove special characters and duplicates.
    
    Args:
        file_list (list): List of file paths to process
    
    Returns:
        list: List of files that were successfully processed
    """
    successful_files = []
    
    for file_path in file_list:
        if file_path.endswith('.txt'):
            success = True
            # First remove duplicates
            if not remove_duplicates(file_path):
                success = False
            # Then remove special characters
            if not remove_special_chars(file_path):
                success = False
            
            if success:
                successful_files.append(file_path)
    
    return successful_files





if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        files = sys.argv[1:]
        processed = batch_process_files(files)
        print(f"Successfully processed {len(processed)} files.")
    else:
        print("Usage: python Conversion.py file1.txt file2.txt ...")