#!/usr/bin/env python3
"""
Build and test UCSF dataset specifically
"""

from hospital_dataset_builder import build_hospital_dataset, save_hospital_dataset, test_hospital_dataset

def main():
    print("🏥 BUILDING UCSF MEDICAL CENTER DATASET")
    print("=" * 80)
    
    # Build UCSF dataset
    dataset = build_hospital_dataset('ucsf')
    
    if dataset:
        # Save the dataset
        save_hospital_dataset(dataset, 'ucsf')
        
        # Test the dataset
        test_hospital_dataset(dataset, 'ucsf')
        
        # Show file size
        import os
        filename = 'ucsf_dataset.pkl'
        if os.path.exists(filename):
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"\n📁 Dataset file size: {size_mb:.1f} MB")
        
        print(f"\n✅ UCSF dataset ready for Flask app integration!")
    else:
        print("❌ Failed to build UCSF dataset")

if __name__ == "__main__":
    main() 