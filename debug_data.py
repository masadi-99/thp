#!/usr/bin/env python3

from app import app
from models import db, Hospital, Procedure, PricingData

def analyze_data():
    with app.app_context():
        print("🔍 DEBUGGING HOSPITAL PRICING DATA")
        print("=" * 50)
        
        # Check hospitals
        hospitals = Hospital.query.all()
        print(f"Hospitals: {len(hospitals)}")
        for h in hospitals:
            print(f"  - {h.name} (ID: {h.id})")
        
        print()
        
        # Check total procedures
        total_procedures = Procedure.query.count()
        print(f"Total procedures: {total_procedures:,}")
        
        # Check procedures per hospital
        for hospital in hospitals:
            count = PricingData.query.filter_by(hospital_id=hospital.id).count()
            print(f"  - {hospital.name}: {count:,} pricing records")
        
        print()
        
        # Check for MRI procedures
        print("MRI Procedures Analysis:")
        mri_procedures = Procedure.query.filter(Procedure.name.ilike('%MRI%')).limit(10).all()
        
        for proc in mri_procedures:
            print(f"\nProcedure: {proc.name} (ID: {proc.id})")
            
            # Check pricing for this procedure
            pricing_records = PricingData.query.filter_by(procedure_id=proc.id).all()
            print(f"  Total pricing records: {len(pricing_records)}")
            
            for pricing in pricing_records:
                hospital = Hospital.query.get(pricing.hospital_id)
                print(f"    Hospital: {hospital.name}")
                print(f"    Cash: ${pricing.cash_price}" if pricing.cash_price else "    Cash: None")
                print(f"    Min: ${pricing.min_negotiated_rate}" if pricing.min_negotiated_rate else "    Min: None")
                print(f"    Max: ${pricing.max_negotiated_rate}" if pricing.max_negotiated_rate else "    Max: None")
        
        print()
        
        # Find procedures with actual pricing data
        print("Procedures with actual pricing data:")
        procedures_with_pricing = db.session.query(Procedure).join(PricingData).filter(
            PricingData.min_negotiated_rate.isnot(None)
        ).limit(5).all()
        
        for proc in procedures_with_pricing:
            print(f"\n✅ {proc.name} (ID: {proc.id})")
            pricing_records = PricingData.query.filter_by(procedure_id=proc.id).filter(
                PricingData.min_negotiated_rate.isnot(None)
            ).all()
            
            for pricing in pricing_records:
                hospital = Hospital.query.get(pricing.hospital_id)
                print(f"    {hospital.name}: ${pricing.min_negotiated_rate:,.2f} - ${pricing.max_negotiated_rate:,.2f}")
        
        print()
        
        # Check if procedures are shared between hospitals
        print("Checking procedure sharing between hospitals:")
        
        # Find a procedure that exists for both hospitals
        shared_procedures = db.session.query(Procedure.id, Procedure.name).join(PricingData).group_by(Procedure.id).having(db.func.count(db.distinct(PricingData.hospital_id)) > 1).limit(5).all()
        
        print(f"Procedures shared between hospitals: {len(shared_procedures)}")
        for proc_id, proc_name in shared_procedures:
            print(f"  - {proc_name}")
            hospitals_for_proc = db.session.query(Hospital.name).join(PricingData).filter(PricingData.procedure_id == proc_id).distinct().all()
            print(f"    Available at: {[h[0] for h in hospitals_for_proc]}")

if __name__ == "__main__":
    analyze_data() 