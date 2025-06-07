from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
from models import db, Hospital, Procedure, PricingData
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital_pricing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def index():
    """Main dashboard for hospital pricing comparison"""
    return render_template('index.html')

@app.route('/api/hospitals')
def get_hospitals():
    """API endpoint to get all hospitals"""
    hospitals = Hospital.query.all()
    return jsonify([{
        'id': h.id,
        'name': h.name,
        'location': h.location,
        'system': h.system
    } for h in hospitals])

@app.route('/api/procedures')
def get_procedures():
    """API endpoint to search procedures"""
    search_term = request.args.get('search', '')
    
    if search_term:
        procedures = Procedure.query.filter(
            Procedure.name.ilike(f'%{search_term}%')
        ).all()
    else:
        procedures = Procedure.query.limit(50).all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'code': p.code,
        'category': p.category
    } for p in procedures])

@app.route('/api/pricing/<int:procedure_id>')
def get_pricing(procedure_id):
    """Get pricing data for a specific procedure across hospitals"""
    pricing_data = db.session.query(
        PricingData, Hospital, Procedure
    ).join(Hospital).join(Procedure).filter(
        Procedure.id == procedure_id
    ).all()
    
    result = []
    for pricing, hospital, procedure in pricing_data:
        result.append({
            'hospital_name': hospital.name,
            'hospital_location': hospital.location,
            'procedure_name': procedure.name,
            'cash_price': pricing.cash_price,
            'min_negotiated_rate': pricing.min_negotiated_rate,
            'max_negotiated_rate': pricing.max_negotiated_rate,
            'payer_specific_rates': pricing.payer_specific_rates
        })
    
    return jsonify(result)

@app.route('/api/compare')
def compare_prices():
    """Compare prices for multiple procedures across selected hospitals"""
    procedure_ids = request.args.getlist('procedures[]')
    hospital_ids = request.args.getlist('hospitals[]')
    
    if not procedure_ids or not hospital_ids:
        return jsonify({'error': 'Please select at least one procedure and one hospital'})
    
    # Query pricing data
    pricing_data = db.session.query(
        PricingData, Hospital, Procedure
    ).join(Hospital).join(Procedure).filter(
        Procedure.id.in_(procedure_ids),
        Hospital.id.in_(hospital_ids)
    ).all()
    
    # Organize data for comparison
    comparison_data = {}
    for pricing, hospital, procedure in pricing_data:
        proc_key = f"{procedure.name} ({procedure.code})"
        if proc_key not in comparison_data:
            comparison_data[proc_key] = []
        
        comparison_data[proc_key].append({
            'hospital': hospital.name,
            'location': hospital.location,
            'cash_price': pricing.cash_price,
            'min_rate': pricing.min_negotiated_rate,
            'max_rate': pricing.max_negotiated_rate
        })
    
    return jsonify(comparison_data)

@app.route('/api/chart/<int:procedure_id>')
def get_price_chart(procedure_id):
    """Generate price comparison chart for a specific procedure"""
    pricing_data = db.session.query(
        PricingData, Hospital, Procedure
    ).join(Hospital).join(Procedure).filter(
        Procedure.id == procedure_id
    ).all()
    
    if not pricing_data:
        return jsonify({'error': 'No pricing data found'})
    
    hospitals = []
    cash_prices = []
    min_rates = []
    max_rates = []
    
    for pricing, hospital, procedure in pricing_data:
        hospitals.append(hospital.name[:20] + '...' if len(hospital.name) > 20 else hospital.name)
        cash_prices.append(pricing.cash_price or 0)
        min_rates.append(pricing.min_negotiated_rate or 0)
        max_rates.append(pricing.max_negotiated_rate or 0)
    
    # Create plotly chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Cash Price',
        x=hospitals,
        y=cash_prices,
        marker_color='lightblue'
    ))
    
    fig.add_trace(go.Bar(
        name='Min Negotiated Rate',
        x=hospitals,
        y=min_rates,
        marker_color='lightgreen'
    ))
    
    fig.add_trace(go.Bar(
        name='Max Negotiated Rate',
        x=hospitals,
        y=max_rates,
        marker_color='lightcoral'
    ))
    
    fig.update_layout(
        title=f'Price Comparison: {pricing_data[0][2].name}',
        xaxis_title='Hospitals',
        yaxis_title='Price ($)',
        barmode='group',
        height=500
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return jsonify(graphJSON)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001) 