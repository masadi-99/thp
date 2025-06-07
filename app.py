from flask import Flask, render_template, jsonify, request
import plotly.graph_objs as go
import plotly.utils
from models import db, Hospital, Procedure, PricingData
from sqlalchemy import func, or_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital_pricing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def index():
    """Home page with hospital pricing comparison tool"""
    return render_template('index.html')

@app.route('/api/hospitals')
def get_hospitals():
    """Get list of all hospitals"""
    hospitals = Hospital.query.all()
    return jsonify([hospital.to_dict() for hospital in hospitals])

@app.route('/api/procedures')
def get_procedures():
    """
    Search procedures by name/description.
    Returns procedures that have actual pricing data available.
    """
    search = request.args.get('search', '').strip()
    limit = int(request.args.get('limit', 50))
    
    query = Procedure.query.join(PricingData)
    
    if search:
        # Case-insensitive search in name and description
        search_filter = or_(
            Procedure.name.ilike(f'%{search}%'),
            Procedure.description.ilike(f'%{search}%'),
            Procedure.code.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    # Only return procedures with actual pricing data
    query = query.filter(
        or_(
            PricingData.cash_price.isnot(None),
            PricingData.gross_charge.isnot(None)
        )
    ).distinct()
    
    procedures = query.limit(limit).all()
    
    return jsonify([{
        **procedure.to_dict(),
        'hospital_count': PricingData.query.filter_by(procedure_id=procedure.id).count()
    } for procedure in procedures])

@app.route('/api/pricing/<int:procedure_id>')
def get_pricing_for_procedure(procedure_id):
    """
    Get pricing information for a specific procedure across all hospitals.
    Note: Returns only cash prices and gross charges - no insurance rates available.
    """
    procedure = Procedure.query.get_or_404(procedure_id)
    
    pricing_data = PricingData.query.filter_by(procedure_id=procedure_id).all()
    
    result = {
        'procedure': procedure.to_dict(),
        'pricing_by_hospital': [],
        'data_notes': {
            'available': [
                'Cash/Self-pay prices (what uninsured patients pay)',
                'Hospital gross charges (standard "list" prices)',
                'Price ranges where available'
            ],
            'not_available': [
                'Insurance negotiated rates (not in transparency files)',
                'Real payer-specific pricing (only placeholder text exists)'
            ],
            'explanation': 'Hospital transparency files contain cash prices and gross charges, but do not include actual insurance negotiated rates despite having payer information sections.'
        }
    }
    
    for pricing in pricing_data:
        hospital_pricing = {
            'hospital': pricing.hospital.to_dict(),
            'pricing': {
                'cash_price': pricing.cash_price,
                'gross_charge': pricing.gross_charge,
                'price_range': {
                    'min': pricing.min_rate,
                    'max': pricing.max_rate
                }
            },
            'last_updated': pricing.last_updated.isoformat() if pricing.last_updated else None
        }
        result['pricing_by_hospital'].append(hospital_pricing)
    
    return jsonify(result)

@app.route('/api/compare')
def compare_procedures():
    """
    Compare multiple procedures across selected hospitals.
    Returns only available pricing data (cash prices and gross charges).
    """
    procedure_ids = request.args.getlist('procedures[]')
    hospital_ids = request.args.getlist('hospitals[]')
    
    if not procedure_ids:
        return jsonify({'error': 'No procedures specified'}), 400
    
    # Convert to integers
    try:
        procedure_ids = [int(id) for id in procedure_ids]
        hospital_ids = [int(id) for id in hospital_ids] if hospital_ids else []
    except ValueError:
        return jsonify({'error': 'Invalid ID format'}), 400
    
    query = PricingData.query.filter(PricingData.procedure_id.in_(procedure_ids))
    
    if hospital_ids:
        query = query.filter(PricingData.hospital_id.in_(hospital_ids))
    
    pricing_data = query.all()
    
    # Group by procedure
    comparison = {}
    for pricing in pricing_data:
        proc_id = pricing.procedure_id
        if proc_id not in comparison:
            comparison[proc_id] = {
                'procedure': pricing.procedure.to_dict(),
                'hospitals': []
            }
        
        comparison[proc_id]['hospitals'].append({
            'hospital': pricing.hospital.to_dict(),
            'cash_price': pricing.cash_price,
            'gross_charge': pricing.gross_charge,
            'price_range': {
                'min': pricing.min_rate,
                'max': pricing.max_rate
            }
        })
    
    return jsonify({
        'comparison': list(comparison.values()),
        'data_notes': {
            'pricing_types': {
                'cash_price': 'Discounted price for self-pay/uninsured patients',
                'gross_charge': 'Hospital standard charge (list price)',
                'price_range': 'Min/max from all available pricing data'
            },
            'limitations': 'Insurance negotiated rates are not available in hospital transparency files'
        }
    })

@app.route('/api/chart/<int:procedure_id>')
def get_pricing_chart(procedure_id):
    """
    Generate a chart comparing cash prices and gross charges across hospitals.
    """
    procedure = Procedure.query.get_or_404(procedure_id)
    pricing_data = PricingData.query.filter_by(procedure_id=procedure_id).all()
    
    if not pricing_data:
        return jsonify({'error': 'No pricing data available'}), 404
    
    hospitals = []
    cash_prices = []
    gross_charges = []
    
    for pricing in pricing_data:
        hospitals.append(pricing.hospital.name)
        cash_prices.append(pricing.cash_price or 0)
        gross_charges.append(pricing.gross_charge or 0)
    
    # Create plotly chart
    fig = go.Figure()
    
    # Add cash price bars
    fig.add_trace(go.Bar(
        name='Cash Price',
        x=hospitals,
        y=cash_prices,
        marker_color='lightblue',
        text=[f'${price:,.0f}' if price > 0 else 'N/A' for price in cash_prices],
        textposition='auto'
    ))
    
    # Add gross charge bars
    fig.add_trace(go.Bar(
        name='Gross Charge',
        x=hospitals,
        y=gross_charges,
        marker_color='lightcoral',
        text=[f'${price:,.0f}' if price > 0 else 'N/A' for price in gross_charges],
        textposition='auto'
    ))
    
    fig.update_layout(
        title=f'Pricing Comparison: {procedure.name}',
        xaxis_title='Hospital',
        yaxis_title='Price ($)',
        barmode='group',
        template='plotly_white',
        annotations=[
            dict(
                text='Note: Insurance negotiated rates not available in transparency data',
                showarrow=False,
                xref="paper", yref="paper",
                x=0.5, y=-0.1, xanchor='center', yanchor='top',
                font=dict(size=10, color='gray')
            )
        ]
    )
    
    graphJSON = plotly.utils.PlotlyJSONEncoder().encode(fig)
    return jsonify({'chart': graphJSON})

@app.route('/api/stats')
def get_statistics():
    """Get database statistics and data quality information"""
    with db.session() as session:
        stats = {
            'hospitals': session.query(Hospital).count(),
            'procedures': session.query(Procedure).count(),
            'pricing_records': session.query(PricingData).count(),
            'records_with_cash_price': session.query(PricingData).filter(PricingData.cash_price.isnot(None)).count(),
            'records_with_gross_charge': session.query(PricingData).filter(PricingData.gross_charge.isnot(None)).count(),
            'shared_procedures': session.query(PricingData.procedure_id).group_by(PricingData.procedure_id).having(func.count(PricingData.hospital_id) > 1).count()
        }
    
    return jsonify({
        'statistics': stats,
        'data_quality': {
            'cash_price_coverage': f"{stats['records_with_cash_price'] / stats['pricing_records'] * 100:.1f}%" if stats['pricing_records'] > 0 else '0%',
            'gross_charge_coverage': f"{stats['records_with_gross_charge'] / stats['pricing_records'] * 100:.1f}%" if stats['pricing_records'] > 0 else '0%',
            'shared_procedures_count': stats['shared_procedures']
        },
        'data_limitations': [
            'Insurance negotiated rates are not available in hospital transparency files',
            'Payer information sections contain only placeholder text',
            'Actual reimbursement rates vary significantly from published prices'
        ]
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001) 