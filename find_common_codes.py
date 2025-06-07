#!/usr/bin/env python3
"""
Simple script to find codes that appear in all 4 hospitals.
This will help us identify real matches for comparison.
"""

import json
import os
import re
from collections import defaultdict

def normalize_code(code_value, code_type):
    """Normalize codes to catch format variations"""
    code = str(code_value).strip().upper()
    
    # Remove common separators and formatting
    code = re.sub(r'[-\s\.]', '', code)
    
    # For NDC codes, normalize to 11 digits
    if code_type.upper() in ['NDC']:
        code = re.sub(r'\D', '', code)  # Keep only digits
        if len(code) >= 9:  # Valid NDC should be at least 9 digits
            return f"NDC:{code}"
    
    # For other codes, just clean and normalize
    if len(code) >= 3:  # Minimum reasonable length
        return f"{code_type.upper()}:{code}"
    
    return None

def extract_codes_from_file(file_path, hospital_name):
    """Extract all codes from a hospital file"""
    print(f"Analyzing {hospital_name}...")
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get('standard_charge_information', [])
        print(f"  Found {len(items)} items")
        
        codes_to_items = {}
        
        for i, item in enumerate(items):
            if i % 10000 == 0:
                print(f"  Processing {i}/{len(items)}...")
            
            description = item.get('description', '').strip()
            if not description:
                continue
            
            # Extract codes
            if 'code_information' in item:
                for code_info in item['code_information']:
                    if 'code' in code_info and 'type' in code_info:
                        code_value = str(code_info['code']).strip()
                        code_type = str(code_info['type']).strip()
                        
                        if code_value and code_type:
                            # Try both original and normalized code
                            original_key = f"{code_type}:{code_value}"
                            normalized_key = normalize_code(code_value, code_type)
                            
                            # Extract price
                            price = None
                            if 'standard_charges' in item:
                                for charge in item['standard_charges']:
                                    if 'gross_charge' in charge and charge['gross_charge']:
                                        try:
                                            price = float(str(charge['gross_charge']).replace('$', '').replace(',', ''))
                                            if price > 0:
                                                break
                                        except (ValueError, TypeError):
                                            continue
                            
                            if price is not None and price > 0:
                                item_data = {
                                    'description': description,
                                    'code': code_value,
                                    'code_type': code_type,
                                    'price': price,
                                    'hospital': hospital_name
                                }
                                
                                # Store both original and normalized
                                codes_to_items[original_key] = item_data
                                if normalized_key and normalized_key != original_key:
                                    codes_to_items[normalized_key] = item_data
        
        print(f"  Extracted {len(codes_to_items)} valid codes with prices")
        return codes_to_items
        
    except Exception as e:
        print(f"Error processing {hospital_name}: {e}")
        return {}

def find_common_codes():
    """Find codes that appear in multiple hospitals"""
    
    hospital_files = [
        ('106010776_ucsf-medical-center_standardcharges.json', 'UCSF Medical Center'),
        ('946174066_stanford-health-care_standardcharges.json', 'Stanford Health Care'),
        ('_sites_default_files_cms-hpt_956006143_ronald-reagan-ucla-medical-center_standardcharges.json', 'UCLA Health'),
        ('951644600_CEDARS-SINAI-MEDICAL-CENTER_STANDARDCHARGES.json', 'Cedars-Sinai Medical Center')
    ]
    
    # Extract codes from each hospital
    all_hospitals_data = {}
    
    for file_path, hospital_name in hospital_files:
        codes_data = extract_codes_from_file(file_path, hospital_name)
        all_hospitals_data[hospital_name] = codes_data
    
    # Find codes that appear in multiple hospitals
    print(f"\n{'='*60}")
    print("FINDING COMMON CODES ACROSS HOSPITALS")
    print(f"{'='*60}")
    
    # Get all unique codes
    all_codes = set()
    for hospital_data in all_hospitals_data.values():
        all_codes.update(hospital_data.keys())
    
    print(f"Total unique codes across all hospitals: {len(all_codes)}")
    
    # Group by hospital count
    codes_by_hospital_count = {4: [], 3: [], 2: []}
    
    for code_key in all_codes:
        hospitals_with_code = []
        for hospital_name, hospital_data in all_hospitals_data.items():
            if code_key in hospital_data:
                hospitals_with_code.append(hospital_name)
        
        hospital_count = len(hospitals_with_code)
        if hospital_count >= 2:  # At least 2 hospitals
            # Get the data from each hospital
            code_data = []
            for hospital_name in hospitals_with_code:
                code_data.append(all_hospitals_data[hospital_name][code_key])
            
            codes_by_hospital_count[hospital_count].append({
                'code_key': code_key,
                'hospitals': code_data
            })
    
    # Report findings
    for count in [4, 3, 2]:
        codes = codes_by_hospital_count[count]
        print(f"Codes appearing in {count} hospitals: {len(codes)}")
    
    # Show examples
    for count in [4, 3, 2]:
        codes = codes_by_hospital_count[count]
        if codes:
            print(f"\n{'='*60}")
            print(f"EXAMPLES OF CODES IN {count} HOSPITALS")
            print(f"{'='*60}")
            
            # Show first few examples
            for i, common_code in enumerate(codes[:3]):
                code_key = common_code['code_key']
                hospitals = common_code['hospitals']
                
                print(f"\nExample {i+1}: {code_key}")
                print(f"Description: {hospitals[0]['description']}")
                print(f"Code Type: {hospitals[0]['code_type']}")
                print(f"Code Value: {hospitals[0]['code']}")
                print("Prices across hospitals:")
                
                prices = []
                for hospital_data in hospitals:
                    price = hospital_data['price']
                    prices.append(price)
                    print(f"  {hospital_data['hospital']}: ${price:,.2f}")
                
                if len(prices) > 1:
                    min_price = min(prices)
                    max_price = max(prices)
                    savings = max_price - min_price
                    savings_percent = (savings / max_price) * 100 if max_price > 0 else 0
                    print(f"  Potential Savings: ${savings:,.2f} ({savings_percent:.1f}%)")
                
                print("-" * 40)
            
            if codes:
                break  # Stop after showing the first group with results
    
    return codes_by_hospital_count

if __name__ == "__main__":
    codes_by_hospital_count = find_common_codes()
    
    total_matches = sum(len(codes) for codes in codes_by_hospital_count.values())
    if total_matches > 0:
        print(f"\n✅ SUCCESS: Found {total_matches} codes that appear in multiple hospitals!")
        print("These are candidates for price comparison.")
    else:
        print("\n❌ No codes found that appear in multiple hospitals.")
        print("The hospitals may use completely different coding systems.") 