#!/usr/bin/env python3
"""
Analyze NDC code formats across hospitals to understand overlaps
"""

from hospital_dataset_builder import load_hospital_dataset, HOSPITAL_NAMES
import re

def normalize_ndc(ndc_code):
    """Normalize NDC codes by removing separators and padding"""
    # Remove all non-digits
    digits_only = re.sub(r'\D', '', str(ndc_code))
    
    # NDC codes should be 10-11 digits, pad to 11 if needed
    if len(digits_only) >= 9 and len(digits_only) <= 11:
        # Pad to 11 digits
        return digits_only.zfill(11)
    return None

def analyze_ndc_formats():
    print("🔍 ANALYZING NDC CODE FORMATS ACROSS HOSPITALS")
    print("=" * 80)
    
    hospitals = ['stanford', 'ucsf', 'ucla', 'cedars']
    datasets = {}
    
    # Load all datasets
    for hospital_key in hospitals:
        dataset = load_hospital_dataset(hospital_key)
        if dataset:
            datasets[hospital_key] = dataset
    
    # Analyze NDC format patterns
    for hospital_key, dataset in datasets.items():
        print(f"\n📊 {dataset.hospital_name.upper()} NDC ANALYSIS:")
        print("-" * 60)
        
        ndc_codes = dataset.get_all_codes_of_type('NDC')
        print(f"Total NDC codes: {len(ndc_codes):,}")
        
        # Show sample formats
        print("Sample NDC formats:")
        formats = {}
        for i, ndc in enumerate(ndc_codes[:10]):
            pattern = "".join(['D' if c.isdigit() else c for c in ndc])
            if pattern not in formats:
                formats[pattern] = []
            formats[pattern].append(ndc)
        
        for pattern, examples in formats.items():
            print(f"   {pattern}: {examples[:3]} (and {len(examples)-3} more)" if len(examples) > 3 else f"   {pattern}: {examples}")
        
        # Analyze lengths
        lengths = {}
        for ndc in ndc_codes:
            length = len(ndc)
            lengths[length] = lengths.get(length, 0) + 1
        
        print("NDC code lengths:")
        for length in sorted(lengths.keys()):
            print(f"   {length} chars: {lengths[length]:,} codes")
    
    # Test normalized overlaps
    print(f"\n🎯 TESTING NORMALIZED NDC OVERLAPS:")
    print("=" * 80)
    
    normalized_sets = {}
    for hospital_key, dataset in datasets.items():
        ndc_codes = dataset.get_all_codes_of_type('NDC')
        normalized = set()
        for ndc in ndc_codes:
            norm_ndc = normalize_ndc(ndc)
            if norm_ndc:
                normalized.add(norm_ndc)
        normalized_sets[hospital_key] = normalized
        print(f"{dataset.hospital_name}: {len(normalized)} normalized NDC codes")
    
    # Find normalized overlaps
    print(f"\n🔍 NORMALIZED NDC OVERLAPS:")
    hospitals_list = list(normalized_sets.keys())
    
    for i in range(len(hospitals_list)):
        for j in range(i + 1, len(hospitals_list)):
            hosp1 = hospitals_list[i]
            hosp2 = hospitals_list[j]
            overlap = normalized_sets[hosp1] & normalized_sets[hosp2]
            print(f"   {HOSPITAL_NAMES[hosp1]} ∩ {HOSPITAL_NAMES[hosp2]}: {len(overlap)} common normalized NDC codes")
    
    # Find codes common to all hospitals (normalized)
    if len(normalized_sets) >= 3:
        all_common = set.intersection(*normalized_sets.values())
        print(f"\n   🌟 Common to ALL hospitals (normalized): {len(all_common)} NDC codes")
        
        if len(all_common) > 0:
            print(f"\n   Examples of universal normalized NDC codes:")
            for i, norm_ndc in enumerate(sorted(list(all_common))[:5]):
                print(f"      {i+1}. Normalized NDC: {norm_ndc}")
                
                # Find original codes and prices in each hospital
                for hospital_key, dataset in datasets.items():
                    ndc_codes = dataset.get_all_codes_of_type('NDC')
                    for original_ndc in ndc_codes:
                        if normalize_ndc(original_ndc) == norm_ndc:
                            items = dataset.find_by_code(original_ndc, 'NDC')
                            if items:
                                item = items[0]
                                price = item['prices'][0]['gross_charge']
                                print(f"         {dataset.hospital_name}: NDC {original_ndc} = ${price:.2f}")
                                print(f"           {item['description'][:50]}...")
                            break
                print()
    
    # Detailed insulin analysis
    print(f"\n💉 DETAILED INSULIN ANALYSIS:")
    print("=" * 80)
    
    insulin_data = {}
    for hospital_key, dataset in datasets.items():
        insulin_results = dataset.search_by_keywords('insulin')
        insulin_ndc_codes = []
        
        for item in insulin_results:
            for code_info in item['codes']:
                if code_info['type'] == 'NDC':
                    insulin_ndc_codes.append(code_info['code'])
        
        insulin_data[hospital_key] = {
            'total_insulin_items': len(insulin_results),
            'insulin_ndc_codes': set(insulin_ndc_codes),
            'dataset': dataset
        }
        
        print(f"{dataset.hospital_name}:")
        print(f"   Total insulin items: {len(insulin_results)}")
        print(f"   Unique insulin NDC codes: {len(set(insulin_ndc_codes))}")
    
    # Check insulin NDC overlaps
    print(f"\n🔍 INSULIN NDC OVERLAPS:")
    for i, hosp1 in enumerate(hospitals_list):
        for j in range(i + 1, len(hospitals_list)):
            hosp2 = hospitals_list[j]
            if hosp1 in insulin_data and hosp2 in insulin_data:
                overlap = insulin_data[hosp1]['insulin_ndc_codes'] & insulin_data[hosp2]['insulin_ndc_codes']
                print(f"   {HOSPITAL_NAMES[hosp1]} ∩ {HOSPITAL_NAMES[hosp2]}: {len(overlap)} common insulin NDC codes")
                if len(overlap) > 0:
                    for ndc in list(overlap)[:3]:
                        print(f"      Example: NDC {ndc}")

if __name__ == "__main__":
    analyze_ndc_formats() 