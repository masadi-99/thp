#!/usr/bin/env python3
"""
Fast Hospital Data Matcher
Uses efficient code-based grouping + selective description matching.
Much faster than the previous approach.
"""

import json
import sqlite3
import os
import re
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict

class FastMatcher:
    def __init__(self, db_path: str = 'instance/hospital_pricing.db'):
        self.db_path = db_path
        self.ensure_instance_dir()
        self.hospital_data = {}
        
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
        print("Fast database initialized")
    
    def extract_codes(self, item: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Extract codes from item"""
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
        
        if any(word in desc_lower for word in ['insulin', 'glucose', 'diabetic']):
            return 'Diabetes'
        elif any(word in desc_lower for word in ['mri', 'ct scan', 'x-ray', 'ultrasound', 'imaging']):
            return 'Imaging'
        elif any(word in desc_lower for word in ['surgery', 'surgical', 'operation']):
            return 'Surgery'
        elif any(word in desc_lower for word in ['lab', 'test', 'blood', 'analysis']):
            return 'Laboratory'
        elif any(word in desc_lower for word in ['vaccine', 'immunization']):
            return 'Vaccines'
        elif any(word in desc_lower for word in ['antibiotic', 'medication', 'drug']):
            return 'Medications'
        else:
            return 'Other'
    
    def normalize_description(self, desc: str) -> str:
        """Normalize description for matching"""
        # Remove special characters, normalize spacing
        desc = re.sub(r'[^\w\s]', ' ', desc.lower())
        desc = re.sub(r'\s+', ' ', desc).strip()
        return desc
    
    def description_similarity(self, desc1: str, desc2: str) -> bool:
        """Fast description similarity check"""
        # Split into words and check for significant overlap
        words1 = set(desc1.split())
        words2 = set(desc2.split())
        
        # Filter out common words
        common_words = {'mg', 'ml', 'unit', 'dose', 'tablet', 'injection', 'solution', 'each', 'per', 'of', 'for', 'with', 'and', 'or', 'the', 'a', 'an'}
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if not words1 or not words2:
            return False
        
        # Check for significant word overlap
        overlap = len(words1 & words2)
        min_words = min(len(words1), len(words2))
        
        return overlap >= max(2, min_words * 0.6)  # At least 60% overlap
    
    def load_hospital_data(self, file_path: str, hospital_name: str):
        """Load hospital data efficiently"""
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
                
                processed_items.append({
                    'hospital': hospital_name,
                    'description': description,
                    'normalized_desc': self.normalize_description(description),
                    'price': price,
                    'codes': codes,
                    'category': self.categorize_procedure(description)
                })
            
            self.hospital_data[hospital_name] = processed_items
            print(f"Processed {len(processed_items)} valid items")
            
        except Exception as e:
            print(f"Error loading {hospital_name}: {e}")
    
    def find_matches_fast(self):
        """Fast matching algorithm"""
        print("\nFinding matches using fast algorithm...")
        
        # First, group by exact code matches
        code_groups = defaultdict(list)
        no_code_items = []
        
        for hospital_name, items in self.hospital_data.items():
            for item in items:
                if item['codes']:
                    # Use the first code as primary
                    primary_code = f"{item['codes'][0][0]}|{item['codes'][0][1]}"
                    code_groups[primary_code].append(item)
                else:
                    no_code_items.append(item)
        
        matches = []
        
        # Process exact code matches
        exact_matches = 0
        for code, items in code_groups.items():
            hospitals = set(item['hospital'] for item in items)
            if len(hospitals) >= 2:
                matches.append(items)
                exact_matches += 1
        
        print(f"Found {exact_matches} exact code matches")
        
        # Process items without codes by description similarity within categories
        print("Processing items without codes...")
        by_category = defaultdict(list)
        for item in no_code_items:
            by_category[item['category']].append(item)
        
        desc_matches = 0
        for category, items in by_category.items():
            if len(items) < 2:
                continue
                
            print(f"  Processing {category}: {len(items)} items")
            
            # Group by similar descriptions
            grouped = []
            for item in items:
                placed = False
                for group in grouped:
                    if self.description_similarity(item['normalized_desc'], group[0]['normalized_desc']):
                        group.append(item)
                        placed = True
                        break
                
                if not placed:
                    grouped.append([item])
            
            # Keep groups with multiple hospitals
            for group in grouped:
                hospitals = set(item['hospital'] for item in group)
                if len(hospitals) >= 2:
                    matches.append(group)
                    desc_matches += 1
        
        print(f"Found {desc_matches} description-based matches")
        print(f"Total matches: {len(matches)}")
        
        return matches
    
    def create_database(self):
        """Create database with matched procedures"""
        print("\nCreating database...")
        
        self.init_database()
        matches = self.find_matches_fast()
        
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
            # Use the best description
            best_item = max(match_group, key=lambda x: len(x['description']))
            
            # Get primary code
            primary_code = None
            primary_code_type = None
            for item in match_group:
                if item['codes']:
                    primary_code = item['codes'][0][0]
                    primary_code_type = item['codes'][0][1]
                    break
            
            # Insert procedure
            cursor.execute('''
                INSERT INTO procedures (description, code, code_type, category) 
                VALUES (?, ?, ?, ?)
            ''', (
                best_item['description'],
                primary_code,
                primary_code_type,
                best_item['category']
            ))
            procedure_id = cursor.lastrowid
            procedure_count += 1
            
            # Insert pricing for each hospital
            for item in match_group:
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
        """Print statistics"""
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
        print("FAST MATCHING COMPLETE")
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
        
        # Sample comparisons
        print("\nTop price differences:")
        cursor.execute('''
            SELECT p.description, COUNT(DISTINCT pr.hospital_id) as hospital_count,
                   MIN(pr.price) as min_price, MAX(pr.price) as max_price
            FROM procedures p
            JOIN pricing pr ON p.id = pr.procedure_id
            GROUP BY p.id
            HAVING hospital_count >= 2
            ORDER BY (max_price - min_price) DESC
            LIMIT 10
        ''')
        samples = cursor.fetchall()
        
        for desc, hosp_count, min_price, max_price in samples:
            savings = max_price - min_price
            savings_percent = (savings / max_price) * 100 if max_price > 0 else 0
            print(f"  {desc[:50]}...")
            print(f"    {hosp_count} hospitals: ${min_price:.2f} - ${max_price:.2f} (save ${savings:.2f}, {savings_percent:.1f}%)")
        
        conn.close()
    
    def run(self):
        """Run the fast matching process"""
        hospital_files = [
            ('106010776_ucsf-medical-center_standardcharges.json', 'UCSF Medical Center'),
            ('946174066_stanford-health-care_standardcharges.json', 'Stanford Health Care'),
            ('_sites_default_files_cms-hpt_956006143_ronald-reagan-ucla-medical-center_standardcharges.json', 'UCLA Health'),
            ('951644600_CEDARS-SINAI-MEDICAL-CENTER_STANDARDCHARGES.json', 'Cedars-Sinai Medical Center')
        ]
        
        # Load data
        for file_path, hospital_name in hospital_files:
            self.load_hospital_data(file_path, hospital_name)
        
        # Create database
        self.create_database()
        
        # Print statistics
        self.print_statistics()

if __name__ == "__main__":
    matcher = FastMatcher()
    matcher.run() 