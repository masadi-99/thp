#!/usr/bin/env python3
"""
Script to show exactly where specific codes appear in the JSON files.
"""

import json
import os

def find_code_in_file(file_path, hospital_name, target_codes):
    """Find specific codes in a hospital file and show exact JSON structure"""
    print(f"\n{'='*80}")
    print(f"SEARCHING IN: {hospital_name}")
    print(f"File: {file_path}")
    print(f"{'='*80}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get('standard_charge_information', [])
        print(f"📊 Total items in file: {len(items)}")
        
        found_codes = {}
        
        for i, item in enumerate(items):
            # Check if this item has any of our target codes
            if 'code_information' in item:
                for code_info in item['code_information']:
                    if 'code' in code_info and 'type' in code_info:
                        code_value = str(code_info['code']).strip()
                        code_type = str(code_info['type']).strip()
                        
                        # Check if this matches any of our target codes
                        for target_code in target_codes:
                            if code_type == 'NDC' and code_value == target_code:
                                found_codes[target_code] = {
                                    'item_index': i,
                                    'full_item': item
                                }
        
        # Show results
        for target_code in target_codes:
            if target_code in found_codes:
                item_data = found_codes[target_code]
                item = item_data['full_item']
                index = item_data['item_index']
                
                print(f"\n✅ FOUND: NDC {target_code} at index {index}")
                print(f"📝 Description: {item.get('description', 'N/A')}")
                
                # Show the exact JSON structure
                print(f"\n📋 EXACT JSON STRUCTURE:")
                print("-" * 60)
                print(json.dumps(item, indent=2)[:2000] + "..." if len(json.dumps(item, indent=2)) > 2000 else json.dumps(item, indent=2))
                print("-" * 60)
                
                # Extract and show price information
                if 'standard_charges' in item:
                    print(f"\n💰 PRICING INFORMATION:")
                    for j, charge in enumerate(item['standard_charges']):
                        if 'gross_charge' in charge:
                            print(f"  Charge {j+1}: {charge.get('gross_charge', 'N/A')}")
                            if 'setting' in charge:
                                print(f"    Setting: {charge['setting']}")
                            if 'payer_specific_negotiated_charge' in charge:
                                print(f"    Negotiated: {charge['payer_specific_negotiated_charge']}")
                
            else:
                print(f"\n❌ NOT FOUND: NDC {target_code}")
        
    except Exception as e:
        print(f"❌ Error processing {hospital_name}: {e}")

def main():
    # The 3 examples we found
    target_codes = [
        "61314022705",  # TIMOLOL MALEATE 0.5 % EYE DROPS
        "16729011408",  # ETOPOSIDE (UNDILUTED) CHEMO INFUSION  
        "00264987210"   # HEPARIN (PORCINE) (PF) 1,000 UNIT/500 ML IN 0.9 % SODIUM CHLORIDE IV
    ]
    
    hospital_files = [
        ('106010776_ucsf-medical-center_standardcharges.json', 'UCSF Medical Center'),
        ('946174066_stanford-health-care_standardcharges.json', 'Stanford Health Care'),
        ('_sites_default_files_cms-hpt_956006143_ronald-reagan-ucla-medical-center_standardcharges.json', 'UCLA Health'),
        ('951644600_CEDARS-SINAI-MEDICAL-CENTER_STANDARDCHARGES.json', 'Cedars-Sinai Medical Center')
    ]
    
    print("🔍 SEARCHING FOR SPECIFIC NDC CODES IN ALL HOSPITAL FILES")
    print("Target codes:")
    for i, code in enumerate(target_codes, 1):
        print(f"  {i}. NDC {code}")
    
    # Search each hospital file
    for file_path, hospital_name in hospital_files:
        find_code_in_file(file_path, hospital_name, target_codes)
    
    print(f"\n{'='*80}")
    print("SEARCH COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    main() 