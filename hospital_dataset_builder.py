#!/usr/bin/env python3
"""
Hospital Dataset Builder - Generalized for all hospitals
Creates comprehensive hashmap/datasets for fast lookups and analysis.
"""

import json
import os
import pickle
from collections import defaultdict, Counter
import re

class HospitalDataset:
    def __init__(self, hospital_name):
        self.hospital_name = hospital_name
        self.items = []  # Main list of all items
        self.code_to_indices = defaultdict(list)  # code -> [item_indices]
        self.description_to_indices = defaultdict(list)  # description -> [item_indices]
        self.code_type_stats = Counter()  # code_type -> count
        self.word_index = defaultdict(set)  # word -> {item_indices} for search
        
    def add_item(self, item_data):
        """Add an item to the dataset with all indexes"""
        item_index = len(self.items)
        self.items.append(item_data)
        
        # Index by all codes
        for code_info in item_data.get('codes', []):
            code_value = code_info['code']
            code_type = code_info['type']
            
            # Create searchable key for this code
            code_key = f"{code_type}:{code_value}"
            self.code_to_indices[code_key].append(item_index)
            self.code_to_indices[code_value].append(item_index)  # Also index by code value alone
            
            # Count code types
            self.code_type_stats[code_type] += 1
        
        # Index by description
        description = item_data.get('description', '').strip()
        if description:
            self.description_to_indices[description.lower()].append(item_index)
            
            # Create word index for searching
            words = re.findall(r'\w+', description.lower())
            for word in words:
                if len(word) >= 3:  # Only index words 3+ chars
                    self.word_index[word].add(item_index)
    
    def find_by_code(self, code_value, code_type=None):
        """Find items by code value, optionally filtered by code type"""
        if code_type:
            code_key = f"{code_type}:{code_value}"
            indices = self.code_to_indices.get(code_key, [])
        else:
            indices = self.code_to_indices.get(code_value, [])
        
        return [self.items[i] for i in indices]
    
    def find_by_description(self, description):
        """Find items by exact description match"""
        indices = self.description_to_indices.get(description.lower(), [])
        return [self.items[i] for i in indices]
    
    def search_by_keywords(self, keywords):
        """Search items by keywords in description"""
        if isinstance(keywords, str):
            keywords = keywords.split()
        
        # Find items that contain ALL keywords
        matching_indices = None
        for keyword in keywords:
            keyword = keyword.lower().strip()
            if len(keyword) >= 3:
                keyword_indices = self.word_index.get(keyword, set())
                if matching_indices is None:
                    matching_indices = keyword_indices.copy()
                else:
                    matching_indices &= keyword_indices
        
        if matching_indices:
            return [self.items[i] for i in matching_indices]
        return []
    
    def count_by_code_type(self, code_type):
        """Count how many items have a specific code type"""
        return self.code_type_stats.get(code_type, 0)
    
    def get_code_type_stats(self):
        """Get statistics about all code types"""
        return dict(self.code_type_stats)
    
    def get_all_codes_of_type(self, code_type):
        """Get all unique codes of a specific type"""
        codes = set()
        for code_key in self.code_to_indices.keys():
            if ':' in code_key and code_key.startswith(f"{code_type}:"):
                codes.add(code_key.split(':', 1)[1])
        return sorted(list(codes))
    
    def get_stats(self):
        """Get comprehensive dataset statistics"""
        return {
            'hospital_name': self.hospital_name,
            'total_items': len(self.items),
            'total_unique_codes': len([k for k in self.code_to_indices.keys() if ':' not in k]),
            'code_type_counts': dict(self.code_type_stats),
            'searchable_words': len(self.word_index),
            'unique_descriptions': len(self.description_to_indices)
        }

# Hospital file mappings
HOSPITAL_FILES = {
    'stanford': '946174066_stanford-health-care_standardcharges.json',
    'ucsf': '106010776_ucsf-medical-center_standardcharges.json',
    'ucla': '_sites_default_files_cms-hpt_956006143_ronald-reagan-ucla-medical-center_standardcharges.json',
    'cedars': '951644600_CEDARS-SINAI-MEDICAL-CENTER_STANDARDCHARGES.json'
}

HOSPITAL_NAMES = {
    'stanford': 'Stanford Health Care',
    'ucsf': 'UCSF Medical Center',
    'ucla': 'UCLA Health',
    'cedars': 'Cedars-Sinai Medical Center'
}

