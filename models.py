from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Hospital(db.Model):
    """Hospital model to store hospital information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    zip_code = db.Column(db.String(10))
    system = db.Column(db.String(200))  # Hospital system/network
    ein = db.Column(db.String(20))  # Employer Identification Number
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    pricing_data = db.relationship('PricingData', backref='hospital', lazy=True)
    
    def __repr__(self):
        return f'<Hospital {self.name}>'

class Procedure(db.Model):
    """Procedure model to store medical procedures and services"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    code = db.Column(db.String(50))  # CPT, HCPCS, DRG, or other codes
    code_type = db.Column(db.String(20))  # CPT, HCPCS, DRG, etc.
    category = db.Column(db.String(100))  # Surgery, Imaging, Lab, etc.
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    pricing_data = db.relationship('PricingData', backref='procedure', lazy=True)
    
    def __repr__(self):
        return f'<Procedure {self.name} ({self.code})>'

class PricingData(db.Model):
    """Pricing data model to store hospital pricing information"""
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    procedure_id = db.Column(db.Integer, db.ForeignKey('procedure.id'), nullable=False)
    
    # Pricing information
    cash_price = db.Column(db.Numeric(10, 2))  # Self-pay/cash price
    min_negotiated_rate = db.Column(db.Numeric(10, 2))  # Minimum negotiated rate
    max_negotiated_rate = db.Column(db.Numeric(10, 2))  # Maximum negotiated rate
    
    # Payer-specific rates (stored as JSON)
    payer_specific_rates = db.Column(db.Text)  # JSON string of payer rates
    
    # Metadata
    effective_date = db.Column(db.Date)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    data_source = db.Column(db.String(200))  # Source of the pricing data
    
    def get_payer_rates(self):
        """Parse payer-specific rates from JSON"""
        if self.payer_specific_rates:
            try:
                return json.loads(self.payer_specific_rates)
            except:
                return {}
        return {}
    
    def set_payer_rates(self, rates_dict):
        """Set payer-specific rates as JSON"""
        self.payer_specific_rates = json.dumps(rates_dict)
    
    def __repr__(self):
        return f'<PricingData Hospital:{self.hospital_id} Procedure:{self.procedure_id}>'

class DataImport(db.Model):
    """Track data import sessions"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'))
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    records_imported = db.Column(db.Integer, default=0)
    records_failed = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed
    error_log = db.Column(db.Text)
    
    def __repr__(self):
        return f'<DataImport {self.filename} - {self.status}>' 