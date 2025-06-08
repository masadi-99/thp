#!/usr/bin/env python3

from stanford_dataset_builder import build_stanford_dataset

print("🏥 STANFORD HOSPITAL DATASET SUMMARY")
print("=" * 80)

dataset = build_stanford_dataset()

if dataset:
    print(f"\n💊 SAMPLE NDC CODES IN STANFORD:")
    ndc_codes = dataset.get_all_codes_of_type('NDC')[:5]
    for ndc in ndc_codes:
        items = dataset.find_by_code(ndc, 'NDC')
        if items:
            item = items[0]
            print(f"   ✅ NDC {ndc}:")
            print(f"      {item['description']}")
            print(f"      Price: ${item['prices'][0]['gross_charge']:.2f}")

    print(f"\n🔍 CODE COUNTING CAPABILITIES:")
    print(f"   HCPCS items: {dataset.count_by_code_type('HCPCS'):,}")
    print(f"   NDC items: {dataset.count_by_code_type('NDC'):,}")
    print(f"   CPT items: {dataset.count_by_code_type('CPT'):,}")
    print(f"   CDM items: {dataset.count_by_code_type('CDM'):,}")

    print(f"\n🎯 SEARCH EXAMPLES:")
    insulin_items = dataset.search_by_keywords('insulin')
    print(f"   'insulin': {len(insulin_items)} results")
    if insulin_items:
        item = insulin_items[0]
        print(f"      Example: {item['description']}")
        print(f"      Price: ${item['prices'][0]['gross_charge']:.2f}")

    mri_items = dataset.search_by_keywords('mri')
    print(f"   'mri': {len(mri_items)} results") 
    if mri_items:
        item = mri_items[0]
        print(f"      Example: {item['description']}")
        print(f"      Price: ${item['prices'][0]['gross_charge']:.2f}")

    print(f"\n✅ DATASET READY!")
    print(f"   • Total items: {len(dataset.items):,}")
    print(f"   • Easy lookups by code")
    print(f"   • Fast counting by code type")
    print(f"   • Full-text search")
    print(f"   • Ready for Flask app!") 