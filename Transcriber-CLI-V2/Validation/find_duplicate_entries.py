import requests
import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Constants
PORTAL_API_URL = "https://bryophyteportal.org/portal/api/v2/occurrence"
REQUEST_TIMEOUT = 30

def search_portal_by_criteria(collector: str, collection_date: str, collid: str, filter_institutions: bool = True) -> Optional[List[Dict]]:    
    # Query parameters - build dynamically based on provided inputs
    params = {
        'limit': 100,
        'offset': 0
    }
    
    # Add parameters only if values are provided
    if collector and collector.strip():
        params['recordedBy'] = collector.strip()
    if collection_date and collection_date.strip():
        params['eventDate'] = collection_date.strip()
    if collid and collid.strip():
        params['recordNumber'] = collid.strip()
    
    # Check if at least one search criterion is provided
    if not any([collector and collector.strip(), collection_date and collection_date.strip(), collid and collid.strip()]):
        return None

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
        
        # Filter results to only include specified institution codes if requested
        if results and filter_institutions:
            target_institutions = ["F", "TENN", "MICH", "NY", "MO"]
            results = [record for record in results 
                      if record.get('institutionCode', '').strip() in target_institutions]
        
        return results if results else []
        
    except requests.exceptions.RequestException as e:
        print(f"Warning: Error searching portal for collector='{collector}', date='{collection_date}', collid='{collid}': {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing response for collector='{collector}', date='{collection_date}', collid='{collid}': {e}")
        return None

