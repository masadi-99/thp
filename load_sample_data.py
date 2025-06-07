#!/usr/bin/env python3
"""
Sample data loader for Hospital Pricing Transparency Tool
"""

from app import app
from models import db, Hospital, Procedure, PricingData
from datetime import datetime, date
import json

def load_sample_data():
    """Load sample hospitals, procedures, and pricing data"""
    with app.app_context():
        print("Loading sample data...")
        
        # Sample Hospitals
        hospitals_data = [
            {
                'name': 'St. Mary\'s General Hospital',
                'location': 'San Francisco, CA',
                'address': '1234 Health St, San Francisco, CA 94110',
                'city': 'San Francisco',
                'state': 'CA',
                'zip_code': '94110',
                'system': 'St. Mary\'s Health System',
                'ein': '12-3456789'
            },
            {
                'name': 'Valley Medical Center',
                'location': 'San Jose, CA',
                'address': '5678 Valley Rd, San Jose, CA 95110',
                'city': 'San Jose',
                'state': 'CA',
                'zip_code': '95110',
                'system': 'Valley Health Network',
                'ein': '98-7654321'
            },
            {
                'name': 'Bay Area Community Hospital',
                'location': 'Oakland, CA',
                'address': '9876 Bay Ave, Oakland, CA 94601',
                'city': 'Oakland',
                'state': 'CA',
                'zip_code': '94601',
                'system': 'Community Health Partners',
                'ein': '45-6789012'
            },
            {
                'name': 'Pacific Coast Medical Center',
                'location': 'Santa Clara, CA',
                'address': '2468 Pacific Blvd, Santa Clara, CA 95050',
                'city': 'Santa Clara',
                'state': 'CA',
                'zip_code': '95050',
                'system': 'Pacific Health Group',
                'ein': '78-9012345'
            },
            {
                'name': 'Golden Gate Regional Hospital',
                'location': 'Palo Alto, CA',
                'address': '1357 Golden Gate Dr, Palo Alto, CA 94301',
                'city': 'Palo Alto',
                'state': 'CA',
                'zip_code': '94301',
                'system': 'Regional Health Alliance',
                'ein': '23-4567890'
            }
        ]
        
        hospitals = []
        for hospital_data in hospitals_data:
            hospital = Hospital(**hospital_data)
            db.session.add(hospital)
            hospitals.append(hospital)
        
        db.session.commit()
        print(f"Added {len(hospitals)} hospitals")
        
        # Sample Procedures
        procedures_data = [
            {
                'name': 'MRI Brain without Contrast',
                'code': '70551',
                'code_type': 'CPT',
                'category': 'Diagnostic Imaging',
                'description': 'Magnetic resonance imaging of brain without contrast material'
            },
            {
                'name': 'CT Scan Chest with Contrast',
                'code': '71260',
                'code_type': 'CPT',
                'category': 'Diagnostic Imaging',
                'description': 'Computed tomography of chest with contrast material'
            },
            {
                'name': 'Knee Arthroscopy',
                'code': '29881',
                'code_type': 'CPT',
                'category': 'Surgery',
                'description': 'Arthroscopy, knee, surgical; with meniscectomy'
            },
            {
                'name': 'Colonoscopy Screening',
                'code': '45378',
                'code_type': 'CPT',
                'category': 'Preventive Care',
                'description': 'Colonoscopy, flexible; diagnostic screening'
            },
            {
                'name': 'Emergency Room Visit Level 4',
                'code': '99284',
                'code_type': 'CPT',
                'category': 'Emergency Care',
                'description': 'Emergency department visit for evaluation and management'
            },
            {
                'name': 'Hip Replacement Surgery',
                'code': '27130',
                'code_type': 'CPT',
                'category': 'Surgery',
                'description': 'Total hip arthroplasty'
            },
            {
                'name': 'Chest X-Ray',
                'code': '71020',
                'code_type': 'CPT',
                'category': 'Diagnostic Imaging',
                'description': 'Radiologic examination, chest, 2 views'
            },
            {
                'name': 'Blood Test Complete Panel',
                'code': '80053',
                'code_type': 'CPT',
                'category': 'Laboratory',
                'description': 'Comprehensive metabolic panel'
            },
            {
                'name': 'Cardiac Catheterization',
                'code': '93458',
                'code_type': 'CPT',
                'category': 'Cardiology',
                'description': 'Catheter placement in coronary artery for angiography'
            },
            {
                'name': 'Mammography Screening',
                'code': '77067',
                'code_type': 'CPT',
                'category': 'Preventive Care',
                'description': 'Screening mammography, bilateral'
            }
        ]
        
        procedures = []
        for procedure_data in procedures_data:
            procedure = Procedure(**procedure_data)
            db.session.add(procedure)
            procedures.append(procedure)
        
        db.session.commit()
        print(f"Added {len(procedures)} procedures")
        
        # Sample Pricing Data
        print("Adding pricing data...")
        pricing_count = 0
        
        # Generate realistic pricing data for each procedure at each hospital
        import random
        random.seed(42)  # For consistent sample data
        
        for procedure in procedures:
            base_prices = {
                'MRI Brain without Contrast': 2500,
                'CT Scan Chest with Contrast': 1800,
                'Knee Arthroscopy': 8500,
                'Colonoscopy Screening': 1200,
                'Emergency Room Visit Level 4': 1500,
                'Hip Replacement Surgery': 45000,
                'Chest X-Ray': 250,
                'Blood Test Complete Panel': 150,
                'Cardiac Catheterization': 12000,
                'Mammography Screening': 400
            }
            
            base_price = base_prices.get(procedure.name, 1000)
            
            for hospital in hospitals:
                # Generate varied pricing with some randomness
                price_variation = random.uniform(0.7, 1.4)  # 30% below to 40% above base
                cash_price = int(base_price * price_variation)
                
                # Insurance rates are typically lower
                min_rate = int(cash_price * random.uniform(0.4, 0.7))
                max_rate = int(cash_price * random.uniform(0.8, 0.95))
                
                # Sample payer-specific rates
                payer_rates = {
                    'Blue Cross Blue Shield': int(cash_price * random.uniform(0.5, 0.75)),
                    'Kaiser Permanente': int(cash_price * random.uniform(0.45, 0.65)),
                    'Aetna': int(cash_price * random.uniform(0.55, 0.8)),
                    'Medicare': int(cash_price * random.uniform(0.4, 0.6)),
                    'Medicaid': int(cash_price * random.uniform(0.3, 0.5))
                }
                
                pricing = PricingData(
                    hospital_id=hospital.id,
                    procedure_id=procedure.id,
                    cash_price=cash_price,
                    min_negotiated_rate=min_rate,
                    max_negotiated_rate=max_rate,
                    payer_specific_rates=json.dumps(payer_rates),
                    effective_date=date(2024, 1, 1),
                    data_source='Sample Data Generator'
                )
                
                db.session.add(pricing)
                pricing_count += 1
        
        db.session.commit()
        print(f"Added {pricing_count} pricing records")
        print("Sample data loaded successfully!")
        
        # Display summary
        print("\n=== DATA SUMMARY ===")
        print(f"Hospitals: {len(hospitals)}")
        print(f"Procedures: {len(procedures)}")
        print(f"Pricing Records: {pricing_count}")
        print("\nExample hospitals:")
        for hospital in hospitals[:3]:
            print(f"  - {hospital.name} ({hospital.location})")
        print("\nExample procedures:")
        for procedure in procedures[:5]:
            print(f"  - {procedure.name} ({procedure.code})")

if __name__ == '__main__':
    load_sample_data() 