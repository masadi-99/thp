#!/usr/bin/env python3
"""
Compare all hospital datasets and show comprehensive statistics
"""

from hospital_dataset_builder import load_hospital_dataset, HOSPITAL_NAMES
import os

def main():
    print("🏥 COMPREHENSIVE HOSPITAL DATASET COMPARISON")
    print("=" * 80)
    
    hospitals = ['stanford', 'ucsf', 'ucla', 'cedars']
    datasets = {}
    
    # Load all datasets
    print("📂 Loading all hospital datasets...")
    for hospital_key in hospitals:
        dataset = load_hospital_dataset(hospital_key)
        if dataset:
            datasets[hospital_key] = dataset
            print(f"   ✅ {dataset.hospital_name}")
        else:
            print(f"   ❌ {HOSPITAL_NAMES[hospital_key]} - not found")
    
    if len(datasets) == 0:
        print("❌ No datasets found! Run the individual build scripts first.")
        return
    
    print(f"\n📊 OVERALL STATISTICS COMPARISON:")
    print("-" * 80)
    print(f"{'Hospital':<25} {'Items':<10} {'NDC':<8} {'HCPCS':<8} {'CPT':<6} {'File Size':<10}")
    print("-" * 80)
    
    total_items = 0
    total_ndc = 0
    total_hcpcs = 0
    total_cpt = 0
    
    for hospital_key in hospitals:
        if hospital_key in datasets:
            dataset = datasets[hospital_key]
            stats = dataset.get_stats()
            
            # Get file size
            filename = f"{hospital_key}_dataset.pkl"
            file_size = "N/A"
            if os.path.exists(filename):
                size_mb = os.path.getsize(filename) / (1024 * 1024)
                file_size = f"{size_mb:.1f} MB"
            
            ndc_count = dataset.count_by_code_type('NDC')
            hcpcs_count = dataset.count_by_code_type('HCPCS')
            cpt_count = dataset.count_by_code_type('CPT')
            
            print(f"{stats['hospital_name']:<25} {stats['total_items']:<10,} {ndc_count:<8,} {hcpcs_count:<8,} {cpt_count:<6,} {file_size:<10}")
            
            total_items += stats['total_items']
            total_ndc += ndc_count
            total_hcpcs += hcpcs_count
            total_cpt += cpt_count
    
    print("-" * 80)
    print(f"{'TOTAL':<25} {total_items:<10,} {total_ndc:<8,} {total_hcpcs:<8,} {total_cpt:<6,}")
    
    # Test common codes across hospitals
    print(f"\n🔍 TESTING COMMON NDC CODES:")
    print("-" * 80)
    
    # Get NDC codes from each hospital
    ndc_sets = {}
    for hospital_key, dataset in datasets.items():
        ndc_codes = set(dataset.get_all_codes_of_type('NDC'))
        ndc_sets[hospital_key] = ndc_codes
        print(f"{dataset.hospital_name}: {len(ndc_codes):,} unique NDC codes")
    
    # Find intersections
    if len(ndc_sets) >= 2:
        print(f"\n🎯 NDC CODE OVERLAPS:")
        hospitals_list = list(ndc_sets.keys())
        
        for i in range(len(hospitals_list)):
            for j in range(i + 1, len(hospitals_list)):
                hosp1 = hospitals_list[i]
                hosp2 = hospitals_list[j]
                overlap = ndc_sets[hosp1] & ndc_sets[hosp2]
                print(f"   {HOSPITAL_NAMES[hosp1]} ∩ {HOSPITAL_NAMES[hosp2]}: {len(overlap)} common NDC codes")
        
        # Find codes common to all hospitals
        if len(ndc_sets) >= 3:
            all_common = set.intersection(*ndc_sets.values())
            print(f"\n   🌟 Common to ALL hospitals: {len(all_common)} NDC codes")
            
            if len(all_common) > 0:
                print(f"   Examples of universal NDC codes:")
                for i, ndc_code in enumerate(sorted(list(all_common))[:3]):
                    print(f"      {i+1}. NDC {ndc_code}")
                    # Show pricing from each hospital
                    for hospital_key, dataset in datasets.items():
                        items = dataset.find_by_code(ndc_code, 'NDC')
                        if items:
                            item = items[0]
                            price = item['prices'][0]['gross_charge']
                            print(f"         {dataset.hospital_name}: ${price:.2f} - {item['description'][:40]}...")
    
    # Test search capabilities across all hospitals
    print(f"\n🔍 SEARCH TEST: 'INSULIN' ACROSS ALL HOSPITALS:")
    print("-" * 80)
    
    for hospital_key, dataset in datasets.items():
        insulin_results = dataset.search_by_keywords('insulin')
        print(f"{dataset.hospital_name}: {len(insulin_results)} insulin items")
        if insulin_results:
            cheapest = min(insulin_results, key=lambda x: x['prices'][0]['gross_charge'])
            most_expensive = max(insulin_results, key=lambda x: x['prices'][0]['gross_charge'])
            print(f"   Cheapest: ${cheapest['prices'][0]['gross_charge']:.2f} - {cheapest['description'][:40]}...")
            print(f"   Most expensive: ${most_expensive['prices'][0]['gross_charge']:.2f} - {most_expensive['description'][:40]}...")
    
    print(f"\n✅ ALL HOSPITAL DATASETS READY FOR CROSS-HOSPITAL PRICE COMPARISON!")
    print(f"   • Total items across all hospitals: {total_items:,}")
    print(f"   • Total NDC codes: {total_ndc:,}")
    print(f"   • Total HCPCS codes: {total_hcpcs:,}")
    print(f"   • Ready for Flask app integration")

if __name__ == "__main__":
    main() 