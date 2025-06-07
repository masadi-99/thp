#!/usr/bin/env python3
"""
Improved Hospital Data Matcher
Uses flexible code matching + description matching for better coverage.
Real data only - but with smarter matching logic.
"""

import json
import sqlite3
import os
import re
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
from difflib import SequenceMatcher

class ImprovedMatcher:
    def __init__(self, db_path: str = 'instance/hospital_pricing.db'):
        self.db_path = db_path
        self.ensure_instance_dir()
        self.hospital_data = {}
        self.all_items = []  # Store all items for flexible matching
        
    def ensure_instance_dir(self):
        """Ensure instance directory exists"""
        os.makedirs('instance', exist_ok=True)
    
    def init_database(self):
        """Initialize database with improved schema"""
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
                primary_code TEXT,
                primary_code_type TEXT,
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
                original_code TEXT,
                original_code_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                FOREIGN KEY (procedure_id) REFERENCES procedures(id)
            )
        ''')
        
        # Create indices
        cursor.execute('CREATE INDEX idx_procedures_desc ON procedures(description)')
        cursor.execute('CREATE INDEX idx_procedures_code ON procedures(primary_code)')
        cursor.execute('CREATE INDEX idx_pricing_lookup ON pricing(hospital_id, procedure_id)')
        
        conn.commit()
        conn.close()
        print("Improved database initialized")
    
    def normalize_code(self, code: str) -> str:
        """Normalize codes for flexible matching"""
        if not code:
            return ""
        # Remove common prefixes/suffixes, normalize format
        code = str(code).strip().upper()
        # Remove leading zeros for some code types
        code = re.sub(r'^0+', '', code)
        return code
    
    def extract_all_codes(self, item: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Extract all possible codes from an item"""
        codes = []
        
        # Extract from code_information array (all hospitals use this format)
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
        """Categorize procedures for better grouping"""
        desc_lower = description.lower()
        
        # Common categories
        if any(word in desc_lower for word in ['insulin', 'diabetic', 'glucose']):
            return 'Diabetes Care'
        elif any(word in desc_lower for word in ['antibiotic', 'penicillin', 'amoxicillin', 'azithromycin']):
            return 'Antibiotics'
        elif any(word in desc_lower for word in ['blood pressure', 'hypertension', 'metoprolol', 'lisinopril']):
            return 'Cardiovascular'
        elif any(word in desc_lower for word in ['mri', 'ct scan', 'x-ray', 'ultrasound', 'echo']):
            return 'Imaging'
        elif any(word in desc_lower for word in ['surgery', 'surgical', 'operation']):
            return 'Surgery'
        elif any(word in desc_lower for word in ['lab', 'test', 'analysis', 'panel']):
            return 'Laboratory'
        elif any(word in desc_lower for word in ['vaccine', 'immunization', 'flu shot']):
            return 'Vaccines'
        elif any(word in desc_lower for word in ['pain', 'analgesic', 'morphine', 'oxycodone']):
            return 'Pain Management'
        else:
            return 'Other'
    
    def similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def load_hospital_data(self, file_path: str, hospital_name: str):
        """Load and parse data from a hospital JSON file"""
        print(f"Loading {hospital_name} from {file_path}...")
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            items = []
            if 'standard_charge_information' in data:
                items = data['standard_charge_information']
            
            print(f"Found {len(items)} items in {hospital_name}")
            
            hospital_items = []
            processed_count = 0
            
            for i, item in enumerate(items):
                if i % 10000 == 0:
                    print(f"  Processing {i}/{len(items)} items...")
                
                # Extract description
                description = item.get('description', '').strip()
                if not description or len(description) < 3:
                    continue
                
                # Extract codes and price
                codes = self.extract_all_codes(item)
                price = self.extract_price(item)
                
                if price is None or price <= 0:
                    continue
                
                # Create standardized item
                processed_item = {
                    'hospital': hospital_name,
                    'description': description,
                    'price': price,
                    'codes': codes,
                    'category': self.categorize_procedure(description),
                    'normalized_desc': re.sub(r'[^\w\s]', ' ', description.lower()).strip()
                }
                
                hospital_items.append(processed_item)
                self.all_items.append(processed_item)
                processed_count += 1
            
            self.hospital_data[hospital_name] = hospital_items
            print(f"Processed {processed_count} items from {hospital_name}")
            
        except Exception as e:
            print(f"Error loading {hospital_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def find_matches(self):
        """Find matches using flexible code and description matching"""
        print("\nFinding matches using flexible algorithms...")
        
        matches = []
        processed_descriptions = set()
        
        # Group items by category first for efficiency
        by_category = defaultdict(list)
        for item in self.all_items:
            by_category[item['category']].append(item)
        
        total_procedures = 0
        
        for category, category_items in by_category.items():
            print(f"Processing {category} ({len(category_items)} items)...")
            
            # Group by description similarity within category
            desc_groups = []
            
            for item in category_items:
                desc = item['normalized_desc']
                
                # Skip if we've already processed a very similar description
                skip = False
                for processed_desc in processed_descriptions:
                    if self.similarity_score(desc, processed_desc) > 0.9:
                        skip = True
                        break
                
                if skip:
                    continue
                
                # Find all items with similar descriptions
                similar_items = [item]
                
                for other_item in category_items:
                    if other_item['hospital'] == item['hospital']:
                        continue
                    
                    # Check description similarity
                    desc_similarity = self.similarity_score(desc, other_item['normalized_desc'])
                    
                    # Check code overlap
                    code_overlap = False
                    if item['codes'] and other_item['codes']:
                        item_codes = {self.normalize_code(c[0]) for c in item['codes']}
                        other_codes = {self.normalize_code(c[0]) for c in other_item['codes']}
                        if item_codes & other_codes:  # Any overlap
                            code_overlap = True
                    
                    # Include if high description similarity OR code overlap
                    if desc_similarity > 0.8 or code_overlap:
                        similar_items.append(other_item)
                
                # Only keep if we have items from multiple hospitals
                hospitals_represented = set(item['hospital'] for item in similar_items)
                if len(hospitals_represented) >= 2:
                    desc_groups.append(similar_items)
                    processed_descriptions.add(desc)
                    total_procedures += 1
        
        print(f"Found {total_procedures} matchable procedures across hospitals")
        return desc_groups
    
    def create_improved_database(self):
        """Create database with improved matching results"""
        print("\nCreating improved database...")
        
        self.init_database()
        matches = self.find_matches()
        
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
        
        for match_group in matches:
            # Use the best description (longest, most descriptive)
            best_item = max(match_group, key=lambda x: len(x['description']))
            
            # Get primary code (prefer CPT, then HCPCS, then others)
            primary_code = None
            primary_code_type = None
            
            for item in match_group:
                for code, code_type in item['codes']:
                    if code_type == 'CPT' and not primary_code:
                        primary_code = code
                        primary_code_type = code_type
                        break
                if primary_code:
                    break
            
            if not primary_code:
                for item in match_group:
                    for code, code_type in item['codes']:
                        if code_type == 'HCPCS' and not primary_code:
                            primary_code = code
                            primary_code_type = code_type
                            break
                    if primary_code:
                        break
            
            if not primary_code and match_group[0]['codes']:
                primary_code = match_group[0]['codes'][0][0]
                primary_code_type = match_group[0]['codes'][0][1]
            
            # Insert procedure
            cursor.execute('''
                INSERT INTO procedures (description, primary_code, primary_code_type, category) 
                VALUES (?, ?, ?, ?)
            ''', (
                best_item['description'],
                primary_code,
                primary_code_type,
                best_item['category']
            ))
            procedure_id = cursor.lastrowid
            procedure_count += 1
            
            # Insert pricing for each hospital in the match group
            for item in match_group:
                original_code = item['codes'][0][0] if item['codes'] else None
                original_code_type = item['codes'][0][1] if item['codes'] else None
                
                cursor.execute('''
                    INSERT INTO pricing (hospital_id, procedure_id, price, original_code, original_code_type) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    hospital_ids[item['hospital']],
                    procedure_id,
                    item['price'],
                    original_code,
                    original_code_type
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
        
        # Cross-hospital coverage
        cursor.execute('''
            SELECT COUNT(DISTINCT pr.hospital_id) as hospital_count, COUNT(*) as procedure_count
            FROM procedures p
            JOIN pricing pr ON p.id = pr.procedure_id
            GROUP BY p.id
            HAVING hospital_count > 1
        ''')
        coverage_stats = cursor.fetchall()
        
        multi_hospital_count = len(coverage_stats)
        
        print("\n" + "="*60)
        print("IMPROVED MATCHING COMPLETE - COMPREHENSIVE COVERAGE")
        print("="*60)
        print(f"Hospitals: {hospitals_count}")
        print(f"Procedures (multi-hospital): {procedures_count}")
        print(f"Pricing Records: {pricing_count}")
        print(f"Procedures available across multiple hospitals: {multi_hospital_count}")
        
        print("\nPricing records by hospital:")
        for name, count in hospital_stats:
            print(f"  {name}: {count:,} records")
        
        print("\nProcedures by category:")
        for category, count in categories:
            print(f"  {category}: {count} procedures")
        
        # Sample comparisons
        print("\nSample price comparisons:")
        cursor.execute('''
            SELECT p.description, p.category, COUNT(DISTINCT pr.hospital_id) as hospital_count,
                   MIN(pr.price) as min_price, MAX(pr.price) as max_price
            FROM procedures p
            JOIN pricing pr ON p.id = pr.procedure_id
            GROUP BY p.id
            HAVING hospital_count >= 2
            ORDER BY (max_price - min_price) DESC
            LIMIT 10
        ''')
        samples = cursor.fetchall()
        
        for desc, category, hosp_count, min_price, max_price in samples:
            savings = max_price - min_price
            savings_percent = (savings / max_price) * 100 if max_price > 0 else 0
            print(f"  {desc[:45]}... ({category})")
            print(f"    {hosp_count} hospitals, ${min_price:.2f} - ${max_price:.2f} (save ${savings:.2f}, {savings_percent:.1f}%)")
        
        conn.close()
    
    def run_improved_matching(self):
        """Run the complete improved matching process"""
        hospital_files = [
            ('106010776_ucsf-medical-center_standardcharges.json', 'UCSF Medical Center'),
            ('946174066_stanford-health-care_standardcharges.json', 'Stanford Health Care'),
            ('_sites_default_files_cms-hpt_956006143_ronald-reagan-ucla-medical-center_standardcharges.json', 'UCLA Health'),
            ('951644600_CEDARS-SINAI-MEDICAL-CENTER_STANDARDCHARGES.json', 'Cedars-Sinai Medical Center')
        ]
        
        # Load all hospital data
        for file_path, hospital_name in hospital_files:
            self.load_hospital_data(file_path, hospital_name)
        
        # Create database with improved matching
        self.create_improved_database()
        
        # Print statistics
        self.print_statistics()

if __name__ == "__main__":
    matcher = ImprovedMatcher()
    matcher.run_improved_matching() 