def build_hospital_dataset(hospital_key):
    """Build dataset for a specific hospital"""
    if hospital_key not in HOSPITAL_FILES:
        print(f"❌ Unknown hospital: {hospital_key}")
        print(f"Available hospitals: {list(HOSPITAL_FILES.keys())}")
        return None
        
    file_path = HOSPITAL_FILES[hospital_key]
    hospital_name = HOSPITAL_NAMES[hospital_key]
    
    print(f"🏥 Building {hospital_name} Dataset...")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None
    
    # Load JSON data
    print("📂 Loading JSON data...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    items = data.get('standard_charge_information', [])
    print(f"📊 Found {len(items)} items in {hospital_name} data")
    
    # Build dataset
    dataset = HospitalDataset(hospital_name)
    
    processed_count = 0
    skipped_count = 0
    
    for i, item in enumerate(items):
        if i % 10000 == 0:
            print(f"  Processing {i}/{len(items)}...")
        
        description = item.get('description', '').strip()
        if not description:
            skipped_count += 1
            continue
        
        # Extract codes
        codes = []
        if 'code_information' in item:
            for code_info in item['code_information']:
                if 'code' in code_info and 'type' in code_info:
                    code_value = str(code_info['code']).strip()
                    code_type = str(code_info['type']).strip()
                    if code_value and code_type:
                        codes.append({
                            'code': code_value,
                            'type': code_type
                        })
        
        # Extract pricing
        prices = []
        if 'standard_charges' in item:
            for charge in item['standard_charges']:
                if 'gross_charge' in charge:
                    try:
                        price = float(str(charge['gross_charge']).replace('$', '').replace(',', ''))
                        if price > 0:
                            prices.append({
                                'gross_charge': price,
                                'setting': charge.get('setting', 'unknown'),
                                'discounted_cash': charge.get('discounted_cash'),
                                'billing_class': charge.get('billing_class')
                            })
                    except (ValueError, TypeError):
                        continue
        
        # Only include items with codes AND prices
        if codes and prices:
            item_data = {
                'index': i,
                'description': description,
                'codes': codes,
                'prices': prices,
                'drug_info': item.get('drug_information', {}),
                'original_item': item  # Keep reference to original
            }
            
            dataset.add_item(item_data)
            processed_count += 1
    
    print(f"✅ Dataset built successfully!")
    print(f"   Processed: {processed_count} items")
    print(f"   Skipped: {skipped_count} items")
    
    # Show statistics
    stats = dataset.get_stats()
    print(f"\n📈 DATASET STATISTICS:")
    print(f"   Hospital: {stats['hospital_name']}")
    print(f"   Total Items: {stats['total_items']:,}")
    print(f"   Unique Codes: {stats['total_unique_codes']:,}")
    print(f"   Searchable Words: {stats['searchable_words']:,}")
    print(f"   Unique Descriptions: {stats['unique_descriptions']:,}")
    
    print(f"\n🏷️  CODE TYPE BREAKDOWN:")
    for code_type, count in sorted(stats['code_type_counts'].items()):
        print(f"   {code_type}: {count:,} items")
    
    return dataset

def save_hospital_dataset(dataset, hospital_key):
    """Save hospital dataset to pickle file"""
    filename = f"{hospital_key}_dataset.pkl"
    print(f"💾 Saving {dataset.hospital_name} dataset to {filename}...")
    with open(filename, 'wb') as f:
        pickle.dump(dataset, f)
    print("✅ Dataset saved!")

def load_hospital_dataset(hospital_key):
    """Load hospital dataset from pickle file"""
    filename = f"{hospital_key}_dataset.pkl"
    if not os.path.exists(filename):
        return None
    
    print(f"📂 Loading {HOSPITAL_NAMES[hospital_key]} dataset from {filename}...")
    with open(filename, 'rb') as f:
        dataset = pickle.load(f)
    print("✅ Dataset loaded!")
    return dataset

def test_hospital_dataset(dataset, hospital_key):
    """Test hospital dataset functionality"""
    print(f"\n🧪 TESTING {dataset.hospital_name.upper()} DATASET:")
    print("=" * 80)
    
    # Test 1: Code type statistics
    print(f"\n📊 CODE TYPE STATISTICS:")
    stats = dataset.get_code_type_stats()
    for code_type, count in sorted(stats.items()):
        print(f"   {code_type}: {count:,} items")
    
    # Test 2: Sample NDC codes
    ndc_codes = dataset.get_all_codes_of_type('NDC')[:5]
    if ndc_codes:
        print(f"\n💊 SAMPLE NDC CODES:")
        for ndc_code in ndc_codes:
            items = dataset.find_by_code(ndc_code, 'NDC')
            if items:
                item = items[0]
                print(f"   ✅ NDC {ndc_code}:")
                print(f"      {item['description'][:60]}...")
                print(f"      Price: ${item['prices'][0]['gross_charge']:.2f}")
    
    # Test 3: Search capabilities
    print(f"\n🔍 SEARCH TESTS:")
    test_keywords = ['insulin', 'mri', 'ct', 'surgery']
    for keyword in test_keywords:
        results = dataset.search_by_keywords(keyword)
        print(f"   '{keyword}': {len(results)} results")
        if results and len(results) > 0:
            example = results[0]
            print(f"      Example: {example['description'][:50]}... ${example['prices'][0]['gross_charge']:.2f}")
    
    # Test 4: Overall stats
    print(f"\n📈 FINAL STATISTICS:")
    all_stats = dataset.get_stats()
    print(f"   Hospital: {all_stats['hospital_name']}")
    print(f"   Total Items: {all_stats['total_items']:,}")
    print(f"   NDC Codes: {dataset.count_by_code_type('NDC'):,}")
    print(f"   HCPCS Codes: {dataset.count_by_code_type('HCPCS'):,}")
    print(f"   CPT Codes: {dataset.count_by_code_type('CPT'):,}")

def main():
    """Main function to build and test all hospitals"""
    hospitals = ['stanford', 'ucsf', 'ucla', 'cedars']
    
    for hospital_key in hospitals:
        print(f"\n{'='*100}")
        print(f"PROCESSING {HOSPITAL_NAMES[hospital_key].upper()}")
        print(f"{'='*100}")
        
        # Try to load existing dataset first
        dataset = load_hospital_dataset(hospital_key)
        
        if dataset is None:
            # Build new dataset
            dataset = build_hospital_dataset(hospital_key)
            if dataset:
                save_hospital_dataset(dataset, hospital_key)
        
        if dataset:
            # Test the dataset
            test_hospital_dataset(dataset, hospital_key)
        
        print(f"\n✅ {HOSPITAL_NAMES[hospital_key]} dataset ready!")

if __name__ == "__main__":
    main() 