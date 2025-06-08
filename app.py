from flask import Flask, render_template, jsonify, request
import plotly.graph_objs as go
import plotly.utils
from models import db, Hospital, Procedure, PricingData
from hospital_dataset_builder import load_hospital_dataset, HOSPITAL_NAMES
from sqlalchemy import func, or_
import re
from collections import defaultdict, Counter

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital_pricing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Load all hospital datasets on startup
print("🏥 Loading hospital datasets...")
hospital_datasets = {}
hospitals = ['stanford', 'ucsf', 'ucla', 'cedars']

for hospital_key in hospitals:
    try:
        dataset = load_hospital_dataset(hospital_key)
        if dataset:
            hospital_datasets[hospital_key] = dataset
            print(f"✅ Loaded {dataset.hospital_name}")
        else:
            print(f"❌ Failed to load {HOSPITAL_NAMES[hospital_key]}")
    except Exception as e:
        print(f"❌ Error loading {HOSPITAL_NAMES[hospital_key]}: {e}")

print(f"📊 Total datasets loaded: {len(hospital_datasets)}")

def normalize_ndc(ndc_code):
    """Normalize NDC codes by removing separators and padding"""
    # Remove all non-digits
    digits_only = re.sub(r'\D', '', str(ndc_code))
    
    # NDC codes should be 10-11 digits, pad to 11 if needed
    if len(digits_only) >= 9 and len(digits_only) <= 11:
        # Pad to 11 digits
        return digits_only.zfill(11)
    return None

def find_cross_hospital_matches(search_term, max_results=50):
    """
    Find items across all hospitals that match the search term,
    then group them by matching codes (NDC, HCPCS, CPT, etc.)
    """
    # Step 1: Search each hospital for matching items
    hospital_results = {}
    
    for hospital_key, dataset in hospital_datasets.items():
        # Search by keywords
        results = dataset.search_by_keywords(search_term)
        
        # Also try direct code search if search term looks like a code
        if re.match(r'^[A-Z0-9\-]+$', search_term.upper()):
            code_results = []
            # Try different code types
            for code_type in ['NDC', 'HCPCS', 'CPT', 'CDM']:
                code_matches = dataset.find_by_code(search_term.upper(), code_type)
                code_results.extend(code_matches)
            
            # Merge with keyword results
            results.extend(code_results)
        
        # Remove duplicates
        seen_indices = set()
        unique_results = []
        for item in results:
            if item['index'] not in seen_indices:
                unique_results.append(item)
                seen_indices.add(item['index'])
        
        hospital_results[hospital_key] = unique_results[:max_results]
    
    # Step 2: Group by matching codes
    code_groups = defaultdict(lambda: {
        'hospitals': {},
        'code': None,
        'code_type': None,
        'description_samples': set(),
        'min_price': float('inf'),
        'max_price': 0,
        'hospital_count': 0
    })
    
    # Process each hospital's results
    for hospital_key, items in hospital_results.items():
        for item in items:
            for code_info in item.get('codes', []):
                code_value = code_info['code']
                code_type = code_info['type']
                
                # For NDC codes, use normalized version for matching
                if code_type == 'NDC':
                    match_key = normalize_ndc(code_value)
                    if not match_key:
                        continue
                    match_key = f"NDC:{match_key}"
                else:
                    match_key = f"{code_type}:{code_value}"
                
                # Add to group
                group = code_groups[match_key]
                group['code'] = code_value
                group['code_type'] = code_type
                group['description_samples'].add(item['description'][:100])
                
                # Get best price for this item
                best_price = min(p['gross_charge'] for p in item['prices'] if p['gross_charge'] > 0) if item['prices'] else 0
                if best_price > 0:
                    group['min_price'] = min(group['min_price'], best_price)
                    group['max_price'] = max(group['max_price'], best_price)
                
                # Store hospital-specific data
                if hospital_key not in group['hospitals']:
                    group['hospitals'][hospital_key] = []
                
                group['hospitals'][hospital_key].append({
                    'item': item,
                    'original_code': code_value,
                    'price': best_price,
                    'price_details': item['prices']
                })
    
    # Step 3: Filter and sort groups
    # Only keep groups with multiple hospitals
    filtered_groups = {}
    for match_key, group in code_groups.items():
        hospital_count = len(group['hospitals'])
        if hospital_count >= 2:  # At least 2 hospitals
            group['hospital_count'] = hospital_count
            
            # Fix min_price if no valid prices found
            if group['min_price'] == float('inf'):
                group['min_price'] = 0
            
            # Calculate price spread
            if group['max_price'] > 0 and group['min_price'] > 0:
                group['price_spread'] = group['max_price'] - group['min_price']
                group['price_spread_percent'] = (group['price_spread'] / group['min_price']) * 100
            else:
                group['price_spread'] = 0
                group['price_spread_percent'] = 0
            
            # Convert description samples to list
            group['description_samples'] = list(group['description_samples'])
            
            filtered_groups[match_key] = group
    
    # Sort by hospital count (descending), then by price spread (descending)
    sorted_groups = sorted(
        filtered_groups.items(),
        key=lambda x: (x[1]['hospital_count'], x[1]['price_spread']),
        reverse=True
    )
    
    return [group for _, group in sorted_groups[:max_results]]

