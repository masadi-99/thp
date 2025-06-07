#!/usr/bin/env python3
"""
Comprehensive Hospital Data Importer
Imports and matches procedures from all 4 hospitals based on medical codes.
"""

import json
import sqlite3
import os
from typing import Dict, List, Any, Optional
import re
from datetime import datetime

class HospitalDataImporter:
    def __init__(self, db_path: str = 'instance/hospital_pricing.db'):
        self.db_path = db_path
        self.ensure_instance_dir()
        self.init_database()
        
    def ensure_instance_dir(self):
        """Ensure instance directory exists"""
        os.makedirs('instance', exist_ok=True)
    
    def init_database(self):
        """Initialize database with improved schema for code-based matching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drop existing tables to start fresh
        cursor.execute('DROP TABLE IF EXISTS pricing')
        cursor.execute('DROP TABLE IF EXISTS procedures')
        cursor.execute('DROP TABLE IF EXISTS hospitals')
        
        # Create hospitals table
        cursor.execute('''
            CREATE TABLE hospitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_name TEXT,
                last_updated TEXT,
                location TEXT,
                address TEXT,
                license_number TEXT,
                state TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create procedures table with improved indexing for codes
        cursor.execute('''
            CREATE TABLE procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                cpt_code TEXT,
                hcpcs_code TEXT,
                ndc_code TEXT,
                drg_code TEXT,
                icd_code TEXT,
                revenue_code TEXT,
                primary_code TEXT,
                category TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create pricing table
        cursor.execute('''
            CREATE TABLE pricing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_id INTEGER NOT NULL,
                procedure_id INTEGER NOT NULL,
                price REAL,
                min_price REAL,
                max_price REAL,
                standard_charge REAL,
                cash_price REAL,
                payer_specific_price REAL,
                setting TEXT,
                charge_type TEXT,
                billing_class TEXT,
                additional_generic_notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                FOREIGN KEY (procedure_id) REFERENCES procedures(id)
            )
        ''')
        
        # Create indices for better performance
        cursor.execute('CREATE INDEX idx_procedures_codes ON procedures(cpt_code, hcpcs_code, ndc_code)')
        cursor.execute('CREATE INDEX idx_procedures_description ON procedures(description)')
        cursor.execute('CREATE INDEX idx_pricing_lookup ON pricing(hospital_id, procedure_id)')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    
    def extract_codes(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Extract various medical codes from item"""
        codes = {
            'cpt_code': '',
            'hcpcs_code': '',
            'ndc_code': '', 
            'drg_code': '',
            'icd_code': '',
            'revenue_code': ''
        }
        
        # Common field names for codes across different hospitals
        code_fields = {
            'cpt_code': ['code', 'cpt_code', 'CPT', 'cpt', 'procedure_code'],
            'hcpcs_code': ['hcpcs_code', 'HCPCS', 'hcpcs'],
            'ndc_code': ['ndc_code', 'NDC', 'ndc', 'drug_code'],
            'drg_code': ['drg_code', 'DRG', 'drg'],
            'icd_code': ['icd_code', 'ICD', 'icd10_code', 'icd9_code'],
            'revenue_code': ['revenue_code', 'rev_code', 'revenue']
        }
        
        for code_type, field_names in code_fields.items():
            for field in field_names:
                if field in item and item[field]:
                    codes[code_type] = str(item[field]).strip()
                    break
        
        return codes
    
    def normalize_description(self, description: str) -> str:
        """Normalize procedure descriptions for better matching"""
        if not description:
            return ""
        
        # Remove extra whitespace and normalize case
        normalized = ' '.join(description.split())
        
        # Standard medical abbreviations
        replacements = {
            ' W/ ': ' WITH ',
            ' W/O ': ' WITHOUT ',
            ' WO ': ' WITHOUT ',
            ' & ': ' AND ',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized.upper()
    
    def find_or_create_procedure(self, description: str, codes: Dict[str, str]) -> int:
        """Find existing procedure or create new one based on codes and description"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        normalized_desc = self.normalize_description(description)
        primary_code = codes.get('cpt_code') or codes.get('hcpcs_code') or codes.get('ndc_code') or ''
        
        # First try to match by primary code if available
        if primary_code:
            cursor.execute('''
                SELECT id FROM procedures 
                WHERE (cpt_code = ? OR hcpcs_code = ? OR ndc_code = ?) 
                AND description = ?
            ''', (primary_code, primary_code, primary_code, normalized_desc))
            
            result = cursor.fetchone()
            if result:
                conn.close()
                return result[0]
        
        # If no code match, try exact description match
        cursor.execute('SELECT id FROM procedures WHERE description = ?', (normalized_desc,))
        result = cursor.fetchone()
        if result:
            conn.close()
            return result[0]
        
        # Create new procedure
        cursor.execute('''
            INSERT INTO procedures (description, cpt_code, hcpcs_code, ndc_code, 
                                  drg_code, icd_code, revenue_code, primary_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            normalized_desc,
            codes.get('cpt_code', ''),
            codes.get('hcpcs_code', ''),
            codes.get('ndc_code', ''),
            codes.get('drg_code', ''),
            codes.get('icd_code', ''),
            codes.get('revenue_code', ''),
            primary_code
        ))
        
        procedure_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return procedure_id
    
    def extract_pricing_info(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pricing information from hospital item"""
        pricing = {
            'price': None,
            'min_price': None,
            'max_price': None,
            'standard_charge': None,
            'cash_price': None,
            'payer_specific_price': None,
            'setting': '',
            'charge_type': '',
            'billing_class': ''
        }
        
        # Common price field names
        price_fields = [
            'gross_charge', 'price', 'amount', 'charge', 'standard_charge',
            'cash_price', 'de_identified_min_negotiated_charge',
            'de_identified_max_negotiated_charge'
        ]
        
        for field in price_fields:
            if field in item and item[field] is not None:
                try:
                    value = float(str(item[field]).replace('$', '').replace(',', ''))
                    if field in ['de_identified_min_negotiated_charge', 'minimum']:
                        pricing['min_price'] = value
                    elif field in ['de_identified_max_negotiated_charge', 'maximum']:
                        pricing['max_price'] = value
                    elif field in ['cash_price', 'cash']:
                        pricing['cash_price'] = value
                    else:
                        pricing['price'] = value
                        pricing['standard_charge'] = value
                except (ValueError, TypeError):
                    continue
        
        # Extract metadata
        pricing['setting'] = str(item.get('setting', ''))
        pricing['charge_type'] = str(item.get('charge_type', ''))
        pricing['billing_class'] = str(item.get('billing_class', ''))
        
        return pricing
    
    def import_hospital_data(self, file_path: str, hospital_name: str):
        """Import data from a single hospital JSON file"""
        print(f"Importing {hospital_name} from {file_path}...")
        
        # Add hospital to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO hospitals (name, file_name, location, state)
            VALUES (?, ?, ?, ?)
        ''', (hospital_name, os.path.basename(file_path), hospital_name, 'CA'))
        
        cursor.execute('SELECT id FROM hospitals WHERE name = ?', (hospital_name,))
        hospital_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        # Process JSON file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle different JSON structures
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if 'reporting_plans' in data:
                    for plan in data['reporting_plans']:
                        if 'in_network' in plan:
                            for item in plan['in_network']:
                                items.append(item)
                elif 'standard_charges' in data:
                    items = data['standard_charges']
                elif 'chargemaster' in data:
                    items = data['chargemaster']
                else:
                    # Assume the dict itself contains the items
                    for key, value in data.items():
                        if isinstance(value, list):
                            items.extend(value)
                            break
            
            if not items:
                print(f"No items found in {file_path}")
                return
                
            print(f"Processing {len(items)} items from {hospital_name}...")
            
            # Process each item
            imported_count = 0
            for i, item in enumerate(items):
                try:
                    if i % 10000 == 0:
                        print(f"  Processed {i}/{len(items)} items...")
                    
                    # Extract description
                    description = (item.get('description') or 
                                 item.get('drug_generic_name') or 
                                 item.get('procedure_name') or 
                                 item.get('service_name') or 
                                 item.get('item_name') or 
                                 str(item.get('code', '')))
                    
                    if not description or len(description.strip()) < 3:
                        continue
                    
                    # Extract codes
                    codes = self.extract_codes(item)
                    
                    # Find or create procedure
                    procedure_id = self.find_or_create_procedure(description, codes)
                    
                    # Extract pricing
                    pricing_info = self.extract_pricing_info(item)
                    
                    if pricing_info['price'] is None and pricing_info['standard_charge'] is None:
                        continue
                    
                    # Insert pricing record
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO pricing (
                            hospital_id, procedure_id, price, min_price, max_price,
                            standard_charge, cash_price, setting, charge_type, billing_class
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        hospital_id, procedure_id,
                        pricing_info['price'], pricing_info['min_price'], pricing_info['max_price'],
                        pricing_info['standard_charge'], pricing_info['cash_price'],
                        pricing_info['setting'], pricing_info['charge_type'], pricing_info['billing_class']
                    ))
                    
                    conn.commit()
                    conn.close()
                    imported_count += 1
                    
                except Exception as e:
                    if i < 10:  # Only print first few errors
                        print(f"Error processing item {i}: {str(e)[:100]}")
                    continue
            
            print(f"Successfully imported {imported_count} records from {hospital_name}")
            
        except Exception as e:
            print(f"Error importing {hospital_name}: {e}")
    
    def import_all_hospitals(self):
        """Import data from all hospital files"""
        hospital_files = [
            ('106010776_ucsf-medical-center_standardcharges.json', 'UCSF Medical Center'),
            ('946174066_stanford-health-care_standardcharges.json', 'Stanford Health Care'),
            ('_sites_default_files_cms-hpt_956006143_ronald-reagan-ucla-medical-center_standardcharges.json', 'UCLA Health'),
            ('951644600_CEDARS-SINAI-MEDICAL-CENTER_STANDARDCHARGES.json', 'Cedars-Sinai Medical Center')
        ]
        
        for file_path, hospital_name in hospital_files:
            if os.path.exists(file_path):
                self.import_hospital_data(file_path, hospital_name)
            else:
                print(f"File not found: {file_path}")
        
        # Print final statistics
        self.print_statistics()
    
    def print_statistics(self):
        """Print database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM hospitals')
        hospitals_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM procedures')
        procedures_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM pricing')
        pricing_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT h.name, COUNT(p.id) as record_count
            FROM hospitals h
            LEFT JOIN pricing p ON h.id = p.hospital_id
            GROUP BY h.id, h.name
            ORDER BY record_count DESC
        ''')
        hospital_stats = cursor.fetchall()
        
        print("\n" + "="*60)
        print("COMPREHENSIVE IMPORT COMPLETE")
        print("="*60)
        print(f"Hospitals: {hospitals_count}")
        print(f"Procedures: {procedures_count}")
        print(f"Pricing Records: {pricing_count}")
        print("\nRecords by Hospital:")
        for name, count in hospital_stats:
            print(f"  {name}: {count:,} records")
        
        conn.close()

if __name__ == "__main__":
    importer = HospitalDataImporter()
    importer.import_all_hospitals() 