#!/usr/bin/env python3
"""
Build and test UCLA dataset specifically
"""

from hospital_dataset_builder import build_hospital_dataset, save_hospital_dataset, test_hospital_dataset

def main():
    print("🏥 BUILDING UCLA HEALTH DATASET")
    print("=" * 80)
    
    # Build UCLA dataset
    dataset = build_hospital_dataset('ucla')
    
    if dataset:
        # Save the dataset
        save_hospital_dataset(dataset, 'ucla')
        
        # Test the dataset
        test_hospital_dataset(dataset, 'ucla')
        
        # Show file size
        import os
        filename = 'ucla_dataset.pkl'
        if os.path.exists(filename):
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"\n📁 Dataset file size: {size_mb:.1f} MB")
        
        print(f"\n✅ UCLA dataset ready for Flask app integration!")
    else:
        print("❌ Failed to build UCLA dataset")

if __name__ == "__main__":
    main() 