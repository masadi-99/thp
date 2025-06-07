#!/usr/bin/env python3
"""
Hash Map-Based Hospital Data Matcher
Uses hash maps to efficiently find code matches across hospitals.
Much more comprehensive than previous approaches.
"""

import json
import sqlite3
import os
import re
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict

class HashMatcher:
    def __init__(self, db_path: str = 'instance/hospital_pricing.db'):
        self.db_path = db_path
        self.ensure_instance_dir()
        self.hospital_data = {}
        self.code_to_items = defaultdict(list)  # Hash map: normalized_code -> [items]
        
    def ensure_instance_dir(self):
        """Ensure instance directory exists"""
        os.makedirs('instance', exist_ok=True)
    
    def init_database(self):
        """Initialize database"""
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
                code TEXT,
                code_type TEXT,
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                FOREIGN KEY (procedure_id) REFERENCES procedures(id)
            )
        ''')
        
        # Create indices
        cursor.execute('CREATE INDEX idx_procedures_desc ON procedures(description)')
        cursor.execute('CREATE INDEX idx_procedures_code ON procedures(code)')
        cursor.execute('CREATE INDEX idx_pricing_lookup ON pricing(hospital_id, procedure_id)')
        
        conn.commit()
        conn.close()
        print("Hash database initialized")
    
    def normalize_code(self, code: str, code_type: str) -> str:
        """Normalize codes for better matching"""
        if not code:
            return ""
        
        # Convert to string and clean
        code = str(code).strip().upper()
        
        # Remove common prefixes/formatting variations
        code = re.sub(r'^[0\-\s]+', '', code)  # Remove leading zeros and dashes
        code = re.sub(r'[\-\s\.]', '', code)   # Remove separators
        
        # Normalize based on code type
        if code_type in ['NDC']:
            # NDC codes can have different formats (11-digit, with/without dashes)
            code = re.sub(r'\D', '', code)  # Keep only digits
            if len(code) >= 9:  # Valid NDC should be at least 9 digits
                return f"NDC_{code}"
        elif code_type in ['CPT', 'HCPCS']:
            # CPT/HCPCS codes are usually 5 characters
            if len(code) >= 3:  # Minimum reasonable length
                return f"{code_type}_{code}"
        elif code_type in ['DRG']:
            # DRG codes are usually 3-4 digits
            code = re.sub(r'\D', '', code)  # Keep only digits
            if len(code) >= 2:
                return f"DRG_{code}"
        elif code_type in ['ICD10', 'ICD9']:
            # ICD codes
            return f"{code_type}_{code}"
        else:
            # Generic normalization for other code types
            if len(code) >= 3:
                return f"{code_type}_{code}"
        
        return ""
    
    def extract_codes(self, item: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Extract all codes from item"""
        codes = []
        if 'code_information' in item:
            for code_info in item['code_information']:
                if 'code' in code_info and 'type' in code_info:
                    code_value = str(code_info['code']).strip()
                    code_type = str(code_info['type']).strip().upper()
                    if code_value and code_type:
                        codes.append((code_value, code_type))
        return codes
    
    def extract_price(self, item: Dict[str, Any]) -> float:
        """Extract price from item"""
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
    
    def categorize_procedure(self, description: str) -> str:
        """Categorize procedures"""
        desc_lower = description.lower()
        
        if any(word in desc_lower for word in ['insulin', 'glucose', 'diabetic', 'metformin']):
            return 'Diabetes'
        elif any(word in desc_lower for word in ['mri', 'ct scan', 'ct ', 'x-ray', 'ultrasound', 'imaging', 'scan']):
            return 'Imaging'
        elif any(word in desc_lower for word in ['surgery', 'surgical', 'operation', 'procedure']):
            return 'Surgery'
        elif any(word in desc_lower for word in ['lab', 'test', 'blood', 'analysis', 'panel', 'culture']):
            return 'Laboratory'
        elif any(word in desc_lower for word in ['vaccine', 'immunization', 'vaccination']):
            return 'Vaccines'
        elif any(word in desc_lower for word in ['antibiotic', 'medication', 'drug', 'tablet', 'capsule', 'injection']):
            return 'Medications'
        elif any(word in desc_lower for word in ['cardiology', 'cardiac', 'heart', 'ecg', 'ekg', 'echo']):
            return 'Cardiology'
        else:
            return 'Other'
    
    def load_hospital_data(self, file_path: str, hospital_name: str):
        """Load hospital data and build hash maps"""
        print(f"Loading {hospital_name}...")
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            items = data.get('standard_charge_information', [])
            print(f"Found {len(items)} items")
            
            processed_items = []
            code_count = 0
            
            for i, item in enumerate(items):
                if i % 20000 == 0:
                    print(f"  Processing {i}/{len(items)}...")
                
                description = item.get('description', '').strip()
                if not description or len(description) < 5:
                    continue
                
                codes = self.extract_codes(item)
                price = self.extract_price(item)
                
                if price is None or price <= 0:
                    continue
                
                # Create item with all normalized codes
                normalized_codes = []
                for code_value, code_type in codes:
                    normalized = self.normalize_code(code_value, code_type)
                    if normalized:
                        normalized_codes.append((code_value, code_type, normalized))
                        code_count += 1
                
                if not normalized_codes:
                    continue  # Skip items without valid codes
                
                processed_item = {
                    'hospital': hospital_name,
                    'description': description,
                    'price': price,
                    'original_codes': codes,
                    'normalized_codes': normalized_codes,
                    'category': self.categorize_procedure(description)
                }
                
                processed_items.append(processed_item)
                
                # Add to hash maps for each normalized code
                for _, _, normalized_code in normalized_codes:
                    self.code_to_items[normalized_code].append(processed_item)
            
            self.hospital_data[hospital_name] = processed_items
            print(f"Processed {len(processed_items)} items with {code_count} valid codes")
            
        except Exception as e:
            print(f"Error loading {hospital_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def find_code_matches(self):
        """Find matches using hash maps"""
        print(f"\nAnalyzing {len(self.code_to_items)} unique codes...")
        
        matches = []
        
        for normalized_code, items in self.code_to_items.items():
            # Group items by hospital
            hospitals_with_items = defaultdict(list)
            for item in items:
                hospitals_with_items[item['hospital']].append(item)
            
            # Only keep codes that appear in multiple hospitals
            if len(hospitals_with_items) >= 2:
                # For each hospital, pick the best representative item
                representative_items = []
                for hospital, hospital_items in hospitals_with_items.items():
                    # Pick item with longest description as representative
                    best_item = max(hospital_items, key=lambda x: len(x['description']))
                    representative_items.append(best_item)
                
                matches.append({
                    'code': normalized_code,
                    'items': representative_items,
                    'hospital_count': len(hospitals_with_items),
                    'total_items': len(items)
                })
        
        print(f"Found {len(matches)} codes that appear in multiple hospitals")
        
        # Sort by hospital count (most coverage first)
        matches.sort(key=lambda x: x['hospital_count'], reverse=True)
        
        # Show distribution
        distribution = defaultdict(int)
        for match in matches:
            distribution[match['hospital_count']] += 1
        
        print("Hospital coverage distribution:")
        for hospital_count in sorted(distribution.keys(), reverse=True):
            count = distribution[hospital_count]
            print(f"  {hospital_count} hospitals: {count} codes")
        
        return matches
    
    def create_database_from_matches(self, matches):
        """Create database from hash map matches"""
        print(f"\nCreating database from {len(matches)} matches...")
        
        self.init_database()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert hospitals
        hospital_ids = {}
        for hospital_name in self.hospital_data.keys():
            cursor.execute('INSERT INTO hospitals (name) VALUES (?)', (hospital_name,))
            hospital_ids[hospital_name] = cursor.lastrowid
        
        # Insert procedures and pricing
        procedure_count = 0
        pricing_count = 0
        
        for match in matches:
            items = match['items']
            
            # Use the item with the longest description
            best_item = max(items, key=lambda x: len(x['description']))
            
            # Get the original code that led to this match
            original_code = None
            original_code_type = None
            if best_item['original_codes']:
                original_code = best_item['original_codes'][0][0]
                original_code_type = best_item['original_codes'][0][1]
            
            # Insert procedure
            cursor.execute('''
                INSERT INTO procedures (description, code, code_type, category) 
                VALUES (?, ?, ?, ?)
            ''', (
                best_item['description'],
                original_code,
                original_code_type,
                best_item['category']
            ))
            procedure_id = cursor.lastrowid
            procedure_count += 1
            
            # Insert pricing for each hospital
            for item in items:
                cursor.execute('''
                    INSERT INTO pricing (hospital_id, procedure_id, price) 
                    VALUES (?, ?, ?)
                ''', (
                    hospital_ids[item['hospital']],
                    procedure_id,
                    item['price']
                ))
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
        
        # Hospital distribution
        cursor.execute('''
            SELECT h.name, COUNT(p.id) as record_count
            FROM hospitals h
            LEFT JOIN pricing p ON h.id = p.hospital_id
            GROUP BY h.id, h.name
            ORDER BY record_count DESC
        ''')
        hospital_stats = cursor.fetchall()
        
        # Category distribution
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM procedures
            GROUP BY category
            ORDER BY count DESC
        ''')
        categories = cursor.fetchall()
        
        # Multi-hospital procedures
        cursor.execute('''
            SELECT COUNT(DISTINCT pr.hospital_id) as hospital_count
            FROM procedures p
            JOIN pricing pr ON p.id = pr.procedure_id
            GROUP BY p.id
            HAVING hospital_count >= 2
        ''')
        multi_hospital = len(cursor.fetchall())
        
        print("\n" + "="*60)
        print("HASH MAP MATCHING COMPLETE")
        print("="*60)
        print(f"Hospitals: {hospitals_count}")
        print(f"Procedures: {procedures_count}")
        print(f"Pricing Records: {pricing_count}")
        print(f"Multi-hospital procedures: {multi_hospital}")
        
        print("\nPricing records by hospital:")
        for name, count in hospital_stats:
            print(f"  {name}: {count:,} records")
        
        print("\nProcedures by category:")
        for category, count in categories:
            print(f"  {category}: {count} procedures")
        
        # Sample high-savings comparisons
        print("\nTop savings opportunities:")
        cursor.execute('''
            SELECT p.description, p.category, COUNT(DISTINCT pr.hospital_id) as hospital_count,
                   MIN(pr.price) as min_price, MAX(pr.price) as max_price
            FROM procedures p
            JOIN pricing pr ON p.id = pr.procedure_id
            GROUP BY p.id
            HAVING hospital_count >= 2
            ORDER BY (max_price - min_price) DESC
            LIMIT 15
        ''')
        samples = cursor.fetchall()
        
        for desc, category, hosp_count, min_price, max_price in samples:
            savings = max_price - min_price
            savings_percent = (savings / max_price) * 100 if max_price > 0 else 0
            print(f"  {desc[:45]}... ({category})")
            print(f"    {hosp_count} hospitals: ${min_price:.2f} - ${max_price:.2f} (save ${savings:.2f}, {savings_percent:.1f}%)")
        
        conn.close()
    
    def run(self):
        """Run the hash map matching process"""
        hospital_files = [
            ('106010776_ucsf-medical-center_standardcharges.json', 'UCSF Medical Center'),
            ('946174066_stanford-health-care_standardcharges.json', 'Stanford Health Care'),
            ('_sites_default_files_cms-hpt_956006143_ronald-reagan-ucla-medical-center_standardcharges.json', 'UCLA Health'),
            ('951644600_CEDARS-SINAI-MEDICAL-CENTER_STANDARDCHARGES.json', 'Cedars-Sinai Medical Center')
        ]
        
        # Load data and build hash maps
        for file_path, hospital_name in hospital_files:
            self.load_hospital_data(file_path, hospital_name)
        
        # Find matches using hash maps
        matches = self.find_code_matches()
        
        # Create database
        self.create_database_from_matches(matches)
        
        # Print statistics
        self.print_statistics()

if __name__ == "__main__":
    matcher = HashMatcher()
    matcher.run() 