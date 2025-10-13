# Transcription Viewer & Editor

A Streamlit web application for viewing and editing herbarium transcriptions from segmented images.

## Features

- 📷 **Image Viewing**: Browse through all segmented herbarium images
- 📝 **Transcription Display**: View both First Shot and Second Shot transcriptions
- ✏️ **Edit Capabilities**: Edit transcriptions using either:
  - Field-by-field editor for structured data
  - Raw text editor for full control
- 💾 **Save Changes**: Persist edits back to the original JSON files
- 🔄 **Multiple Views**: Switch between side-by-side and stacked display modes

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the Streamlit app:
```bash
streamlit run transcription_viewer.py
```

The app will open in your default web browser. You can then:
1. Select an image from the sidebar dropdown
2. Choose between First Shot or Second Shot transcriptions
3. Edit the transcription fields or raw text
4. Save your changes

## Directory Structure

The app expects the following structure:
```
TestOutput/
  TestingTrays/
    Segmented_Images/          # Source images
    Raw Transcriptions/
      First Shot/              # First shot transcriptions
      Second Shot/             # Second shot transcriptions
```

## Features Explained

### Display Modes
- **Side by Side**: View the image and transcription side by side
- **Stacked**: View the image above the transcription

### Editing Modes
- **Field Editor**: Edit individual fields in a form layout
- **Raw Text Editor**: Edit the entire transcription as text

### Navigation
Use the sidebar to:
- Select different images
- Switch between transcription types
- Change display modes
- See total image count
