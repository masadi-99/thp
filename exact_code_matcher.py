#!/usr/bin/env python3
"""
Exact Code Matcher for Hospital Data
Only includes procedures that have exact code matches across multiple hospitals.
No synthetic or hallucinated data - only real matched codes.
"""

import json
import sqlite3
import os
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict

class ExactCodeMatcher:
    def __init__(self, db_path: str = 'instance/hospital_pricing.db'):
        self.db_path = db_path
        self.ensure_instance_dir()
        self.hospital_data = {}  # Will store all parsed hospital data
        self.code_matches = defaultdict(list)  # code -> list of (hospital, item) tuples
        
    def ensure_instance_dir(self):
        """Ensure instance directory exists"""
        os.makedirs('instance', exist_ok=True)
    
    def init_database(self):
        """Initialize database with clean schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drop existing tables
        cursor.execute('DROP TABLE IF EXISTS pricing')
        cursor.execute('DROP TABLE IF EXISTS procedures')
        cursor.execute('DROP TABLE IF EXISTS hospitals')
        
        # Create hospitals table
        cursor.execute('''
            CREATE TABLE hospitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create procedures table
        cursor.execute('''
            CREATE TABLE procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                code TEXT NOT NULL,
                code_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, code_type)
            )
        ''')
        
        # Create pricing table
        cursor.execute('''
            CREATE TABLE pricing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_id INTEGER NOT NULL,
                procedure_id INTEGER NOT NULL,
                price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                FOREIGN KEY (procedure_id) REFERENCES procedures(id),
                UNIQUE(hospital_id, procedure_id)
            )
        ''')
        
        # Create indices
        cursor.execute('CREATE INDEX idx_procedures_code ON procedures(code, code_type)')
        cursor.execute('CREATE INDEX idx_pricing_lookup ON pricing(hospital_id, procedure_id)')
        
        conn.commit()
        conn.close()
        print("Clean database initialized")
    
    def extract_code_and_type_from_ucsf(self, item: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Extract codes from UCSF format"""
        codes = []
        if 'code_information' in item:
            for code_info in item['code_information']:
                if 'code' in code_info and 'type' in code_info:
                    code_value = str(code_info['code']).strip()
                    code_type = str(code_info['type']).strip().upper()
                    if code_value and code_type:
                        codes.append((code_value, code_type))
        return codes
    
    def extract_code_and_type_from_others(self, item: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Extract codes from other hospitals' format"""
        codes = []
        
        # Priority order for code types
        code_fields = [
            ('code', 'CPT'),
            ('cpt_code', 'CPT'),
            ('hcpcs_code', 'HCPCS'),
            ('ndc_code', 'NDC'),
            ('drg_code', 'DRG'),
            ('revenue_code', 'REV')
        ]
        
        for field_name, code_type in code_fields:
            if field_name in item and item[field_name]:
                code_value = str(item[field_name]).strip()
                if code_value and code_value != 'null' and len(code_value) > 0:
                    codes.append((code_value, code_type))
        
        return codes
    
    def extract_price_from_ucsf(self, item: Dict[str, Any]) -> float:
        """Extract price from UCSF format"""
        if 'standard_charges' in item:
            for charge in item['standard_charges']:
                if 'gross_charge' in charge and charge['gross_charge']:
                    try:
                        value = float(str(charge['gross_charge']).replace('$', '').replace(',', ''))
                        if value > 0:
                            return value
                    except (ValueError, TypeError):
                        continue
        return None
    
    def extract_price_from_others(self, item: Dict[str, Any]) -> float:
        """Extract price from other hospitals' format"""
        price_fields = [
            'gross_charge', 'price', 'amount', 'charge', 'standard_charge',
            'cash_price', 'de_identified_min_negotiated_charge'
        ]
        
        for field in price_fields:
            if field in item and item[field] is not None:
                try:
                    value_str = str(item[field]).replace('$', '').replace(',', '')
                    value = float(value_str)
                    if value > 0:
                        return value
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def load_hospital_data(self, file_path: str, hospital_name: str):
        """Load and parse data from a hospital JSON file"""
        print(f"Loading {hospital_name} from {file_path}...")
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # All hospitals use the same format with standard_charge_information
            items = []
            if 'standard_charge_information' in data:
                items = data['standard_charge_information']
            
            print(f"Found {len(items)} items in {hospital_name}")
            
            # Parse items and group by code
            hospital_items = {}
            processed_count = 0
            
            for i, item in enumerate(items):
                if i % 10000 == 0:
                    print(f"  Processing {i}/{len(items)} items...")
                
                # Extract description
                description = item.get('description', '').strip()
                if not description or len(description) < 3:
                    continue
                
                # Extract codes and price (all hospitals use UCSF format)
                codes = self.extract_code_and_type_from_ucsf(item)
                price = self.extract_price_from_ucsf(item)
                
                if not codes or price is None:
                    continue
                
                # Process each code
                for code_value, code_type in codes:
                    code_key = f"{code_value}|{code_type}"
                    
                    # Store the item (keep the one with best description if duplicate)
                    if code_key not in hospital_items or len(description) > len(hospital_items[code_key]['description']):
                        hospital_items[code_key] = {
                            'code': code_value,
                            'code_type': code_type,
                            'description': description,
                            'price': price,
                            'hospital': hospital_name
                        }
                        processed_count += 1
            
            self.hospital_data[hospital_name] = hospital_items
            print(f"Processed {processed_count} unique coded items from {hospital_name}")
            
        except Exception as e:
            print(f"Error loading {hospital_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def find_code_matches(self):
        """Find codes that appear in multiple hospitals"""
        print("\nFinding code matches across hospitals...")
        
        # Group all items by code+type
        all_codes = defaultdict(list)
        
        for hospital_name, items in self.hospital_data.items():
            for code_key, item in items.items():
                all_codes[code_key].append((hospital_name, item))
        
        # Keep only codes that appear in multiple hospitals
        multi_hospital_codes = {}
        for code_key, hospital_items in all_codes.items():
            if len(hospital_items) >= 2:  # At least 2 hospitals
                multi_hospital_codes[code_key] = hospital_items
        
        self.code_matches = multi_hospital_codes
        print(f"Found {len(multi_hospital_codes)} codes that appear in multiple hospitals")
        
        # Show distribution
        distribution = defaultdict(int)
        for hospital_items in multi_hospital_codes.values():
            distribution[len(hospital_items)] += 1
        
        print("Distribution of codes by hospital count:")
        for count, num_codes in sorted(distribution.items()):
            print(f"  {count} hospitals: {num_codes} codes")
    
    def create_matched_database(self):
        """Create database with only matched codes"""
        print("\nCreating database with matched codes...")
        
        self.init_database()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert hospitals
        hospital_ids = {}
        for hospital_name in self.hospital_data.keys():
            cursor.execute(
                'INSERT INTO hospitals (name) VALUES (?)', 
                (hospital_name,)
            )
            hospital_ids[hospital_name] = cursor.lastrowid
        
        # Insert procedures and pricing
        procedure_count = 0
        pricing_count = 0
        
        for code_key, hospital_items in self.code_matches.items():
            # Use the description from the first item (they should be similar)
            primary_item = hospital_items[0][1]
            
            # Insert procedure
            cursor.execute('''
                INSERT OR IGNORE INTO procedures (description, code, code_type) 
                VALUES (?, ?, ?)
            ''', (
                primary_item['description'],
                primary_item['code'],
                primary_item['code_type']
            ))
            
            cursor.execute(
                'SELECT id FROM procedures WHERE code = ? AND code_type = ?',
                (primary_item['code'], primary_item['code_type'])
            )
            procedure_id = cursor.fetchone()[0]
            
            if cursor.rowcount > 0:  # New procedure was inserted
                procedure_count += 1
            
            # Insert pricing for each hospital
            for hospital_name, item in hospital_items:
                cursor.execute('''
                    INSERT OR IGNORE INTO pricing (hospital_id, procedure_id, price) 
                    VALUES (?, ?, ?)
                ''', (
                    hospital_ids[hospital_name],
                    procedure_id,
                    item['price']
                ))
                
                if cursor.rowcount > 0:  # New pricing was inserted
                    pricing_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"Database created with {procedure_count} procedures and {pricing_count} pricing records")
    
    def print_statistics(self):
        """Print final statistics"""
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
        
        # Code type distribution
        cursor.execute('''
            SELECT code_type, COUNT(*) as count
            FROM procedures
            GROUP BY code_type
            ORDER BY count DESC
        ''')
        code_types = cursor.fetchall()
        
        print("\n" + "="*60)
        print("EXACT CODE MATCHING COMPLETE - VERIFIED REAL DATA ONLY")
        print("="*60)
        print(f"Hospitals: {hospitals_count}")
        print(f"Procedures (with exact code matches): {procedures_count}")
        print(f"Pricing Records: {pricing_count}")
        print("\nPricing records by hospital:")
        for name, count in hospital_stats:
            print(f"  {name}: {count:,} records")
        
        print("\nCode type distribution:")
        for code_type, count in code_types:
            print(f"  {code_type}: {count} procedures")
        
        # Sample some matches
        print("\nSample exact matches (verified real data):")
        cursor.execute('''
            SELECT p.description, p.code, p.code_type, COUNT(pr.hospital_id) as hospital_count
            FROM procedures p
            JOIN pricing pr ON p.id = pr.procedure_id
            GROUP BY p.id
            ORDER BY hospital_count DESC, p.description
            LIMIT 10
        ''')
        samples = cursor.fetchall()
        
        for desc, code, code_type, hosp_count in samples:
            print(f"  {desc[:50]}... (Code: {code}, Type: {code_type}, Hospitals: {hosp_count})")
        
        conn.close()
    
    def run_exact_matching(self):
        """Run the complete exact matching process"""
        hospital_files = [
            ('106010776_ucsf-medical-center_standardcharges.json', 'UCSF Medical Center'),
            ('946174066_stanford-health-care_standardcharges.json', 'Stanford Health Care'),
            ('_sites_default_files_cms-hpt_956006143_ronald-reagan-ucla-medical-center_standardcharges.json', 'UCLA Health'),
            ('951644600_CEDARS-SINAI-MEDICAL-CENTER_STANDARDCHARGES.json', 'Cedars-Sinai Medical Center')
        ]
        
        # Load all hospital data
        for file_path, hospital_name in hospital_files:
            self.load_hospital_data(file_path, hospital_name)
        
        # Find exact matches
        self.find_code_matches()
        
        # Create database
        self.create_matched_database()
        
        # Print statistics
        self.print_statistics()

if __name__ == "__main__":
    matcher = ExactCodeMatcher()
    matcher.run_exact_matching() 