@app.route('/')
def index():
    """Home page with hospital pricing comparison tool"""
    return render_template('index.html')

@app.route('/api/hospitals')
def get_hospitals():
    """Get list of all hospitals"""
    # Return both database hospitals and dataset hospitals
    db_hospitals = Hospital.query.all()
    
    # Also include dataset hospitals
    dataset_hospitals = []
    for hospital_key, dataset in hospital_datasets.items():
        dataset_hospitals.append({
            'id': hospital_key,
            'name': dataset.hospital_name,
            'location': 'California',
            'dataset_loaded': True
        })
    
    return jsonify({
        'database_hospitals': [hospital.to_dict() for hospital in db_hospitals],
        'dataset_hospitals': dataset_hospitals,
        'total_datasets': len(hospital_datasets)
    })

@app.route('/api/procedures')
def get_procedures():
    """
    Search procedures using the new hospital datasets with cross-hospital matching.
    Returns procedures matched by codes across multiple hospitals.
    """
    search = request.args.get('search', '').strip()
    limit = int(request.args.get('limit', 50))
    
    if not search:
        return jsonify([])
    
    if len(hospital_datasets) == 0:
        # Fallback to old database search if no datasets loaded
        query = Procedure.query.join(PricingData)
        search_filter = or_(
            Procedure.name.ilike(f'%{search}%'),
            Procedure.description.ilike(f'%{search}%'),
            Procedure.code.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
        procedures = query.limit(limit).all()
        return jsonify([{
            **procedure.to_dict(),
            'hospital_count': PricingData.query.filter_by(procedure_id=procedure.id).count(),
            'source': 'database'
        } for procedure in procedures])
    
    # Use new cross-hospital matching
    matches = find_cross_hospital_matches(search, limit)
    
    # Format results for API
    results = []
    for i, match in enumerate(matches):
        # Get representative description
        description = match['description_samples'][0] if match['description_samples'] else 'No description'
        
        # Create pricing summary
        hospital_prices = []
        for hospital_key, items in match['hospitals'].items():
            dataset = hospital_datasets[hospital_key]
            best_item = min(items, key=lambda x: x['price'] if x['price'] > 0 else float('inf'))
            
            hospital_prices.append({
                'hospital': dataset.hospital_name,
                'hospital_key': hospital_key,
                'price': best_item['price'],
                'item_count': len(items)
            })
        
        # Sort by price
        hospital_prices.sort(key=lambda x: x['price'] if x['price'] > 0 else float('inf'))
        
        results.append({
            'id': f"match_{i}",  # Unique ID for this match
            'name': description,
            'code': match['code'],
            'code_type': match['code_type'],
            'description': description,
            'hospital_count': match['hospital_count'],
            'price_range': {
                'min': match['min_price'],
                'max': match['max_price'],
                'spread': match['price_spread'],
                'spread_percent': match['price_spread_percent']
            },
            'hospitals': hospital_prices,
            'source': 'datasets',
            'match_key': f"{match['code_type']}:{match['code']}"
        })
    
    return jsonify(results)

@app.route('/api/pricing/<path:match_id>')
def get_pricing_for_match(match_id):
    """
    Get detailed pricing information for a cross-hospital match.
    """
    # Parse match_id to extract code information
    if not match_id.startswith('match_'):
        # Try old database lookup for backward compatibility
        try:
            procedure_id = int(match_id)
            procedure = Procedure.query.get_or_404(procedure_id)
            pricing_data = PricingData.query.filter_by(procedure_id=procedure_id).all()
            
            result = {
                'procedure': procedure.to_dict(),
                'pricing_by_hospital': [],
                'source': 'database'
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
                    }
                }
                result['pricing_by_hospital'].append(hospital_pricing)
            
            return jsonify(result)
        except:
            return jsonify({'error': 'Match not found'}), 404
    
    # Get parameters from request to reconstruct the search
    search = request.args.get('search', '')
    code = request.args.get('code', '')
    code_type = request.args.get('code_type', '')
    
    if not search and not code:
        return jsonify({'error': 'Search term or code required'}), 400
    
    # Re-run the search to find the specific match
    if search:
        matches = find_cross_hospital_matches(search, 100)
        # Find the specific match
        target_match = None
        for match in matches:
            if f"{match['code_type']}:{match['code']}" == f"{code_type}:{code}":
                target_match = match
                break
        
        if not target_match:
            return jsonify({'error': 'Match not found'}), 404
    else:
        return jsonify({'error': 'Invalid match ID'}), 400
    
    # Format detailed response
    result = {
        'procedure': {
            'name': target_match['description_samples'][0] if target_match['description_samples'] else 'Unknown',
            'code': target_match['code'],
            'code_type': target_match['code_type'],
            'description': ' | '.join(target_match['description_samples'][:3])
        },
        'pricing_by_hospital': [],
        'source': 'datasets',
        'hospital_count': target_match['hospital_count'],
        'price_analysis': {
            'min_price': target_match['min_price'],
            'max_price': target_match['max_price'],
            'price_spread': target_match['price_spread'],
            'potential_savings': target_match['price_spread'],
            'savings_percent': target_match['price_spread_percent']
        }
    }
    
    # Add detailed hospital pricing
    for hospital_key, items in target_match['hospitals'].items():
        dataset = hospital_datasets[hospital_key]
        
        # Get all pricing options for this hospital
        hospital_items = []
        for item_data in items:
            item = item_data['item']
            hospital_items.append({
                'description': item['description'],
                'prices': item_data['price_details'],
                'codes': item['codes']
            })
        
        # Get best price
        best_price = min(item_data['price'] for item_data in items if item_data['price'] > 0) if items else 0
        
        hospital_pricing = {
            'hospital': {
                'name': dataset.hospital_name,
                'key': hospital_key
            },
            'pricing': {
                'best_price': best_price,
                'item_count': len(items),
                'all_items': hospital_items
            }
        }
        result['pricing_by_hospital'].append(hospital_pricing)
    
    # Sort by price
    result['pricing_by_hospital'].sort(key=lambda x: x['pricing']['best_price'] if x['pricing']['best_price'] > 0 else float('inf'))
    
    return jsonify(result)