def display_detailed_record(record: Dict, record_number: int = 1):
    print(f"\nRecord {record_number}:")
    print(f"  occid:                      {record.get('occid', 'N/A')}")
    print(f"  collid:                     {record.get('collid', 'N/A')}")
    print(f"  occurrenceID:               {record.get('occurrenceID', 'N/A')}")
    print(f"  catalogNumber:              {record.get('catalogNumber', 'N/A')}")
    print(f"  otherCatalogNumbers:        {record.get('otherCatalogNumbers', 'N/A')}")
    print(f"  ownerInstitutionCode:       {record.get('ownerInstitutionCode', 'N/A')}")
    print(f"  family:                     {record.get('family', 'N/A')}")
    print(f"  sciname:                    {record.get('sciname', 'N/A')}")
    print(f"  genus:                      {record.get('genus', 'N/A')}")
    print(f"  specificEpithet:            {record.get('specificEpithet', 'N/A')}")
    print(f"  institutionCode:            {record.get('institutionCode', 'N/A')}")
    print(f"  collectionCode:             {record.get('collectionCode', 'N/A')}")
    print(f"  scientificNameAuthorship:   {record.get('scientificNameAuthorship', 'N/A')}")
    print(f"  taxonRemarks:               {record.get('taxonRemarks', 'N/A')}")
    print(f"  identifiedBy:               {record.get('identifiedBy', 'N/A')}")
    print(f"  dateIdentified:             {record.get('dateIdentified', 'N/A')}")
    print(f"  identificationReferences:   {record.get('identificationReferences', 'N/A')}")
    print(f"  identificationRemarks:      {record.get('identificationRemarks', 'N/A')}")
    print(f"  identificationQualifier:    {record.get('identificationQualifier', 'N/A')}")
    print(f"  typeStatus:                 {record.get('typeStatus', 'N/A')}")
    print(f"  recordedBy:                 {record.get('recordedBy', 'N/A')}")
    print(f"  recordNumber:               {record.get('recordNumber', 'N/A')}")
    print(f"  associatedCollectors:       {record.get('associatedCollectors', 'N/A')}")
    print(f"  eventDate:                  {record.get('eventDate', 'N/A')}")
    print(f"  eventDate2:                 {record.get('eventDate2', 'N/A')}")
    print(f"  year:                       {record.get('year', 'N/A')}")
    print(f"  month:                      {record.get('month', 'N/A')}")
    print(f"  day:                        {record.get('day', 'N/A')}")
    print(f"  startDayOfYear:             {record.get('startDayOfYear', 'N/A')}")
    print(f"  endDayOfYear:               {record.get('endDayOfYear', 'N/A')}")
    print(f"  verbatimEventDate:          {record.get('verbatimEventDate', 'N/A')}")
    print(f"  eventTime:                  {record.get('eventTime', 'N/A')}")
    print(f"  habitat:                    {record.get('habitat', 'N/A')}")
    print(f"  substrate:                  {record.get('substrate', 'N/A')}")
    print(f"  eventID:                    {record.get('eventID', 'N/A')}")
    print(f"  occurrenceRemarks:          {record.get('occurrenceRemarks', 'N/A')}")
    print(f"  associatedTaxa:             {record.get('associatedTaxa', 'N/A')}")
    print(f"  dynamicProperties:          {record.get('dynamicProperties', 'N/A')}")
    print(f"  verbatimAttributes:         {record.get('verbatimAttributes', 'N/A')}")
    print(f"  locationID:                 {record.get('locationID', 'N/A')}")
    print(f"  continent:                  {record.get('continent', 'N/A')}")
    print(f"  waterBody:                  {record.get('waterBody', 'N/A')}")
    print(f"  parentLocationID:           {record.get('parentLocationID', 'N/A')}")
    print(f"  country:                    {record.get('country', 'N/A')}")
    print(f"  stateProvince:              {record.get('stateProvince', 'N/A')}")
    print(f"  county:                     {record.get('county', 'N/A')}")
    print(f"  municipality:               {record.get('municipality', 'N/A')}")
    print(f"  islandGroup:                {record.get('islandGroup', 'N/A')}")
    print(f"  island:                     {record.get('island', 'N/A')}")
    print(f"  countryCode:                {record.get('countryCode', 'N/A')}")
    print(f"  locality:                   {record.get('locality', 'N/A')}")
    print(f"  recordSecurity:             {record.get('recordSecurity', 'N/A')}")
    print(f"  decimalLatitude:            {record.get('decimalLatitude', 'N/A')}")
    print(f"  decimalLongitude:           {record.get('decimalLongitude', 'N/A')}")
    print(f"  locationRemarks:            {record.get('locationRemarks', 'N/A')}")
    print(f"  verbatimCoordinates:        {record.get('verbatimCoordinates', 'N/A')}")
    print(f"  minimumElevationInMeters:   {record.get('minimumElevationInMeters', 'N/A')}")
    print(f"  maximumElevationInMeters:   {record.get('maximumElevationInMeters', 'N/A')}")
    print(f"  verbatimElevation:          {record.get('verbatimElevation', 'N/A')}")
    print(f"  minimumDepthInMeters:       {record.get('minimumDepthInMeters', 'N/A')}")
    print(f"  maximumDepthInMeters:       {record.get('maximumDepthInMeters', 'N/A')}")
    print(f"  verbatimDepth:              {record.get('verbatimDepth', 'N/A')}")
    print("-" * 40)

def count_populated_fields(record: Dict) -> int:
    count = 0
    for key, value in record.items():
        # Skip occid field
        if key == 'occid':
            continue
        
        # Check if field is truly populated (not None, not empty, not the string "None", not "N/A")
        value_str = str(value).strip().lower()
        if (value is not None and 
            value_str != '' and 
            value_str != 'none' and
            value_str != 'null' and
            value_str != 'n/a'):
            count += 1
    return count

def find_best_record(portal_records: List[Dict]) -> Tuple[Optional[Dict], int]:
    if not portal_records or len(portal_records) == 0:
        return None, 0
    
    # Calculate populated field counts for all records
    records_with_counts = []
    for record in portal_records:
        field_count = count_populated_fields(record)
        records_with_counts.append((record, field_count))
    
    # Sort by field count (descending) and get the record with most fields
    records_with_counts.sort(key=lambda x: x[1], reverse=True)
    best_record, best_count = records_with_counts[0]
    
    return best_record, best_count

