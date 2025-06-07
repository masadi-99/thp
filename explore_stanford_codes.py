#!/usr/bin/env python3
"""
Explore actual codes in Stanford dataset
"""

from stanford_dataset_builder import load_dataset

def main():
    print("🔍 EXPLORING ACTUAL CODES IN STANFORD DATASET")
    print("=" * 80)
    
    dataset = load_dataset()
    if not dataset:
        print("❌ Dataset not found!")
        return
    
    # Get actual NDC codes that exist
    print(f"\n💊 ACTUAL NDC CODES IN STANFORD:")
    ndc_codes = dataset.get_all_codes_of_type('NDC')[:10]  # First 10
    
    for ndc_code in ndc_codes:
        items = dataset.find_by_code(ndc_code, 'NDC')
        if items:
            item = items[0]
            print(f"   ✅ NDC {ndc_code}:")
            print(f"      {item['description']}")
            print(f"      Price: ${item['prices'][0]['gross_charge']:.2f}")
    
    # Show count statistics
    print(f"\n📊 CODE DISTRIBUTION:")
    stats = dataset.get_code_type_stats()
    for code_type, count in sorted(stats.items()):
        print(f"   {code_type}: {count:,} items")
        
        # Show sample codes for each type
        sample_codes = dataset.get_all_codes_of_type(code_type)[:3]
        for code in sample_codes:
            items = dataset.find_by_code(code, code_type)
            if items:
                print(f"      Example {code}: {items[0]['description'][:40]}...")
    
    # Test specific lookups
    print(f"\n🎯 TESTING FAST LOOKUPS:")
    
    # Find items by CDM (all items should have CDM)
    cdm_codes = dataset.get_all_codes_of_type('CDM')[:3]
    for cdm_code in cdm_codes:
        items = dataset.find_by_code(cdm_code, 'CDM')
        print(f"   CDM {cdm_code}: {len(items)} item(s)")
        if items:
            print(f"      {items[0]['description'][:50]}...")
    
    # Find insulin items (should have many)
    insulin_items = dataset.search_by_keywords('insulin')
    print(f"\n💉 INSULIN ITEMS FOUND: {len(insulin_items)}")
    for i, item in enumerate(insulin_items[:5]):
        print(f"   {i+1}. {item['description'][:50]}...")
        codes_list = [f"{c['type']}:{c['code']}" for c in item['codes'][:2]]
        print(f"      Codes: {', '.join(codes_list)}")
        print(f"      Price: ${item['prices'][0]['gross_charge']:.2f}")
    
    print(f"\n✅ STANFORD DATASET SUMMARY:")
    print(f"   • {len(dataset.items):,} total items with codes and prices")
    print(f"   • {len(ndc_codes):,} unique NDC codes")
    print(f"   • Fast lookup by any code type")
    print(f"   • Full-text search capabilities")
    print(f"   • Ready for Flask app integration")

if __name__ == "__main__":
    main() 