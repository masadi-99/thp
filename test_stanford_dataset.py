#!/usr/bin/env python3
"""
Test Stanford Dataset - Demonstrate easy lookups and counting
"""

from stanford_dataset_builder import load_dataset, StanfordDataset
import pickle
import os

def load_stanford_dataset(filename='stanford_dataset.pkl'):
    """Load dataset properly"""
    if not os.path.exists(filename):
        return None
    
    print(f"📂 Loading dataset from {filename}...")
    with open(filename, 'rb') as f:
        dataset = pickle.load(f)
    print("✅ Dataset loaded!")
    return dataset

def main():
    print("🧪 TESTING STANFORD DATASET CAPABILITIES")
    print("=" * 80)
    
    # Load the dataset
    dataset = load_stanford_dataset()
    if not dataset:
        print("❌ Dataset not found! Run stanford_dataset_builder.py first")
        return
    
    print(f"✅ Dataset loaded with {len(dataset.items):,} items")
    
    # DEMO 1: Easy code counting
    print(f"\n📊 CODE TYPE COUNTING:")
    print(f"   HCPCS codes: {dataset.count_by_code_type('HCPCS'):,}")
    print(f"   NDC codes: {dataset.count_by_code_type('NDC'):,}")
    print(f"   CPT codes: {dataset.count_by_code_type('CPT'):,}")
    print(f"   CDM codes: {dataset.count_by_code_type('CDM'):,}")
    print(f"   RC codes: {dataset.count_by_code_type('RC'):,}")
    print(f"   LOCAL codes: {dataset.count_by_code_type('LOCAL'):,}")
    
    # DEMO 2: Find specific NDC codes
    print(f"\n💊 FINDING SPECIFIC NDC CODES:")
    test_ndc_codes = ['61314022705', '16729011408', '00264987210']
    
    for ndc_code in test_ndc_codes:
        items = dataset.find_by_code(ndc_code, 'NDC')
        if items:
            item = items[0]  # Should only be one
            print(f"   ✅ NDC {ndc_code}:")
            print(f"      Description: {item['description']}")
            print(f"      Prices: {[p['gross_charge'] for p in item['prices']]}")
        else:
            print(f"   ❌ NDC {ndc_code}: Not found")
    
    # DEMO 3: Find by description keywords
    print(f"\n🔍 SEARCHING BY KEYWORDS:")
    keywords = ['insulin', 'timolol', 'heparin', 'mri brain', 'ct scan']
    
    for keyword in keywords:
        results = dataset.search_by_keywords(keyword)
        print(f"   '{keyword}': {len(results)} results")
        if results:
            # Show first 2 examples
            for i, item in enumerate(results[:2]):
                print(f"      {i+1}. {item['description'][:60]}...")
                codes_str = [f"{c['type']}:{c['code']}" for c in item['codes'][:3]]
                print(f"         Codes: {codes_str}")
                print(f"         Price: ${item['prices'][0]['gross_charge']:.2f}")
    
    # DEMO 4: Find all items with specific HCPCS codes
    print(f"\n🏥 SAMPLE HCPCS CODE LOOKUPS:")
    hcpcs_codes = dataset.get_all_codes_of_type('HCPCS')[:5]  # First 5
    
    for hcpcs_code in hcpcs_codes:
        items = dataset.find_by_code(hcpcs_code, 'HCPCS')
        print(f"   HCPCS {hcpcs_code}: {len(items)} item(s)")
        if items:
            item = items[0]
            print(f"      {item['description'][:60]}...")
            print(f"      Price: ${item['prices'][0]['gross_charge']:.2f}")
    
    # DEMO 5: Show items with multiple code types
    print(f"\n📋 ITEMS WITH MULTIPLE CODE TYPES:")
    multi_code_count = 0
    for item in dataset.items:
        code_types = set(code['type'] for code in item['codes'])
        if len(code_types) >= 3:  # Items with 3+ different code types
            print(f"   {item['description'][:50]}...")
            for code in item['codes']:
                print(f"      {code['type']}: {code['code']}")
            print(f"      Price: ${item['prices'][0]['gross_charge']:.2f}")
            multi_code_count += 1
            if multi_code_count >= 3:
                break
    
    # DEMO 6: Statistics summary
    print(f"\n📈 FINAL STATISTICS:")
    stats = dataset.get_stats()
    print(f"   Total Items: {stats['total_items']:,}")
    print(f"   Items with NDC codes: {dataset.count_by_code_type('NDC'):,}")
    print(f"   Items with HCPCS codes: {dataset.count_by_code_type('HCPCS'):,}")
    print(f"   Items with CPT codes: {dataset.count_by_code_type('CPT'):,}")
    print(f"   Unique searchable words: {stats['searchable_words']:,}")
    
    print(f"\n✅ DATASET IS READY FOR FLASK INTEGRATION!")
    print(f"   • Fast code lookups: dataset.find_by_code('12345', 'NDC')")
    print(f"   • Easy counting: dataset.count_by_code_type('HCPCS')")
    print(f"   • Keyword search: dataset.search_by_keywords('insulin')")
    print(f"   • Get all codes: dataset.get_all_codes_of_type('NDC')")

if __name__ == "__main__":
    main() 