def get_field_mapping():

    return {
        'verbatimCollectors': 'recordedBy',
        'collectedBy': 'recordedBy',
        'secondaryCollectors': 'associatedCollectors',
        'recordNumber': 'recordNumber',
        'verbatimEventDate': 'verbatimEventDate',
        'minimumEventDate': 'eventDate',
        'maximumEventDate': 'eventDate2',
        'verbatimIdentification': 'sciname',
        'latestScientificName': 'sciname',
        'identifiedBy': 'identifiedBy',
        'verbatimDateIdentified': 'dateIdentified',
        'associatedTaxa': 'associatedTaxa',
        'country': 'country',
        'firstPoliticalUnit': 'stateProvince',
        'secondPoliticalUnit': 'county',
        'municipality': 'municipality',
        'verbatimLocality': 'locality',
        'locality': 'locality',
        'habitat': 'habitat',
        'verbatimElevation': 'verbatimElevation',
        'verbatimCoordinates': 'verbatimCoordinates',
        'otherCatalogNumbers': 'otherCatalogNumbers',
        'originalMethod': 'dynamicProperties',
        'typeStatus': 'typeStatus',
        'catalogNumber': 'catalogNumber',
        'occurrenceID': 'occurrenceID',
        'ownerInstitutionCode': 'ownerInstitutionCode',
        'family': 'family',
        'genus': 'genus',
        'specificEpithet': 'specificEpithet',
        'institutionCode': 'institutionCode',
        'collectionCode': 'collectionCode',
        'scientificNameAuthorship': 'scientificNameAuthorship',
        'taxonRemarks': 'taxonRemarks',
        'identificationReferences': 'identificationReferences',
        'identificationRemarks': 'identificationRemarks',
        'identificationQualifier': 'identificationQualifier',
        'year': 'year',
        'month': 'month',
        'day': 'day',
        'eventTime': 'eventTime',
        'substrate': 'substrate',
        'eventID': 'eventID',
        'occurrenceRemarks': 'occurrenceRemarks',
        'dynamicProperties': 'dynamicProperties',
        'verbatimAttributes': 'verbatimAttributes',
        'locationID': 'locationID',
        'continent': 'continent',
        'waterBody': 'waterBody',
        'islandGroup': 'islandGroup',
        'island': 'island',
        'countryCode': 'countryCode',
        'locationRemarks': 'locationRemarks',
        'decimalLatitude': 'decimalLatitude',
        'decimalLongitude': 'decimalLongitude',
        'minimumElevationInMeters': 'minimumElevationInMeters',
        'maximumElevationInMeters': 'maximumElevationInMeters',
        'minimumDepthInMeters': 'minimumDepthInMeters',
        'maximumDepthInMeters': 'maximumDepthInMeters',
        'verbatimDepth': 'verbatimDepth',
    }

def extract_entry_info(portal_records: List[Dict]) -> Dict[str, str]:
    if not portal_records or len(portal_records) == 0:
        return {
            "EntriesFound": "No",
            "EntryCount": "0"
        }
    
    # Only return the basic yes/no and count information
    return {
        "EntriesFound": "Yes",
        "EntryCount": str(len(portal_records))
    }