@app.route('/api/chart/<path:match_id>')
def get_pricing_chart(match_id):
    """
    Generate a chart comparing both cash prices and gross charges across hospitals for a matched item.
    """
    # Get the pricing data first
    search = request.args.get('search', '')
    code = request.args.get('code', '')
    code_type = request.args.get('code_type', '')
    
    if not search and not code:
        return jsonify({'error': 'Search term or code required'}), 400
    
    # Re-run the search to find the specific match
    matches = find_cross_hospital_matches(search, 100)
    target_match = None
    for match in matches:
        if f"{match['code_type']}:{match['code']}" == f"{code_type}:{code}":
            target_match = match
            break
    
    if not target_match:
        return jsonify({'error': 'Match not found'}), 404
    
    # Prepare data for both cash prices and gross charges
    hospital_names = []
    cash_prices = []
    gross_charges = []
    
    # Extract pricing data from the match structure
    for hospital_key, items in target_match['hospitals'].items():
        dataset = hospital_datasets[hospital_key]
        hospital_name = dataset.hospital_name
        
        # Find best cash price and corresponding gross charge across all items for this hospital
        best_cash = None
        corresponding_gross = None
        
        for item_data in items:
            item_prices = item_data.get('price_details', [])
            for price_entry in item_prices:
                cash_price = price_entry.get('discounted_cash')
                gross_price = price_entry.get('gross_charge')
                
                if cash_price is not None and gross_price is not None:
                    if best_cash is None or cash_price < best_cash:
                        best_cash = cash_price
                        corresponding_gross = gross_price
        
        if best_cash is not None and corresponding_gross is not None:
            hospital_names.append(hospital_name)
            cash_prices.append(best_cash)
            gross_charges.append(corresponding_gross)
    
    if not hospital_names:
        return jsonify({'error': 'No pricing data available for chart'}), 404
    
    # Create dual-bar chart data
    chart_data = {
        'type': 'bar',
        'data': {
            'labels': hospital_names,
            'datasets': [
                {
                    'label': 'Cash Price',
                    'data': cash_prices,
                    'backgroundColor': 'rgba(40, 167, 69, 0.8)',
                    'borderColor': 'rgba(40, 167, 69, 1)',
                    'borderWidth': 1
                },
                {
                    'label': 'Gross Charge',
                    'data': gross_charges,
                    'backgroundColor': 'rgba(220, 53, 69, 0.8)',
                    'borderColor': 'rgba(220, 53, 69, 1)',
                    'borderWidth': 1
                }
            ]
        },
        'options': {
            'responsive': True,
            'plugins': {
                'title': {
                    'display': True,
                    'text': f'Price Comparison: {code_type} {code} - {target_match.get("description_samples", ["Unknown"])[0][:50]}...'
                },
                'legend': {
                    'display': True,
                    'position': 'top'
                }
            },
            'scales': {
                'y': {
                    'beginAtZero': True,
                    'title': {
                        'display': True,
                        'text': 'Price ($)'
                    },
                    'ticks': {
                        'callback': 'function(value) { return "$" + value.toLocaleString(); }'
                    }
                },
                'x': {
                    'title': {
                        'display': True,
                        'text': 'Hospitals'
                    }
                }
            },
            'interaction': {
                'intersect': False,
                'mode': 'index'
            },
            'elements': {
                'bar': {
                    'borderWidth': 2
                }
            }
        }
    }
    
    return jsonify(chart_data)

