#!/usr/bin/env python3

import json
import sys
from datetime import datetime
from app import app
from models import db, Hospital, Procedure, PricingData

def import_hospital_transparency_json(file_path):
    """
    Import hospital transparency JSON data.
    
    Note: These files contain cash prices and gross charges, but NO real 
    insurance negotiated rates despite having payer information sections.
    All payer info just contains placeholder text.
    """
    print(f'📂 Loading {file_path}...')
    
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except Exception as e:
        print(f'❌ Error loading file: {e}')
        return
    
    print(f'✅ File loaded successfully')
    
    with app.app_context():
        # Extract hospital information
        hospital_name = data.get('hospital_name', 'Unknown Hospital')
        hospital_location = None
        
        # Try to extract location from hospital_location array
        if 'hospital_location' in data and data['hospital_location']:
            location_info = data['hospital_location'][0] if isinstance(data['hospital_location'], list) else data['hospital_location']
            if isinstance(location_info, dict):
                city = location_info.get('hospital_city', '')
                state = location_info.get('hospital_state', '')
                hospital_location = f"{city}, {state}".strip(', ')
        
        # Check if hospital already exists
        hospital = Hospital.query.filter_by(name=hospital_name).first()
        if not hospital:
            hospital = Hospital(
                name=hospital_name,
                location=hospital_location
            )
            db.session.add(hospital)
            db.session.commit()
            print(f'✅ Created hospital: {hospital_name}')
        else:
            print(f'📋 Using existing hospital: {hospital_name}')
        
        # Process standard charge information
        standard_charges = data.get('standard_charge_information', [])
        print(f'📊 Processing {len(standard_charges)} procedures...')
        
        imported_count = 0
        skipped_count = 0
        
        for i, item in enumerate(standard_charges):
            if i % 1000 == 0:
                print(f'   Processed {i}/{len(standard_charges)} procedures...')
            
            # Extract procedure information
            procedure_name = item.get('description', 'Unknown Procedure')
            procedure_code = item.get('code', {}).get('value', '') if isinstance(item.get('code'), dict) else str(item.get('code', ''))
            
            # Skip if no meaningful procedure name
            if not procedure_name or procedure_name.strip() == '':
                skipped_count += 1
                continue
            
            # Find or create procedure
            procedure = Procedure.query.filter_by(name=procedure_name, code=procedure_code).first()
            if not procedure:
                procedure = Procedure(
                    name=procedure_name,
                    code=procedure_code,
                    description=procedure_name
                )
                db.session.add(procedure)
                db.session.flush()  # Get the ID
            
            # Extract pricing information from standard_charges array
            standard_charges_list = item.get('standard_charges', [])
            
            cash_price = None
            gross_charge = None
            
            for charge in standard_charges_list:
                if isinstance(charge, dict):
                    # Look for discounted cash price
                    if charge.get('setting') == 'outpatient' or not cash_price:
                        if 'discounted_cash' in charge:
                            try:
                                cash_price = float(charge['discounted_cash'])
                            except (ValueError, TypeError):
                                pass
                    
                    # Look for gross charge
                    if 'gross_charge' in charge:
                        try:
                            gross_charge = float(charge['gross_charge'])
                        except (ValueError, TypeError):
                            pass
            
            # Skip if no pricing data found
            if not cash_price and not gross_charge:
                skipped_count += 1
                continue
            
            # Calculate min/max rates
            available_prices = [p for p in [cash_price, gross_charge] if p is not None]
            min_rate = min(available_prices) if available_prices else None
            max_rate = max(available_prices) if available_prices else None
            
            # Check if pricing data already exists
            existing_pricing = PricingData.query.filter_by(
                hospital_id=hospital.id,
                procedure_id=procedure.id
            ).first()
            
            if not existing_pricing:
                # Create new pricing record
                pricing_data = PricingData(
                    hospital_id=hospital.id,
                    procedure_id=procedure.id,
                    cash_price=cash_price,
                    gross_charge=gross_charge,
                    min_rate=min_rate,
                    max_rate=max_rate,
                    data_source=file_path.split('/')[-1]
                )
                db.session.add(pricing_data)
                imported_count += 1
            
            # Commit every 100 records to avoid memory issues
            if imported_count % 100 == 0:
                db.session.commit()
        
        # Final commit
        db.session.commit()
        
        print(f'✅ Import completed!')
        print(f'   - Hospital: {hospital_name}')
        print(f'   - Imported: {imported_count:,} pricing records')
        print(f'   - Skipped: {skipped_count:,} records (no pricing data)')
        print(f'   - Total procedures in database: {Procedure.query.count():,}')
        print(f'   - Total pricing records in database: {PricingData.query.count():,}')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python data_importer.py <json_file>')
        sys.exit(1)
    
    import_hospital_transparency_json(sys.argv[1]) 