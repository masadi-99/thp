from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Hospital(db.Model):
    __tablename__ = 'hospitals'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255))
    created_at = db.Column(db.String(50), default=datetime.utcnow)
    
    # Relationship
    pricing_records = db.relationship('Pricing', backref='hospital', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'file_name': self.file_name
        }

    def __repr__(self):
        return f'<Hospital {self.name}>'

class Procedure(db.Model):
    __tablename__ = 'procedures'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    code = db.Column(db.String(50))
    code_type = db.Column(db.String(20))
    category = db.Column(db.String(50))
    created_at = db.Column(db.String(50), default=datetime.utcnow)
    
    # Relationship
    pricing_records = db.relationship('Pricing', backref='procedure', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'code': self.code,
            'code_type': self.code_type,
            'category': self.category
        }

    def __repr__(self):
        return f'<Procedure {self.description}>'

class Pricing(db.Model):
    __tablename__ = 'pricing'
    
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    procedure_id = db.Column(db.Integer, db.ForeignKey('procedures.id'), nullable=False)
    price = db.Column(db.Float)
    created_at = db.Column(db.String(50), default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'hospital_id': self.hospital_id,
            'procedure_id': self.procedure_id,
            'price': self.price,
            'hospital_name': self.hospital.name if self.hospital else None,
            'procedure_description': self.procedure.description if self.procedure else None,
            'procedure_code': self.procedure.code if self.procedure else None,
            'procedure_code_type': self.procedure.code_type if self.procedure else None
        }

    def __repr__(self):
        return f'<Pricing {self.hospital_id} - {self.procedure_id}>' 