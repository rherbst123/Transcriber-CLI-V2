import requests
import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Constants
PORTAL_API_URL = "https://bryophyteportal.org/portal/api/v2/occurrence"
REQUEST_TIMEOUT = 30

def search_portal_by_barcode(barcode: str) -> Optional[Dict]:
    if not barcode or barcode == "N/A":
        return None
    
    # Query parameters - search by catalogNumber, not occurrenceID
    params = {
        'catalogNumber': barcode,
        'limit': 100,
        'offset': 0
    }

    # Add headers to mimic a browser request and avoid 403 errors
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        response = requests.get(PORTAL_API_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Process response to find results
        results = None
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            # Check common response structure keys - prioritize 'results' since that's what the API returns
            for key in ['results', 'data', 'records', 'items']:
                if key in data and isinstance(data[key], list):
                    results = data[key]
                    break
            
            # If still no results, check for any list in the response
            if results is None:
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        results = value
                        break
        
        return results[0] if results and len(results) > 0 else None
        
    except requests.exceptions.RequestException as e:
        print(f"Warning: Error searching portal for {barcode}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing response for {barcode}: {e}")
        return None

def extract_duplicate_info(portal_record: Dict) -> Dict[str, str]:
    if not portal_record:
        return {
            "DuplicateFound": "No"
        }
    
    return {
        "DuplicateFound": "Yes",
        "DuplicateScientificName": portal_record.get('sciname', ''),
        "DuplicateLocality": portal_record.get('locality', ''),
        "DuplicateCollector": portal_record.get('recordedBy', ''),
        "DuplicateDate": portal_record.get('eventDate', ''),
        "DuplicateInstitution": portal_record.get('institutionCode', ''),
        "DuplicateCatalogNumber": portal_record.get('catalogNumber', '')
    }

def validate_csv_duplicate_records(csv_path: Path):
    print(f"\n=== Validating duplicate records in {csv_path.name} ===")
    
    with open(csv_path, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)
        
        # Find Barcode column and insert duplicate validation columns after it
        barcode_col_idx = None
        for idx, col in enumerate(fieldnames):
            if col.lower() in ['barcode', 'occurrenceid', 'occurrence_id']:
                barcode_col_idx = idx
                break
        
        if barcode_col_idx is None:
            print("Warning: 'Barcode' column not found, skipping duplicate validation")
            return
        
        rows = list(reader)
    
    # Extract unique barcodes for validation
    barcodes_to_check = []
    barcode_column = fieldnames[barcode_col_idx]
    
    for row in rows:
        barcode = row.get(barcode_column, '').strip()
        if barcode and barcode != "N/A" and barcode not in barcodes_to_check:
            barcodes_to_check.append(barcode)
    
    if not barcodes_to_check:
        print("No barcodes found to validate")
        return
    
    print(f"Checking {len(barcodes_to_check)} unique barcodes for duplicates...")
    
    # Check each barcode for duplicates
    duplicate_results = {}
    duplicates_found = False
    
    for barcode in barcodes_to_check:
        print(f"  Checking barcode: {barcode}")
        portal_record = search_portal_by_barcode(barcode)
        duplicate_info = extract_duplicate_info(portal_record)
        duplicate_results[barcode] = duplicate_info
        
        if duplicate_info["DuplicateFound"] == "Yes":
            duplicates_found = True
            print(f"    → DUPLICATE FOUND: {duplicate_info['DuplicateScientificName']} from {duplicate_info['DuplicateInstitution']}")
        else:
            print(f"    → No duplicate found")
    
    # Determine which columns to add based on whether any duplicates were found
    if duplicates_found:
        # Add all duplicate columns after the barcode column
        new_columns = [
            'DuplicateFound', 'DuplicateScientificName', 'DuplicateLocality', 
            'DuplicateCollector', 'DuplicateDate', 'DuplicateInstitution', 
            'DuplicateCatalogNumber'
        ]
    else:
        # Only add the DuplicateFound column
        new_columns = ['DuplicateFound']
    
    # Insert new columns after the barcode column
    for i, col in enumerate(new_columns):
        fieldnames.insert(barcode_col_idx + 1 + i, col)
    
    # Update CSV with duplicate information
    with open(csv_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            barcode = row.get(barcode_column, '').strip()
            if barcode in duplicate_results:
                info = duplicate_results[barcode]
                # Only add columns that exist in fieldnames
                for key, value in info.items():
                    if key in fieldnames:
                        row[key] = value
            else:
                # Set default values for rows without barcodes
                row['DuplicateFound'] = "No"
                # Only set other duplicate fields if they exist in the fieldnames
                if duplicates_found:
                    for col in new_columns[1:]:  # Skip 'DuplicateFound' since we already set it
                        row[col] = "N/A"
            
            writer.writerow(row)
    
    total_duplicates = sum(1 for info in duplicate_results.values() if info["DuplicateFound"] == "Yes")
    print(f"✓ Duplicate validation completed. Found {total_duplicates} duplicates out of {len(barcodes_to_check)} checked barcodes")
    print(f"  Results added to {csv_path.name}")
    if duplicates_found:
        print(f"  Added detailed duplicate information columns")
    else:
        print(f"  Added only 'DuplicateFound' column (no duplicates detected)")

def main():
    if len(sys.argv) != 2:
        print("Usage: python find_duplicate_records.py <csv_file_path>")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    validate_csv_duplicate_records(csv_path)

if __name__ == "__main__":
    main()
