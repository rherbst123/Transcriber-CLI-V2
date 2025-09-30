```text
  _______                            _ _                       _____ _      _____ 
 |__   __|                          (_) |                     / ____| |    |_   _|
    | |_ __ __ _ _ __  ___  ___ _ __ _| |__   ___ _ __ ______| |    | |      | |  
    | | '__/ _` | '_ \/ __|/ __| '__| | '_ \ / _ \ '__|______| |    | |      | |  
    | | | | (_| | | | \__ \ (__| |  | | |_) |  __/ |         | |____| |____ _| |_ 
    |_|_|  \__,_|_| |_|___/\___|_|  |_|_.__/ \___|_|          \_____|______|_____|
                                                                                  
                                                                                  
```

A command-line interface tool for transcribing herbarium label details from images using AWS Bedrock AI models.

## Overview

Transcriber CLI is designed to process and transcribe text from herbarium specimen images:

- **First Shot**: Processes full images to extract label information
- **Second Shot**: Processes Images once more. (First shot results + Image) for another pass


## Prerequisites

- Python 3.x
- AWS account with Bedrock access
- Properly configured AWS credentials: [AWS CLI](https://aws.amazon.com/cli/)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/rherbst123/Transcriber-CLI-V2
   cd Transcriber_CLI
   ```
2. 
    - Create a virtual enviroment 
   ```
   python3 -m venv "Whatever you want to call the venv"
   ```
3. Install required dependencies:
    
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the main script:

```
python TranscribeCLI.py
```

The tool will:
1. Ask you to name the run
2. How many Runs to do
3. Choose Model For First run
4. Let Run complete
5. Ask Model for second shot (If chosen)
6. Output a completed .csv file to your desktop with a cost analysis and raw .json files 

## Future Updates

- [x] Scientific Name Validation (Done with Global Names Validator on Tropicos) [Global Names](https://verifier.globalnames.org/)
- [ ] Validation using GBIF, IDigBio and Sybiota ()
- [ ] Search in Portal for Duplicate Catalog numbers
- [ ] Search in Portal for Entries on "Collector, record Number and Date" 
- [x] Automatic Segmentation for all images done before transcription

## Supported AI Models

The tool supports multiple AWS Bedrock models:
- Claude 3 Sonnet
- Claude 3.7 Sonnet
- Claude 4 Sonnet
- Claude 4.5 Sonnet
- Claude 4 Opus
- Claude 4.1 Opus
- LLama 3.2 90b 
- LLama 4 17b
- Amazon Nova-lite,pro,premier
- Mistral Pixtral Large

##### More models will be added as they come out. 

## Output

Transcription results are saved in:
- Desktop/Finished_Transcriptions_"User Entered Run Name"

## Prompts

The tool uses specialized prompts for herbarium label transcription, located in the `Prompts/` directory. The default prompt (Prompt_1.5.3.txt) is designed to extract detailed information from herbarium labels following specific formatting rules.

## Customization

- Modify prompts in the `Prompts/` directory to adjust transcription behavior
- Add or remove models in the `AVAILABLE_MODELS` list in each transcriber module (This is updated frequently so you dont have to really)



Created by Riley Herbst, for the Field Museum. With much thanks to the following: Matt Von Konrat, Jeff Gwilliam, Dan Stille 



