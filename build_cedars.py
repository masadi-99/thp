#!/usr/bin/env python3
"""
Build and test Cedars-Sinai dataset specifically
"""

from hospital_dataset_builder import build_hospital_dataset, save_hospital_dataset, test_hospital_dataset

def main():
    print("🏥 BUILDING CEDARS-SINAI MEDICAL CENTER DATASET")
    print("=" * 80)
    
    # Build Cedars dataset
    dataset = build_hospital_dataset('cedars')
    
    if dataset:
        # Save the dataset
        save_hospital_dataset(dataset, 'cedars')
        
        # Test the dataset
        test_hospital_dataset(dataset, 'cedars')
        
        # Show file size
        import os
        filename = 'cedars_dataset.pkl'
        if os.path.exists(filename):
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"\n📁 Dataset file size: {size_mb:.1f} MB")
        
        print(f"\n✅ Cedars-Sinai dataset ready for Flask app integration!")
    else:
        print("❌ Failed to build Cedars-Sinai dataset")

if __name__ == "__main__":
    main() 