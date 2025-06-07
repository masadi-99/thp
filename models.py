from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Hospital(db.Model):
    """Hospital model to store hospital information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    pricing_data = db.relationship('PricingData', backref='hospital', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location
        }

    def __repr__(self):
        return f'<Hospital {self.name}>'

class Procedure(db.Model):
    """Procedure model to store medical procedures and services"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    code = db.Column(db.String(50))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    pricing_data = db.relationship('PricingData', backref='procedure', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description
        }

    def __repr__(self):
        return f'<Procedure {self.name}>'

class PricingData(db.Model):
    """
    Pricing data model for hospital transparency information.
    
    Note: Real insurance negotiated rates are NOT available in hospital 
    transparency files. All payer information only contains placeholder text.
    This model reflects what we actually have: cash prices and gross charges.
    """
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    procedure_id = db.Column(db.Integer, db.ForeignKey('procedure.id'), nullable=False)
    
    # What we actually have from transparency files:
    cash_price = db.Column(db.Float)  # Discounted cash/self-pay price
    gross_charge = db.Column(db.Float)  # Hospital's "list price" (standard charge)
    
    # Derived pricing ranges
    min_rate = db.Column(db.Float)  # Minimum price from available data
    max_rate = db.Column(db.Float)  # Maximum price from available data
    
    # Metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    data_source = db.Column(db.String(200))  # Source of the pricing data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'hospital_id': self.hospital_id,
            'procedure_id': self.procedure_id,
            'cash_price': self.cash_price,
            'gross_charge': self.gross_charge,
            'min_rate': self.min_rate,
            'max_rate': self.max_rate,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'hospital': self.hospital.to_dict() if self.hospital else None,
            'procedure': self.procedure.to_dict() if self.procedure else None
        }

    def __repr__(self):
        return f'<PricingData Hospital:{self.hospital_id} Procedure:{self.procedure_id}>' 