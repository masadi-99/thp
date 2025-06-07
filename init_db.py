#!/usr/bin/env python3
"""
Database initialization script for Hospital Pricing Transparency Tool
"""

from app import app
from models import db, Hospital, Procedure, PricingData, DataImport

def init_database():
    """Initialize the database and create all tables"""
    with app.app_context():
        # Drop all tables (use with caution in production)
        print("Dropping existing tables...")
        db.drop_all()
        
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        
        print("Database initialized successfully!")
        print("Tables created:")
        print("- hospitals")
        print("- procedures") 
        print("- pricing_data")
        print("- data_imports")

if __name__ == '__main__':
    init_database() 