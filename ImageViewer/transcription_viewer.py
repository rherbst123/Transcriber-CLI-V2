import streamlit as st
import json
import os
import csv
from pathlib import Path
from PIL import Image

#Created in a pinch by Claude 4.5 Sonnet. Not bad for a concept

# Set page config
st.set_page_config(
    page_title="Transcription Viewer & Editor",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Base paths - look for Finished Transcriptions on Desktop
DESKTOP_PATH = Path.home() / "Desktop"
FINISHED_TRANSCRIPTIONS_DIR = DESKTOP_PATH / "Finished Transcriptions"

def get_available_folders():
    """Get all available folders in Finished Transcriptions directory"""
    if not FINISHED_TRANSCRIPTIONS_DIR.exists():
        return []
    return sorted([f.name for f in FINISHED_TRANSCRIPTIONS_DIR.iterdir() if f.is_dir()])

def get_available_shot_types(folder_paths):
    """Determine which shot types are available in the selected folder"""
    available_shots = []
    
    # Check for Single Shot (single shot runs)
    if folder_paths['single_shot'].exists() and any(folder_paths['single_shot'].glob("*.json")):
        available_shots.append("Single Shot")
    
    # Check for First Shot
    if folder_paths['first_shot'].exists() and any(folder_paths['first_shot'].glob("*.json")):
        available_shots.append("First Shot")
    
    # Check for Second Shot
    if folder_paths['second_shot'].exists() and any(folder_paths['second_shot'].glob("*.json")):
        available_shots.append("Second Shot")
    
    return available_shots

def get_folder_paths(folder_name):
    """Get the paths for a specific folder"""
    base_dir = FINISHED_TRANSCRIPTIONS_DIR / folder_name
    
    # Check for different possible structures
    raw_transcriptions = base_dir / "Raw Transcriptions"
    
    paths = {
        'base': base_dir,
        'images': base_dir / "Segmented_Images",
    }
    
    # Add single shot path (for single shot runs)
    single_shot_path = raw_transcriptions / "Single Shot"
    if not single_shot_path.exists():
        single_shot_path = base_dir / "Single Shot"
    paths['single_shot'] = single_shot_path
    
    # Add first shot path if it exists
    first_shot_path = raw_transcriptions / "First Shot"
    if not first_shot_path.exists():
        # Try without "Raw Transcriptions" folder
        first_shot_path = base_dir / "First Shot"
    paths['first_shot'] = first_shot_path
    
    # Add second shot path if it exists
    second_shot_path = raw_transcriptions / "Second Shot"
    if not second_shot_path.exists():
        # Try without "Raw Transcriptions" folder
        second_shot_path = base_dir / "Second Shot"
    paths['second_shot'] = second_shot_path
    
    return paths

def get_image_files(images_dir):
    """Get all image files from the Segmented_Images directory"""
    if not images_dir.exists():
        return []
    return sorted([f for f in images_dir.glob("*.jpg")])

def get_transcription_path(image_name, shot_type, folder_paths):
    """Get the transcription file path for a given image"""
    base_name = image_name.replace(".jpg", "_transcription.json")
    if shot_type == "Single Shot":
        return folder_paths['single_shot'] / base_name
    elif shot_type == "First Shot":
        return folder_paths['first_shot'] / base_name
    else:
        return folder_paths['second_shot'] / base_name

def load_transcription(transcription_path):
    """Load transcription from JSON file"""
    if not transcription_path.exists():
        return None
    
    try:
        with open(transcription_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading transcription: {e}")
        return None

def get_csv_data(folder_paths, shot_type):
    """Load data from the CSV file for the selected shot type"""
    folder_name = folder_paths['base'].name
    if shot_type == "Single Shot":
        csv_path = folder_paths['base'] / f"{folder_name}_single_shot.csv"
    elif shot_type == "First Shot":
        csv_path = folder_paths['base'] / f"{folder_name}_first_shot.csv"
    else:
        csv_path = folder_paths['base'] / f"{folder_name}_second_shot.csv"
    
    if not csv_path.exists():
        return None, None
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = {row['Image']: row for row in reader}
        return rows, fieldnames
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None, None

def parse_transcription_text(text):
    """Parse the transcription text into a dictionary of fields"""
    fields = {}
    lines = text.strip().split('\n')
    
    for line in lines:
        if ':' in line and not line.startswith('#'):
            key, value = line.split(':', 1)
            fields[key.strip()] = value.strip()
    
    return fields

def fields_to_text(fields):
    """Convert fields dictionary back to formatted text"""
    lines = ["# Transcription of Herbarium Label", ""]
    for key, value in fields.items():
        if key not in ['Image', 'ImageURL']:  # Skip metadata fields
            lines.append(f"{key}: {value}")
    return '\n\n'.join([lines[0]] + ['\n'.join(lines[2:])])

def csv_row_to_fields(csv_row):
    """Convert CSV row to fields dictionary, excluding Image and ImageURL"""
    if not csv_row:
        return {}
    return {k: v for k, v in csv_row.items() if k not in ['Image', 'ImageURL']}

def update_csv_file(csv_path, image_name, updated_fields):
    """Update the corresponding row in the CSV file"""
    try:
        if not csv_path.exists():
            return False
        
        # Read the CSV
        rows = []
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['Image'] == image_name:
                    # Update this row with new values
                    for key, value in updated_fields.items():
                        if key in row:
                            row[key] = value
                rows.append(row)
        
        # Write back the CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        return True
    except Exception as e:
        st.error(f"Error updating CSV: {e}")
        return False

def save_pending_changes(folder_paths, shot_type):
    """Save any pending changes before navigating"""
    if st.session_state.pending_changes:
        try:
            image_name = st.session_state.pending_changes.get('image_name')
            updated_text = st.session_state.pending_changes.get('updated_text')
            updated_fields = st.session_state.pending_changes.get('updated_fields')
            transcription_data = st.session_state.pending_changes.get('transcription_data')
            
            if image_name and updated_text and transcription_data:
                transcription_path = st.session_state.pending_changes.get('transcription_path')
                save_transcription(transcription_path, transcription_data, updated_text, 
                                 folder_paths, image_name, shot_type, updated_fields)
        except Exception as e:
            st.error(f"Error saving pending changes: {e}")

def save_transcription(transcription_path, data, updated_text, folder_paths, image_name, shot_type, updated_fields=None):
    """Save the updated transcription back to the JSON file and update CSV"""
    try:
        # Update the text content in the data if data exists
        if data and 'content' in data and len(data['content']) > 0:
            data['content'][0]['text'] = updated_text
            
            # Save JSON
            with open(transcription_path, 'w') as f:
                json.dump(data, f, indent=2)
        
        # Use provided fields or parse from text
        if updated_fields is None:
            updated_fields = parse_transcription_text(updated_text)
        
        # Determine CSV file path
        folder_name = folder_paths['base'].name
        if shot_type == "Single Shot":
            csv_path = folder_paths['base'] / f"{folder_name}_single_shot.csv"
        elif shot_type == "First Shot":
            csv_path = folder_paths['base'] / f"{folder_name}_first_shot.csv"
        else:
            csv_path = folder_paths['base'] / f"{folder_name}_second_shot.csv"
        
        # Update CSV if it exists
        csv_updated = update_csv_file(csv_path, image_name, updated_fields)
        
        return True, csv_updated
    except Exception as e:
        st.error(f"Error saving transcription: {e}")
        return False, False

def main():
    st.title("🔬 Herbarium Transcription Viewer & Editor")
    st.markdown("View and edit transcriptions from segmented herbarium images")
    
    # Initialize session state for tracking changes
    if 'pending_changes' not in st.session_state:
        st.session_state.pending_changes = {}
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
    
    # Check if Finished Transcriptions folder exists
    if not FINISHED_TRANSCRIPTIONS_DIR.exists():
        st.error(f"❌ Finished Transcriptions folder not found at: `{FINISHED_TRANSCRIPTIONS_DIR}`")
        st.info("💡 Please ensure the CLI has created the 'Finished Transcriptions' folder on your Desktop.")
        return
    
    # Sidebar for navigation
    st.sidebar.header("Navigation")
    
    # Display base directory location
    st.sidebar.success(f"✅ Found: `{FINISHED_TRANSCRIPTIONS_DIR.name}`")
    st.sidebar.markdown("---")
    
    # Folder selection
    available_folders = get_available_folders()
    
    if not available_folders:
        st.error("No project folders found in the Finished Transcriptions directory")
        st.info(f"📁 Looking in: `{FINISHED_TRANSCRIPTIONS_DIR}`")
        return
    
    selected_folder = st.sidebar.selectbox(
        "📁 Select Folder",
        available_folders,
        key="folder_selector"
    )
    
    st.sidebar.markdown("---")
    
    # Get paths for selected folder
    folder_paths = get_folder_paths(selected_folder)
    
    # Check which shot types are available
    available_shots = get_available_shot_types(folder_paths)
    
    if not available_shots:
        st.error(f"No transcription files found in {selected_folder}")
        st.info("Please ensure the folder contains transcription data in 'Raw Transcriptions/Single Shot', 'Raw Transcriptions/First Shot', or 'Raw Transcriptions/Second Shot'")
        return
    
    # Get all image files from selected folder
    image_files = get_image_files(folder_paths['images'])
    
    if not image_files:
        st.error(f"No images found in {selected_folder}/Segmented_Images directory")
        st.info("Please select a different folder or ensure the folder contains segmented images.")
        return
    
    image_names = [f.name for f in image_files]
    
    # Reset index if out of bounds
    if st.session_state.current_image_index >= len(image_names):
        st.session_state.current_image_index = 0
    
    # Shot type selection - only show available shot types
    if len(available_shots) == 1:
        # Only one shot type available, use it directly
        shot_type = available_shots[0]
        st.sidebar.info(f"📝 Transcription Type: **{shot_type}**")
    else:
        # Multiple shot types available, let user choose
        shot_type = st.sidebar.radio(
            "📝 Transcription Type",
            available_shots,
            key="shot_type"
        )
    
    # Display mode
    display_mode = st.sidebar.radio(
        "👁️ Display Mode",
        ["Side by Side", "Stacked"],
        key="display_mode"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 Total Images: {len(image_files)}")
    st.sidebar.info(f"📁 Current Folder: {selected_folder}")
    st.sidebar.info(f"🖼️ Image {st.session_state.current_image_index + 1} of {len(image_names)}")
    
    # Navigation buttons at the top
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 1, 1])
    
    with col1:
        if st.button("⬅️ Previous", disabled=(st.session_state.current_image_index == 0), use_container_width=True):
            # Save pending changes before navigating
            save_pending_changes(folder_paths, shot_type)
            st.session_state.current_image_index -= 1
            st.session_state.pending_changes = {}
            st.rerun()
    
    with col2:
        if st.button("➡️ Next", disabled=(st.session_state.current_image_index == len(image_names) - 1), use_container_width=True):
            # Save pending changes before navigating
            save_pending_changes(folder_paths, shot_type)
            st.session_state.current_image_index += 1
            st.session_state.pending_changes = {}
            st.rerun()
    
    with col3:
        st.markdown(f"<h4 style='text-align: center;'>📷 {image_names[st.session_state.current_image_index]}</h4>", unsafe_allow_html=True)
    
    with col4:
        # Jump to first
        if st.button("⏮️ First", disabled=(st.session_state.current_image_index == 0), use_container_width=True):
            save_pending_changes(folder_paths, shot_type)
            st.session_state.current_image_index = 0
            st.session_state.pending_changes = {}
            st.rerun()
    
    with col5:
        # Jump to last
        if st.button("⏭️ Last", disabled=(st.session_state.current_image_index == len(image_names) - 1), use_container_width=True):
            save_pending_changes(folder_paths, shot_type)
            st.session_state.current_image_index = len(image_names) - 1
            st.session_state.pending_changes = {}
            st.rerun()
    
    st.markdown("---")
    
    # Get current image
    selected_image = image_names[st.session_state.current_image_index]
    
    # Load CSV data for this shot type
    csv_data, csv_fieldnames = get_csv_data(folder_paths, shot_type)
    
    # Main content area
    if selected_image:
        image_path = folder_paths['images'] / selected_image
        transcription_path = get_transcription_path(selected_image, shot_type, folder_paths)
        
        # Load transcription
        transcription_data = load_transcription(transcription_path)
        
        if display_mode == "Side by Side":
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📷 Image")
                try:
                    image = Image.open(image_path)
                    st.image(image, use_container_width=True)
                except Exception as e:
                    st.error(f"Error loading image: {e}")
            
            with col2:
                st.subheader(f"📝 {shot_type} Transcription")
                display_and_edit_transcription(transcription_path, transcription_data, selected_image,
                                             folder_paths, shot_type, csv_data, csv_fieldnames)
        
        else:  # Stacked mode
            st.subheader("📷 Image")
            try:
                image = Image.open(image_path)
                st.image(image, use_container_width=True)
            except Exception as e:
                st.error(f"Error loading image: {e}")
            
            st.markdown("---")
            st.subheader(f"📝 {shot_type} Transcription")
            display_and_edit_transcription(transcription_path, transcription_data, selected_image, 
                                         folder_paths, shot_type, csv_data, csv_fieldnames)

def display_and_edit_transcription(transcription_path, transcription_data, selected_image, 
                                  folder_paths, shot_type, csv_data, csv_fieldnames):
    """Display and allow editing of transcription data"""
    
    # Check if we have CSV data for this image
    if csv_data is None:
        st.error("❌ CSV file not found. Cannot display transcription data.")
        st.info("The CSV file should be in the folder with the format: `{folder_name}_{shot_type}.csv`")
        return
    
    if selected_image not in csv_data:
        st.warning(f"⚠️ No data found for {selected_image} in CSV file")
        st.info("This image may not have been processed or is missing from the CSV.")
        return
    
    # Get the CSV row for this image
    csv_row = csv_data[selected_image]
    fields = csv_row_to_fields(csv_row)
    
    # Also show JSON transcription metadata if available
    if transcription_data is not None:
        # Display metadata
        with st.expander("📊 Transcription Metadata", expanded=False):
            cols = st.columns(3)
            with cols[0]:
                st.write(f"**Model:** {transcription_data.get('model', 'N/A')}")
            with cols[1]:
                st.write(f"**Timestamp:** {transcription_data.get('timestamp', 'N/A')[:10]}")
            with cols[2]:
                if 'usage' in transcription_data:
                    tokens = transcription_data['usage'].get('input_tokens', 0) + \
                            transcription_data['usage'].get('output_tokens', 0)
                    st.write(f"**Tokens:** {tokens}")
    
    st.markdown("---")
    
    # Create tabs for different editing modes
    tab1, tab2 = st.tabs(["📋 Field Editor", "📄 CSV View"])
    
    with tab1:
        st.markdown("**Edit transcription fields:**")
        
        # Create editable fields
        edited_fields = {}
        
        # Group fields by category for better organization
        collector_fields = ['verbatimCollectors', 'collectedBy', 'secondaryCollectors', 'recordNumber']
        date_fields = ['verbatimEventDate', 'minimumEventDate', 'maximumEventDate']
        identification_fields = ['verbatimIdentification', 'latestScientificName', 'VerifiedLatestScientificName', 
                                'MatchType', 'VerifiedBy', 'Source', 'identifiedBy', 'verbatimDateIdentified']
        location_fields = ['country', 'firstPoliticalUnit', 'secondPoliticalUnit', 'municipality', 
                          'verbatimLocality', 'locality', 'habitat', 'verbatimElevation', 'verbatimCoordinates']
        other_fields = ['associatedTaxa', 'otherCatalogNumbers', 'originalMethod', 'typeStatus']
        
        # Collector Information
        with st.expander("👥 Collector Information", expanded=True):
            for key in collector_fields:
                if key in fields:
                    edited_fields[key] = st.text_input(
                        key,
                        value=fields[key],
                        key=f"field_{key}_{selected_image}"
                    )
        
        # Date Information
        with st.expander("📅 Date Information", expanded=True):
            for key in date_fields:
                if key in fields:
                    edited_fields[key] = st.text_input(
                        key,
                        value=fields[key],
                        key=f"field_{key}_{selected_image}"
                    )
        
        # Identification Information
        with st.expander("🔬 Identification & Validation", expanded=True):
            for key in identification_fields:
                if key in fields:
                    edited_fields[key] = st.text_input(
                        key,
                        value=fields[key],
                        key=f"field_{key}_{selected_image}"
                    )
        
        # Location Information
        with st.expander("📍 Location Information", expanded=True):
            for key in location_fields:
                if key in fields:
                    edited_fields[key] = st.text_input(
                        key,
                        value=fields[key],
                        key=f"field_{key}_{selected_image}"
                    )
        
        # Other Information
        with st.expander("📝 Additional Information", expanded=True):
            for key in other_fields:
                if key in fields:
                    edited_fields[key] = st.text_input(
                        key,
                        value=fields[key],
                        key=f"field_{key}_{selected_image}"
                    )
        
        # Check if any field was modified
        fields_modified = any(edited_fields.get(k) != fields.get(k) for k in fields.keys() if k in edited_fields)
        
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("💾 Save Now", type="primary", disabled=not fields_modified):
                # Update CSV and JSON
                json_saved, csv_updated = save_transcription(transcription_path, transcription_data, 
                                                             fields_to_text(edited_fields), folder_paths, 
                                                             selected_image, shot_type, edited_fields)
                if json_saved:
                    if csv_updated:
                        st.success("✅ Saved! (JSON + CSV)")
                    else:
                        st.success("✅ Saved! (JSON only)")
                    st.rerun()
        
        # Store changes in session state for auto-save on navigation
        if fields_modified:
            st.session_state.pending_changes = {
                'image_name': selected_image,
                'updated_text': fields_to_text(edited_fields),
                'updated_fields': edited_fields,
                'transcription_data': transcription_data,
                'transcription_path': transcription_path
            }
            st.info("💡 Changes detected. Click 'Save Now' or navigate to auto-save.")
    
    with tab2:
        st.markdown("**Raw CSV Data View:**")
        
        # Display all CSV data in a formatted way
        csv_display = []
        for key, value in csv_row.items():
            csv_display.append(f"**{key}:** {value}")
        
        st.text_area(
            "CSV Row Data",
            value='\n\n'.join(csv_display),
            height=500,
            disabled=True,
            key=f"csv_view_{selected_image}"
        )

if __name__ == "__main__":
    main()
