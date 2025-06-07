import os
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from models import db, Hospital, Procedure, Pricing
import plotly.graph_objs as go
import plotly.utils
from sqlalchemy import or_, and_, func
import json

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    
    # Database configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "hospital_pricing.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    
    @app.route('/')
    def index():
        """Main dashboard page"""
        return render_template('index.html')
    
    @app.route('/api/stats')
    def get_stats():
        """Get overall statistics"""
        try:
            hospitals_count = Hospital.query.count()
            procedures_count = Procedure.query.count()
            pricing_count = Pricing.query.count()
            
            # Code type distribution
            code_types = db.session.query(
                Procedure.code_type, 
                func.count(Procedure.id).label('count')
            ).group_by(Procedure.code_type).all()
            
            # Hospital pricing distribution
            hospital_pricing = db.session.query(
                Hospital.name,
                func.count(Pricing.id).label('count')
            ).join(Pricing).group_by(Hospital.id).all()
            
            return jsonify({
                'hospitals': hospitals_count,
                'procedures': procedures_count,
                'pricing_records': pricing_count,
                'code_types': [{'type': ct[0], 'count': ct[1]} for ct in code_types],
                'hospital_pricing': [{'hospital': hp[0], 'count': hp[1]} for hp in hospital_pricing]
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/hospitals')
    def get_hospitals():
        """Get all hospitals"""
        try:
            hospitals = Hospital.query.all()
            return jsonify([h.to_dict() for h in hospitals])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/procedures')
    def search_procedures():
        """Search procedures by description, code, or code type"""
        try:
            search_term = request.args.get('search', '').strip()
            limit = min(int(request.args.get('limit', 50)), 100)
            
            if not search_term:
                return jsonify({'error': 'Search term required'}), 400
            
            # Search in description, code
            search_pattern = f'%{search_term}%'
            procedures = db.session.query(Procedure)\
                .filter(or_(
                    Procedure.description.ilike(search_pattern),
                    Procedure.code.ilike(search_pattern)
                ))\
                .limit(limit)\
                .all()
            
            results = []
            for proc in procedures:
                # Get pricing data for this procedure
                pricing_data = db.session.query(Pricing, Hospital)\
                    .join(Hospital)\
                    .filter(Pricing.procedure_id == proc.id)\
                    .all()
                
                hospitals_with_pricing = []
                for pricing, hospital in pricing_data:
                    hospitals_with_pricing.append({
                        'hospital_name': hospital.name,
                        'price': pricing.price
                    })
                
                results.append({
                    'id': proc.id,
                    'description': proc.description,
                    'code': proc.code,
                    'code_type': proc.code_type,
                    'hospital_count': len(hospitals_with_pricing),
                    'hospitals': hospitals_with_pricing
                })
            
            return jsonify(results)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/pricing/<int:procedure_id>')
    def get_pricing(procedure_id):
        """Get pricing data for a specific procedure"""
        try:
            procedure = Procedure.query.get_or_404(procedure_id)
            
            # Get all pricing data for this procedure
            pricing_data = db.session.query(Pricing, Hospital)\
                .join(Hospital)\
                .filter(Pricing.procedure_id == procedure_id)\
                .all()
            
            hospitals = []
            for pricing, hospital in pricing_data:
                hospitals.append({
                    'hospital_id': hospital.id,
                    'hospital_name': hospital.name,
                    'price': pricing.price
                })
            
            return jsonify({
                'procedure': procedure.to_dict(),
                'hospitals': hospitals
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/chart/<int:procedure_id>')
    def get_chart(procedure_id):
        """Generate price comparison chart for a procedure"""
        try:
            procedure = Procedure.query.get_or_404(procedure_id)
            
            # Get pricing data
            pricing_data = db.session.query(Pricing, Hospital)\
                .join(Hospital)\
                .filter(Pricing.procedure_id == procedure_id)\
                .order_by(Pricing.price)\
                .all()
            
            if not pricing_data:
                return jsonify({'error': 'No pricing data found'}), 404
            
            hospitals = [hospital.name for _, hospital in pricing_data]
            prices = [pricing.price for pricing, _ in pricing_data]
            
            # Create bar chart
            fig = go.Figure(data=[
                go.Bar(
                    x=hospitals,
                    y=prices,
                    text=[f'${price:,.2f}' for price in prices],
                    textposition='auto',
                    marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'][:len(hospitals)]
                )
            ])
            
            fig.update_layout(
                title=f'Price Comparison: {procedure.description[:60]}...',
                xaxis_title='Hospital',
                yaxis_title='Price ($)',
                template='plotly_white',
                height=400
            )
            
            # Calculate savings
            if len(prices) > 1:
                min_price = min(prices)
                max_price = max(prices)
                savings = max_price - min_price
                savings_percent = (savings / max_price) * 100
                
                fig.add_annotation(
                    text=f'Potential Savings: ${savings:,.2f} ({savings_percent:.1f}%)',
                    xref="paper", yref="paper",
                    x=0.5, y=1.1,
                    showarrow=False,
                    font=dict(size=14, color="green")
                )
            
            chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return jsonify({'chart': chart_json})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001) 