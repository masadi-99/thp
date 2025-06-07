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
        """Import from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Handle different JSON structures
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
                
        except Exception as e:
            raise Exception(f"Error reading JSON file: {e}")
        
        self._process_dataframe(df, hospital_name, hospital_location, data_import)
    
    def _process_dataframe(self, df, hospital_name, hospital_location, data_import):
        """Process DataFrame and import data"""
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
        if value is None:
            return None
        
        try:
            # Clean up common currency formatting
            if isinstance(value, str):
                value = re.sub(r'[,$]', '', value.strip())
            return float(value) if value != '' else None
        except (ValueError, TypeError):
            return None

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