@app.route('/api/stats')
def get_statistics():
    """Get comprehensive statistics from both database and datasets"""
    # Database stats
    with db.session() as session:
        db_stats = {
            'hospitals': session.query(Hospital).count(),
            'procedures': session.query(Procedure).count(),
            'pricing_records': session.query(PricingData).count(),
        }
    
    # Dataset stats
    dataset_stats = {}
    total_items = 0
    total_ndc = 0
    total_hcpcs = 0
    total_cpt = 0
    
    for hospital_key, dataset in hospital_datasets.items():
        stats = dataset.get_stats()
        ndc_count = dataset.count_by_code_type('NDC')
        hcpcs_count = dataset.count_by_code_type('HCPCS')
        cpt_count = dataset.count_by_code_type('CPT')
        
        dataset_stats[hospital_key] = {
            'name': stats['hospital_name'],
            'items': stats['total_items'],
            'ndc_codes': ndc_count,
            'hcpcs_codes': hcpcs_count,
            'cpt_codes': cpt_count,
            'searchable_words': stats['searchable_words']
        }
        
        total_items += stats['total_items']
        total_ndc += ndc_count
        total_hcpcs += hcpcs_count
        total_cpt += cpt_count
    
    return jsonify({
        'database_stats': db_stats,
        'dataset_stats': dataset_stats,
        'totals': {
            'hospitals_with_datasets': len(hospital_datasets),
            'total_items': total_items,
            'total_ndc_codes': total_ndc,
            'total_hcpcs_codes': total_hcpcs,
            'total_cpt_codes': total_cpt
        },
        'capabilities': [
            'Cross-hospital code matching',
            'Real-time price comparison',
            'NDC normalization and matching',
            'HCPCS and CPT code lookup',
            'Keyword-based search',
            'Price spread analysis'
        ]
    })

# Keep the old endpoints for backward compatibility
@app.route('/api/compare')
def compare_procedures():
    """Legacy endpoint for backward compatibility"""
    return jsonify({
        'message': 'This endpoint has been replaced by the new cross-hospital matching system',
        'new_endpoint': '/api/procedures',
        'instructions': 'Use the search parameter to find cross-hospital matches'
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001) 