def search_entries_interactive():
    # Get search criteria from user
    collector = input("Enter Collector name (recordedBy): ").strip()
    collection_date = input("Enter Collection date (eventDate, YYYY-MM-DD format): ").strip()
    collid = input("Enter Record Number (recordNumber): ").strip()
    
    # Ask about institution filtering
    filter_choice = input("Filter results to institutions F, TENN, MICH, NY? (y/n, default=y): ").strip().lower()
    filter_institutions = filter_choice != 'n'
    
    # Check if at least one search criterion is provided
    if not any([collector, collection_date, collid]):
        print("Error: At least one search criterion must be provided.")
        sys.exit(1)
    
    print(f"\nSearching for:")
    if collector:
        print(f"  Collector: {collector}")
    if collection_date:
        print(f"  Date: {collection_date}")
    if collid:
        print(f"  Record Number: {collid}")
    
    if filter_institutions:
        print(f"  Filtering to institutions: F, TENN, MICH, NY, MO")
    else:
        print(f"  Including all institutions")
    
    portal_records = search_portal_by_criteria(collector, collection_date, collid, filter_institutions)
    
    if portal_records is None:
        print("Error occurred during search.")
        return
    
    if filter_institutions and len(portal_records) == 0:
        # Try again without filtering to see if there are any results at all
        all_records = search_portal_by_criteria(collector, collection_date, collid, False)
        if all_records and len(all_records) > 0:
            print(f"\nFound {len(all_records)} total records, but 0 from specified institutions (F, TENN, MICH, NY)")
            return
    
    print(f"\nFound {len(portal_records)} records:")
    
    if len(portal_records) == 0:
        print("No records found from the specified institutions.")
        return
    
    # Find the record with the most populated fields
    best_record, best_count = find_best_record(portal_records)
    
    if best_record:
        print(f"\nShowing record with the most populated fields ({best_count} fields):")
        print(f"Record from {len(portal_records)} filtered results:")
        
        # Display the best record using the detailed display function
        display_detailed_record(best_record, 1)

