#!/usr/bin/env python3

from stanford_dataset_builder import load_dataset

dataset = load_dataset()
print(f'✅ Stanford Dataset: {len(dataset.items):,} items')

print(f'\n💊 SAMPLE NDC CODES:')
ndc_codes = dataset.get_all_codes_of_type('NDC')[:5]
for ndc in ndc_codes:
    items = dataset.find_by_code(ndc, 'NDC')
    if items:
        item = items[0]
        print(f'   NDC {ndc}: {item["description"][:50]}...')
        print(f'      Price: ${item["prices"][0]["gross_charge"]:.2f}')

print(f'\n🔍 EASY CODE COUNTING:')
print(f'   HCPCS items: {dataset.count_by_code_type("HCPCS"):,}')
print(f'   NDC items: {dataset.count_by_code_type("NDC"):,}')
print(f'   CPT items: {dataset.count_by_code_type("CPT"):,}')

print(f'\n🎯 KEYWORD SEARCH - INSULIN:')
insulin_results = dataset.search_by_keywords('insulin')
print(f'   Found: {len(insulin_results)} insulin items')
for i, item in enumerate(insulin_results[:3]):
    print(f'   {i+1}. {item["description"][:40]}... ${item["prices"][0]["gross_charge"]:.2f}')

print(f'\n🎯 KEYWORD SEARCH - MRI:') 
mri_results = dataset.search_by_keywords('mri')
print(f'   Found: {len(mri_results)} MRI items')
for i, item in enumerate(mri_results[:3]):
    print(f'   {i+1}. {item["description"][:40]}... ${item["prices"][0]["gross_charge"]:.2f}')

print(f'\n📊 SUMMARY:')
print(f'   ✅ {len(dataset.items):,} total items with codes and prices')
print(f'   ✅ Fast lookup by any code type')
print(f'   ✅ Easy counting: dataset.count_by_code_type("HCPCS")')
print(f'   ✅ Keyword search: dataset.search_by_keywords("insulin")')
print(f'   ✅ Code lookup: dataset.find_by_code("12345", "NDC")')
print(f'   ✅ Ready for Flask app integration!') 