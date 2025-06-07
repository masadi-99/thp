#!/usr/bin/env python3

from app import app
from models import db, Hospital, Procedure, PricingData

def create_sample_data():
    with app.app_context():
        # Create tables
        db.create_all()
        print('✅ Database created')
        
        # Add sample hospitals
        ucsf = Hospital(name='UCSF Medical Center', location='San Francisco, CA')
        stanford = Hospital(name='Stanford Health Care', location='Stanford, CA')
        
        db.session.add_all([ucsf, stanford])
        db.session.commit()
        
        # Add sample procedures
        mri = Procedure(name='MRI Brain', code='70551', description='Magnetic resonance imaging of brain')
        echo = Procedure(name='Echocardiogram', code='93306', description='Transthoracic echocardiogram')
        bilirubin = Procedure(name='Bilirubin Test', code='82247', description='Blood test for bilirubin levels')
        
        db.session.add_all([mri, echo, bilirubin])
        db.session.commit()
        
        # Add sample pricing data
        pricing_data = [
            # UCSF pricing
            PricingData(
                hospital_id=ucsf.id, 
                procedure_id=mri.id,
                cash_price=2500.0,
                gross_charge=8000.0,
                min_rate=2500.0,
                max_rate=8000.0,
                data_source='sample_data'
            ),
            PricingData(
                hospital_id=ucsf.id,
                procedure_id=echo.id,
                cash_price=850.0,
                gross_charge=2200.0,
                min_rate=850.0,
                max_rate=2200.0,
                data_source='sample_data'
            ),
            PricingData(
                hospital_id=ucsf.id,
                procedure_id=bilirubin.id,
                cash_price=30.90,
                gross_charge=103.0,
                min_rate=30.90,
                max_rate=103.0,
                data_source='sample_data'
            ),
            
            # Stanford pricing
            PricingData(
                hospital_id=stanford.id,
                procedure_id=mri.id, 
                cash_price=3200.0,
                gross_charge=9500.0,
                min_rate=3200.0,
                max_rate=9500.0,
                data_source='sample_data'
            ),
            PricingData(
                hospital_id=stanford.id,
                procedure_id=echo.id,
                cash_price=1150.0,
                gross_charge=2800.0,
                min_rate=1150.0,
                max_rate=2800.0,
                data_source='sample_data'
            ),
            PricingData(
                hospital_id=stanford.id,
                procedure_id=bilirubin.id,
                cash_price=100.40,
                gross_charge=251.0,
                min_rate=100.40,
                max_rate=251.0,
                data_source='sample_data'
            ),
        ]
        
        db.session.add_all(pricing_data)
        db.session.commit()
        
        print(f'✅ Sample data created:')
        print(f'   - {Hospital.query.count()} hospitals')
        print(f'   - {Procedure.query.count()} procedures') 
        print(f'   - {PricingData.query.count()} pricing records')

if __name__ == '__main__':
    create_sample_data() 