def validate_csv_entries(csv_path: Path, filter_institutions: bool = True):
    """Validate entries in CSV by searching for collector, date, and collection ID combinations"""
    print(f"\n=== Validating entries in {csv_path.name} ===")
    
    if filter_institutions:
        print("Filtering results to institutions: F, TENN, MICH, NY")
    else:
        print("Including all institutions")
    
    with open(csv_path, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    
    # Find relevant columns for search criteria
    collector_cols = ['collectedby', 'collector', 'recordedby', 'recorded_by']
    date_cols = ['minimumeventdate', 'minimum_event_date', 'date', 'eventdate', 'event_date', 'collection_date', 'collectiondate']
    collid_cols = ['recordnumber', 'record_number', 'collid', 'collection_id', 'collectionid']
    
    collector_col = None
    date_col = None
    collid_col = None
    
    # Find matching columns (case insensitive)
    for col in fieldnames:
        col_lower = col.lower()
        if not collector_col and col_lower in collector_cols:
            collector_col = col
        if not date_col and col_lower in date_cols:
            date_col = col
        if not collid_col and col_lower in collid_cols:
            collid_col = col
    
    if not any([collector_col, date_col, collid_col]):
        print("Warning: No suitable columns found for validation")
        return
    
    print(f"Using columns - Collector: {collector_col}, Date: {date_col}, CollID: {collid_col}")
    
    # Extract unique search combinations
    search_combinations = []
    for row in rows:
        collector = row.get(collector_col, '').strip() if collector_col else ''
        date = row.get(date_col, '').strip() if date_col else ''
        collid = row.get(collid_col, '').strip() if collid_col else ''
        
        # Only search if at least one field has data
        if any([collector and collector != "N/A", date and date != "N/A", collid and collid != "N/A"]):
            combo = (collector, date, collid)
            if combo not in search_combinations:
                search_combinations.append(combo)
    
    if not search_combinations:
        print("No valid search combinations found")
        return
    
    print(f"Checking {len(search_combinations)} unique search combinations...")
    
    # Check each combination for entries
    entry_results = {}
    best_records = {}  # Store best record for each combination
    entries_found = False
    
    for collector, date, collid in search_combinations:
        combo_key = f"{collector}|{date}|{collid}"
        print(f"  Checking: Collector='{collector}', Date='{date}', CollID='{collid}'")
        
        portal_records = search_portal_by_criteria(collector, date, collid, filter_institutions)
        entry_info = extract_entry_info(portal_records)
        entry_results[combo_key] = entry_info
        
        # Store the best record for this combination
        if portal_records and len(portal_records) > 0:
            best_record, best_count = find_best_record(portal_records)
            best_records[combo_key] = best_record
        
        if entry_info["EntriesFound"] == "Yes":
            entries_found = True
            count = entry_info["EntryCount"]
            print(f"    → ENTRIES FOUND: {count} record(s)")
            
            # Display the best record for this entry
            best_record, best_count = find_best_record(portal_records)
            if best_record:
                print(f"      Best record (most populated fields: {best_count}):")
                print(f"        occid: {best_record.get('occid', 'N/A')}")
                print(f"        collid: {best_record.get('collid', 'N/A')}")
                print(f"        occurrenceID: {best_record.get('occurrenceID', 'N/A')}")
                print(f"        catalogNumber: {best_record.get('catalogNumber', 'N/A')}")
                print(f"        otherCatalogNumbers: {best_record.get('otherCatalogNumbers', 'N/A')}")
                print(f"        ownerInstitutionCode: {best_record.get('ownerInstitutionCode', 'N/A')}")
                print(f"        verbatimCollectors: {best_record.get('recordedBy', 'N/A')}")  # Using recordedBy as closest match
                print(f"        collectedBy: {best_record.get('recordedBy', 'N/A')}")
                print(f"        secondaryCollectors: {best_record.get('associatedCollectors', 'N/A')}")
                print(f"        recordNumber: {best_record.get('recordNumber', 'N/A')}")
                print(f"        verbatimEventDate: {best_record.get('verbatimEventDate', 'N/A')}")
                print(f"        minimumEventDate: {best_record.get('eventDate', 'N/A')}")  # Using eventDate as closest match
                print(f"        maximumEventDate: {best_record.get('eventDate2', 'N/A')}")  # Using eventDate2 as closest match
                print(f"        verbatimIdentification: {best_record.get('sciname', 'N/A')}")  # Using sciname as closest match
                print(f"        latestScientificName: {best_record.get('sciname', 'N/A')}")
                print(f"        identifiedBy: {best_record.get('identifiedBy', 'N/A')}")
                print(f"        verbatimDateIdentified: {best_record.get('dateIdentified', 'N/A')}")
                print(f"        associatedTaxa: {best_record.get('associatedTaxa', 'N/A')}")
                print(f"        country: {best_record.get('country', 'N/A')}")
                print(f"        firstPoliticalUnit: {best_record.get('stateProvince', 'N/A')}")  # Using stateProvince as closest match
                print(f"        secondPoliticalUnit: {best_record.get('county', 'N/A')}")  # Using county as closest match
                print(f"        municipality: {best_record.get('municipality', 'N/A')}")
                print(f"        verbatimLocality: {best_record.get('locality', 'N/A')}")  # Using locality as closest match
                print(f"        locality: {best_record.get('locality', 'N/A')}")
                print(f"        habitat: {best_record.get('habitat', 'N/A')}")
                print(f"        verbatimElevation: {best_record.get('verbatimElevation', 'N/A')}")
                print(f"        verbatimCoordinates: {best_record.get('verbatimCoordinates', 'N/A')}")
                print(f"        otherCatalogNumbers: {best_record.get('otherCatalogNumbers', 'N/A')}")
                print(f"        originalMethod: {best_record.get('dynamicProperties', 'N/A')}")  # Using dynamicProperties as closest match
                print(f"        typeStatus: {best_record.get('typeStatus', 'N/A')}")
                print("      " + "-" * 30)
        else:
            print(f"    → No entries found")
    
    # Get field mapping
    field_mapping = get_field_mapping()
    
    # Build new fieldnames with verified fields inserted after each original field
    new_fieldnames = []
    verified_fields_added = []
    
    for field in fieldnames:
        new_fieldnames.append(field)
        # Check if this field has a mapping to portal data
        if field in field_mapping:
            verified_field = f"Verified{field}"
            new_fieldnames.append(verified_field)
            verified_fields_added.append(verified_field)
    
    # Add the basic tracking columns at the end
    new_fieldnames.extend(['EntriesFound', 'EntryCount', 'PortalInstitution'])
    
    # Update CSV with entry information and verified fields
    with open(csv_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
        writer.writeheader()
        
        for row in rows:
            collector = row.get(collector_col, '').strip() if collector_col else ''
            date = row.get(date_col, '').strip() if date_col else ''
            collid = row.get(collid_col, '').strip() if collid_col else ''
            combo_key = f"{collector}|{date}|{collid}"
            
            # Add verified fields from best record if available
            if combo_key in best_records:
                best_record = best_records[combo_key]
                for csv_field, portal_field in field_mapping.items():
                    if csv_field in fieldnames:
                        verified_field = f"Verified{csv_field}"
                        portal_value = best_record.get(portal_field, 'N/A')
                        # Handle None values
                        if portal_value is None or str(portal_value).strip() == '':
                            portal_value = 'N/A'
                        row[verified_field] = portal_value
            else:
                # No records found, set all verified fields to N/A
                for verified_field in verified_fields_added:
                    row[verified_field] = 'N/A'
            
            # Add entry tracking fields
            if combo_key in entry_results:
                info = entry_results[combo_key]
                row['EntriesFound'] = info.get('EntriesFound', 'No')
                row['EntryCount'] = info.get('EntryCount', '0')
            else:
                row['EntriesFound'] = "No"
                row['EntryCount'] = "0"
            
            # Add institution from best record
            if combo_key in best_records:
                best_record = best_records[combo_key]
                institution = best_record.get('institutionCode', 'N/A')
                if institution is None or str(institution).strip() == '':
                    institution = 'N/A'
                row['PortalInstitution'] = institution
            else:
                row['PortalInstitution'] = 'N/A'
            
            writer.writerow(row)
    
    total_entries = sum(1 for info in entry_results.values() if info["EntriesFound"] == "Yes")
    institution_filter_msg = " (filtered to F, TENN, MICH, NY)" if filter_institutions else " (all institutions)"
    print(f"✓ Entry validation completed. Found {total_entries} combinations with entries out of {len(search_combinations)} checked{institution_filter_msg}")
    print(f"  Results added to {csv_path.name}")
    print(f"  Added {len(verified_fields_added)} verified fields + EntriesFound, EntryCount, PortalInstitution columns")

def main():
    if len(sys.argv) == 1:
        # Interactive mode - no command line arguments
        search_entries_interactive()
    elif len(sys.argv) == 2:
        # CSV validation mode
        csv_path = Path(sys.argv[1])
        if not csv_path.exists():
            print(f"Error: CSV file not found at {csv_path}")
            sys.exit(1)
        
        validate_csv_entries(csv_path)
    elif len(sys.argv) == 3:
        # CSV validation mode with institution filter option
        csv_path = Path(sys.argv[1])
        filter_option = sys.argv[2].lower()
        
        if not csv_path.exists():
            print(f"Error: CSV file not found at {csv_path}")
            sys.exit(1)
        
        if filter_option in ['--no-filter', '--all-institutions']:
            validate_csv_entries(csv_path, filter_institutions=False)
        elif filter_option in ['--filter', '--target-institutions']:
            validate_csv_entries(csv_path, filter_institutions=True)
        else:
            print("Error: Invalid filter option. Use --filter/--target-institutions or --no-filter/--all-institutions")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python find_duplicate_entries.py                                          # Interactive search")
        print("  python find_duplicate_entries.py <csv_file_path>                          # CSV validation (default: filter to F, TENN, MICH, NY)")
        print("  python find_duplicate_entries.py <csv_file_path> --filter                 # CSV validation (filter to F, TENN, MICH, NY)")
        print("  python find_duplicate_entries.py <csv_file_path> --no-filter              # CSV validation (include all institutions)")
        print("  python find_duplicate_entries.py <csv_file_path> --target-institutions    # CSV validation (filter to F, TENN, MICH, NY)")
        print("  python find_duplicate_entries.py <csv_file_path> --all-institutions       # CSV validation (include all institutions)")
        sys.exit(1)

if __name__ == "__main__":
    main()
