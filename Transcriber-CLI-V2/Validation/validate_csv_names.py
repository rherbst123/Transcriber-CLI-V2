#!/usr/bin/env python3
# validate_csv_names.py - Integration function for the main pipeline

import csv
import sys
from pathlib import Path
from typing import List, Union
import requests

# Constants
DEFAULT_API = "https://verifier.globalnames.org/api/v1/verifications"
CHUNK_SIZE = 1_000
DEFAULT_SOURCES = [165]  # Tropicos

def post_chunk(names: List[str], api: str = DEFAULT_API, preferred=None, timeout: int = 30):
    """Send chunk of names to GN Verifier and return raw records."""
    if len(names) > CHUNK_SIZE:
        raise ValueError(f"max {CHUNK_SIZE} names per request")

    payload = {"nameStrings": names}
    if preferred:
        payload["preferredSources"] = list(preferred)
        payload["dataSources"] = list(preferred)

    r = requests.post(api, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data.get("verifications") or data.get("names") or data

def first(obj: dict, *keys: str, default: str = "") -> str:
    """Return the first non-empty value among keys."""
    if isinstance(obj, dict):
        for k in keys:
            val = obj.get(k)
            if val not in (None, "", []):
                return str(val)
    return default

def get_verified_name(rec: dict) -> str:
    """Extract the best verified name from a record."""
    if "bestResult" in rec:
        best = rec["bestResult"]
    else:
        best = rec

    if isinstance(best, str):
        return best

    return (
        best.get("matchedCanonicalFull") or
        best.get("matchedCanonicalSimple") or
        best.get("canonical") or
        ""
    )

def validate_csv_scientific_names(csv_path: Path, sources: List[int] = None):
    """Validate scientific names in CSV and add VerifiedLatestScientificName column."""
    if sources is None:
        sources = DEFAULT_SOURCES
    
    print(f"\n=== Validating scientific names in {csv_path.name} ===")
    
    with open(csv_path, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)
        
        # Find latestScientificName column and insert VerifiedLatestScientificName after it
        try:
            idx = fieldnames.index('latestScientificName')
            fieldnames.insert(idx + 1, 'VerifiedLatestScientificName')
        except ValueError:
            print("Warning: 'latestScientificName' column not found, skipping validation")
            return
        
        rows = list(reader)
    
    # Extract unique names for verification
    names_to_verify = []
    for row in rows:
        name = row.get('latestScientificName', '').strip()
        if name and name not in names_to_verify:
            names_to_verify.append(name)
    
    if not names_to_verify:
        print("No names found to verify")
        return
    
    print(f"Verifying {len(names_to_verify)} unique names...")
    
    # Process names in chunks
    verified_names = {}
    try:
        for i in range(0, len(names_to_verify), CHUNK_SIZE):
            chunk = names_to_verify[i:i + CHUNK_SIZE]
            recs = post_chunk(chunk, DEFAULT_API, sources)
            for rec in recs:
                original = first(rec, "inputStr", "name")
                verified = get_verified_name(rec)
                verified_names[original] = verified if verified else original
                
                # Display original and validated names
                if verified and verified != original:
                    print(f"  {original} → {verified}")
                else:
                    print(f"  {original} (no change)")
    except Exception as exc:
        print(f"Warning: Name validation failed ({exc}), keeping original names")
        # If validation fails, use original names
        for name in names_to_verify:
            verified_names[name] = name
    
    # Overwrite the original CSV with verified names
    with open(csv_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            original_name = row.get('latestScientificName', '').strip()
            row['VerifiedLatestScientificName'] = verified_names.get(original_name, original_name)
            writer.writerow(row)
    
    print(f"✓ Scientific names validated and added to {csv_path.name}")