#!/usr/bin/env python3
"""
Data importer for hospital pricing transparency files
Supports CSV and JSON formats commonly used by hospitals
"""

import pandas as pd
import json
import argparse
from pathlib import Path
from datetime import datetime, date
import re

from app import app
from models import db, Hospital, Procedure, PricingData, DataImport

class HospitalDataImporter:
    """Import hospital pricing data from various file formats"""
    
    def __init__(self):
        self.supported_formats = ['csv', 'json', 'xlsx']
        
    def import_file(self, file_path, hospital_name=None, hospital_location=None):
        """Import pricing data from file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = file_path.suffix.lower()[1:]  # Remove the dot
        
        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_extension}. Supported: {self.supported_formats}")
        
        print(f"Importing data from {file_path}")
        
        with app.app_context():
            # Create import record
            data_import = DataImport(
                filename=str(file_path),
                import_date=datetime.utcnow(),
                status='pending'
            )
            db.session.add(data_import)
            db.session.commit()
            
            try:
                if file_extension == 'csv':
                    self._import_csv(file_path, hospital_name, hospital_location, data_import)
                elif file_extension == 'json':
                    self._import_json(file_path, hospital_name, hospital_location, data_import)
                elif file_extension == 'xlsx':
                    self._import_excel(file_path, hospital_name, hospital_location, data_import)
                
                data_import.status = 'completed'
                db.session.commit()
                print(f"Import completed successfully. Records imported: {data_import.records_imported}")
                
            except Exception as e:
                data_import.status = 'failed'
                data_import.error_log = str(e)
                db.session.commit()
                print(f"Import failed: {e}")
                raise
    
    def _import_csv(self, file_path, hospital_name, hospital_location, data_import):
        """Import from CSV file"""
        try:
            df = pd.read_csv(file_path, low_memory=False)
        except Exception as e:
            raise Exception(f"Error reading CSV file: {e}")
        
        self._process_dataframe(df, hospital_name, hospital_location, data_import)
    
    def _import_excel(self, file_path, hospital_name, hospital_location, data_import):
        """Import from Excel file"""
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise Exception(f"Error reading Excel file: {e}")
        
        self._process_dataframe(df, hospital_name, hospital_location, data_import)
    
    def _import_json(self, file_path, hospital_name, hospital_location, data_import):
        """Import from JSON file - handles hospital transparency format"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check if this is a hospital transparency format
            if isinstance(data, dict) and 'hospital_name' in data and 'standard_charge_information' in data:
                self._process_hospital_transparency_format(data, data_import)
            else:
                # Handle other JSON structures
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                elif isinstance(data, dict):
                    # Try to find the main data array
                    possible_keys = ['data', 'procedures', 'pricing', 'items']
                    main_data = None
                    for key in possible_keys:
                        if key in data and isinstance(data[key], list):
                            main_data = data[key]
                            break
                    
                    if main_data is None:
                        # If no array found, treat the dict as a single record
                        df = pd.DataFrame([data])
                    else:
                        df = pd.DataFrame(main_data)
                else:
                    raise Exception("Unexpected JSON structure")
                
                self._process_dataframe(df, hospital_name, hospital_location, data_import)
                
        except Exception as e:
            raise Exception(f"Error reading JSON file: {e}")
    
    def _process_hospital_transparency_format(self, data, data_import):
        """Process hospital transparency JSON format"""
        print("Processing hospital transparency format...")
        
        # Extract hospital information
        hospital_name = data.get('hospital_name', 'Unknown Hospital').title()
        hospital_location = data.get('hospital_location', ['Unknown Location'])
        if isinstance(hospital_location, list):
            hospital_location = ', '.join(hospital_location)
        
        hospital_address = data.get('hospital_address', {})
        address_str = ""
        if isinstance(hospital_address, dict):
            address_parts = []
            for key in ['street', 'city', 'state', 'zip']:
                if key in hospital_address and hospital_address[key]:
                    address_parts.append(str(hospital_address[key]))
            address_str = ', '.join(address_parts)
        
        # Get or create hospital
        hospital = Hospital.query.filter_by(name=hospital_name).first()
        if not hospital:
            hospital = Hospital(
                name=hospital_name,
                location=hospital_location,
                address=address_str,
                created_at=datetime.utcnow()
            )
            db.session.add(hospital)
            db.session.commit()
            print(f"Created new hospital: {hospital_name}")
        else:
            print(f"Using existing hospital: {hospital_name}")
        
        data_import.hospital_id = hospital.id
        
        # Process standard charge information
        standard_charges = data.get('standard_charge_information', [])
        records_imported = 0
        records_failed = 0
        
        print(f"Processing {len(standard_charges)} charge items...")
        
        for idx, item in enumerate(standard_charges):
            try:
                # Extract procedure information
                description = item.get('description', '').strip()
                if not description:
                    continue
                
                # Get code information
                code_info = item.get('code_information', [])
                procedure_code = ""
                code_type = "OTHER"
                
                if code_info and isinstance(code_info, list):
                    # Find the first relevant code
                    for code_item in code_info:
                        if isinstance(code_item, dict):
                            code_val = code_item.get('code', '')
                            code_type_val = code_item.get('type', 'OTHER').upper()
                            if code_val and code_type_val in ['CPT', 'HCPCS', 'DRG', 'ICD10', 'MS-DRG']:
                                procedure_code = str(code_val)
                                code_type = code_type_val
                                break
                
                # Get or create procedure
                procedure = None
                if procedure_code:
                    procedure = Procedure.query.filter_by(name=description, code=procedure_code).first()
                
                if not procedure:
                    # Try to find by name only
                    procedure = Procedure.query.filter_by(name=description).first()
                
                if not procedure:
                    procedure = Procedure(
                        name=description,
                        code=procedure_code,
                        code_type=code_type,
                        category='Imported',
                        created_at=datetime.utcnow()
                    )
                    db.session.add(procedure)
                    db.session.flush()
                
                # Extract standard charges
                standard_charges_info = item.get('standard_charges', [])
                
                cash_price = None
                min_rate = None
                max_rate = None
                payer_rates = {}
                
                for charge_item in standard_charges_info:
                    if isinstance(charge_item, dict):
                        setting = charge_item.get('setting', '').lower()
                        minimum = self._extract_numeric(charge_item.get('minimum'))
                        maximum = self._extract_numeric(charge_item.get('maximum'))
                        
                        # Look for cash/gross charges
                        if 'gross' in setting or 'cash' in setting or 'uninsured' in setting:
                            if minimum is not None:
                                cash_price = minimum
                        
                        # Collect min/max across all settings
                        if minimum is not None:
                            if min_rate is None or minimum < min_rate:
                                min_rate = minimum
                        if maximum is not None:
                            if max_rate is None or maximum > max_rate:
                                max_rate = maximum
                        
                        # Extract payer-specific information
                        payer_info = charge_item.get('payer_information', [])
                        for payer in payer_info:
                            if isinstance(payer, dict):
                                payer_name = payer.get('payer_name', '').strip()
                                plan_name = payer.get('plan_name', '').strip()
                                standard_charge = self._extract_numeric(payer.get('standard_charge'))
                                
                                if payer_name and standard_charge is not None:
                                    key = f"{payer_name}" + (f" - {plan_name}" if plan_name else "")
                                    payer_rates[key] = standard_charge
                
                # Use cash price from payers if not found in standard charges
                if cash_price is None:
                    # Look for self-pay or cash in payer rates
                    for payer_key, rate in payer_rates.items():
                        if any(term in payer_key.lower() for term in ['self', 'cash', 'uninsured', 'self-pay']):
                            cash_price = rate
                            break
                
                # Check if pricing already exists
                existing_pricing = PricingData.query.filter_by(
                    hospital_id=hospital.id,
                    procedure_id=procedure.id
                ).first()
                
                if existing_pricing:
                    # Update existing record
                    if cash_price is not None:
                        existing_pricing.cash_price = cash_price
                    if min_rate is not None:
                        existing_pricing.min_negotiated_rate = min_rate
                    if max_rate is not None:
                        existing_pricing.max_negotiated_rate = max_rate
                    if payer_rates:
                        existing_pricing.set_payer_rates(payer_rates)
                    existing_pricing.last_updated = datetime.utcnow()
                else:
                    # Create new pricing record
                    pricing = PricingData(
                        hospital_id=hospital.id,
                        procedure_id=procedure.id,
                        cash_price=cash_price,
                        min_negotiated_rate=min_rate,
                        max_negotiated_rate=max_rate,
                        effective_date=date.today(),
                        last_updated=datetime.utcnow(),
                        data_source='Hospital Transparency File'
                    )
                    if payer_rates:
                        pricing.set_payer_rates(payer_rates)
                    db.session.add(pricing)
                
                records_imported += 1
                
                if records_imported % 100 == 0:
                    print(f"Processed {records_imported} records...")
                    db.session.commit()
                    
            except Exception as e:
                records_failed += 1
                print(f"Failed to import item {idx}: {e}")
                continue
        
        db.session.commit()
        data_import.records_imported = records_imported
        data_import.records_failed = records_failed
        
        print(f"Import summary: {records_imported} imported, {records_failed} failed")
    
    def _extract_numeric(self, value):
        """Extract numeric value from various formats"""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value) if value > 0 else None
        
        if isinstance(value, str):
            # Clean up common currency formatting
            cleaned = re.sub(r'[,$]', '', value.strip())
            try:
                return float(cleaned) if cleaned and cleaned != '0' else None
            except ValueError:
                return None
        
        return None
    
    def _process_dataframe(self, df, hospital_name, hospital_location, data_import):
        """Process DataFrame and import data (for CSV/Excel files)"""
        print(f"Processing {len(df)} records...")
        
        # Detect column mappings
        column_mappings = self._detect_columns(df.columns.tolist())
        print(f"Column mappings detected: {column_mappings}")
        
        # Get or create hospital
        hospital = self._get_or_create_hospital(hospital_name, hospital_location, df, column_mappings)
        data_import.hospital_id = hospital.id
        
        records_imported = 0
        records_failed = 0
        
        for index, row in df.iterrows():
            try:
                self._import_row(row, hospital, column_mappings)
                records_imported += 1
                
                if records_imported % 100 == 0:
                    print(f"Processed {records_imported} records...")
                    db.session.commit()  # Commit in batches
                    
            except Exception as e:
                records_failed += 1
                print(f"Failed to import row {index}: {e}")
                continue
        
        db.session.commit()
        data_import.records_imported = records_imported
        data_import.records_failed = records_failed
        
        print(f"Import summary: {records_imported} imported, {records_failed} failed")
    
    def _detect_columns(self, columns):
        """Detect column mappings from header names"""
        mappings = {}
        
        # Common column name patterns
        patterns = {
            'procedure_name': [r'procedure', r'service', r'description', r'item.*description'],
            'procedure_code': [r'code', r'cpt', r'hcpcs', r'drg'],
            'cash_price': [r'cash', r'self.*pay', r'uninsured', r'gross.*charge'],
            'min_rate': [r'min', r'minimum', r'lowest'],
            'max_rate': [r'max', r'maximum', r'highest'],
            'payer_name': [r'payer', r'insurance', r'plan'],
            'negotiated_rate': [r'negotiated', r'contracted', r'rate']
        }
        
        for col in columns:
            col_lower = col.lower()
            for field, patterns_list in patterns.items():
                for pattern in patterns_list:
                    if re.search(pattern, col_lower):
                        if field not in mappings:  # Use first match
                            mappings[field] = col
                        break
        
        return mappings
    
    def _get_or_create_hospital(self, hospital_name, hospital_location, df, column_mappings):
        """Get existing hospital or create new one"""
        
        # Try to extract hospital info from data if not provided
        if not hospital_name and 'hospital_name' in column_mappings:
            hospital_name = df[column_mappings['hospital_name']].iloc[0] if len(df) > 0 else "Unknown Hospital"
        elif not hospital_name:
            hospital_name = "Unknown Hospital"
        
        if not hospital_location:
            hospital_location = "Unknown Location"
        
        # Check if hospital already exists
        hospital = Hospital.query.filter_by(name=hospital_name).first()
        
        if not hospital:
            hospital = Hospital(
                name=hospital_name,
                location=hospital_location,
                created_at=datetime.utcnow()
            )
            db.session.add(hospital)
            db.session.commit()
            print(f"Created new hospital: {hospital_name}")
        else:
            print(f"Using existing hospital: {hospital_name}")
        
        return hospital
    
    def _import_row(self, row, hospital, column_mappings):
        """Import a single row of data"""
        
        # Extract procedure information
        procedure_name = self._get_value(row, column_mappings, 'procedure_name')
        procedure_code = self._get_value(row, column_mappings, 'procedure_code', default='')
        
        if not procedure_name:
            raise Exception("Missing procedure name")
        
        # Get or create procedure
        procedure = Procedure.query.filter_by(name=procedure_name, code=procedure_code).first()
        
        if not procedure:
            procedure = Procedure(
                name=procedure_name,
                code=procedure_code,
                code_type='CPT' if procedure_code else 'OTHER',
                category='Imported',
                created_at=datetime.utcnow()
            )
            db.session.add(procedure)
            db.session.flush()  # Get ID without committing
        
        # Extract pricing information
        cash_price = self._get_numeric_value(row, column_mappings, 'cash_price')
        min_rate = self._get_numeric_value(row, column_mappings, 'min_rate')
        max_rate = self._get_numeric_value(row, column_mappings, 'max_rate')
        
        # Check if pricing already exists
        existing_pricing = PricingData.query.filter_by(
            hospital_id=hospital.id,
            procedure_id=procedure.id
        ).first()
        
        if existing_pricing:
            # Update existing record
            if cash_price is not None:
                existing_pricing.cash_price = cash_price
            if min_rate is not None:
                existing_pricing.min_negotiated_rate = min_rate
            if max_rate is not None:
                existing_pricing.max_negotiated_rate = max_rate
            existing_pricing.last_updated = datetime.utcnow()
        else:
            # Create new pricing record
            pricing = PricingData(
                hospital_id=hospital.id,
                procedure_id=procedure.id,
                cash_price=cash_price,
                min_negotiated_rate=min_rate,
                max_negotiated_rate=max_rate,
                effective_date=date.today(),
                last_updated=datetime.utcnow(),
                data_source='File Import'
            )
            db.session.add(pricing)
    
    def _get_value(self, row, column_mappings, field, default=None):
        """Get value from row using column mapping"""
        if field in column_mappings:
            column_name = column_mappings[field]
            value = row.get(column_name, default)
            return value if pd.notna(value) else default
        return default
    
    def _get_numeric_value(self, row, column_mappings, field):
        """Get numeric value from row"""
        value = self._get_value(row, column_mappings, field)
        return self._extract_numeric(value)

def main():
    """Command-line interface for data import"""
    parser = argparse.ArgumentParser(description='Import hospital pricing data')
    parser.add_argument('file_path', help='Path to the data file')
    parser.add_argument('--hospital-name', help='Hospital name (if not in data)')
    parser.add_argument('--hospital-location', help='Hospital location (if not in data)')
    
    args = parser.parse_args()
    
    importer = HospitalDataImporter()
    
    try:
        importer.import_file(
            args.file_path,
            hospital_name=args.hospital_name,
            hospital_location=args.hospital_location
        )
        print("Data import completed successfully!")
    except Exception as e:
        print(f"Import failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main()) 