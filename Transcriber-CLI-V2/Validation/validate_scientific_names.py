#!/usr/bin/env python3
# validate_csv_names.py - Integration function for the main pipeline

#Using GlobalNames Verifier. 
#https://globalnames.org/

import argparse
import csv
import sys
import textwrap
from pathlib import Path
from typing import List, Union, Dict
import requests

# Constants
DEFAULT_API = "https://verifier.globalnames.org/api/v1/verifications"
CHUNK_SIZE = 1_000
DEFAULT_SOURCES = [165]  # Tropicos

def post_chunk(names: List[str], api: str = DEFAULT_API, preferred=None, timeout: int = 30):
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
    if isinstance(obj, dict):
        for k in keys:
            val = obj.get(k)
            if val not in (None, "", []):
                return str(val)
    return default

def get_verified_info(rec: dict) -> dict:
    if "bestResult" in rec:
        best = rec["bestResult"]
        container = rec
    else:
        best = rec
        container = rec

    if isinstance(best, str):  # "mixed" layout
        return {
            "name": best,
            "match_type": "Unknown",
            "author": "",
            "source": ""
        }

    # Get the canonical name
    verified_name = (
        best.get("matchedCanonicalFull") or
        best.get("matchedCanonicalSimple") or
        best.get("canonical") or
        ""
    )
    
    # Determine match type
    match_type = (
        best.get("matchType") or
        container.get("matchType") or
        ("Exact" if str(best.get("editDistance") or container.get("editDistance")) == "0" else "Fuzzy")
    )
    
    # Get authorship information
    authors = (
        best.get("authorship") or
        container.get("authorship") or
        best.get("author") or
        container.get("author") or
        ""
    )
    
    # Fall-back: pull authorship tail out of matchedName
    if not authors:
        matched_name = best.get("matchedName") or container.get("matchedName")
        if matched_name and verified_name and matched_name.startswith(verified_name):
            tail = matched_name[len(verified_name):].lstrip(" ,")
            authors = tail if tail else ""
    
    # Get source information
    source = (
        first(best, "dataSourceTitleShort", "dataSourceTitle") or
        first(container, "dataSourceTitleShort", "dataSourceTitle") or
        ""
    )
    
    return {
        "name": verified_name,
        "match_type": match_type,
        "author": authors,
        "source": source
    }

def get_verified_name(rec: dict) -> str:
    """Extract the best verified name from a record (backward compatibility)."""
    return get_verified_info(rec)["name"]

def validate_csv_scientific_names(csv_path: Path, sources: List[int] = None):
    """Validate scientific names in CSV and add verification columns."""
    if sources is None:
        sources = DEFAULT_SOURCES
    
    print(f"\n=== Validating scientific names in {csv_path.name} ===")
    
    with open(csv_path, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)
        
        # Find latestScientificName column and insert verification columns after it
        try:
            idx = fieldnames.index('latestScientificName')
            new_columns = ['VerifiedLatestScientificName', 'MatchType', 'VerifiedBy', 'Source']
            for i, col in enumerate(new_columns):
                fieldnames.insert(idx + 1 + i, col)
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
    verification_results = {}
    try:
        for i in range(0, len(names_to_verify), CHUNK_SIZE):
            chunk = names_to_verify[i:i + CHUNK_SIZE]
            recs = post_chunk(chunk, DEFAULT_API, sources)
            for rec in recs:
                original = first(rec, "inputStr", "name")
                verified_info = get_verified_info(rec)
                verification_results[original] = verified_info
                
                # Display original and validated names with match info
                verified_name = verified_info["name"]
                match_type = verified_info["match_type"]
                
                if verified_name and verified_name != original:
                    print(f"  {original.ljust(30)[:30]} → {verified_name} | {match_type} | {verified_info['source']}")
                else:
                    print(f"  {original.ljust(30)[:30]} | {match_type} | {verified_info['source']}")
    except Exception as exc:
        print(f"Warning: Name validation failed ({exc}), keeping original names")
        # If validation fails, use original names
        for name in names_to_verify:
            verification_results[name] = {
                "name": name,
                "match_type": "Error",
                "author": "",
                "source": ""
            }
    
    # Overwrite the original CSV with verified names and additional info
    with open(csv_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            original_name = row.get('latestScientificName', '').strip()
            if original_name in verification_results:
                info = verification_results[original_name]
                row['VerifiedLatestScientificName'] = info["name"] or original_name
                row['MatchType'] = info["match_type"]
                row['VerifiedBy'] = info["author"]
                row['Source'] = info["source"]
            else:
                row['VerifiedLatestScientificName'] = original_name
                row['MatchType'] = "Not Verified"
                row['VerifiedBy'] = ""
                row['Source'] = ""
            writer.writerow(row)
    
    print(f"✓ Scientific names validated and added to {csv_path.name} with match types, authors, and sources")