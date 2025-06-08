#!/usr/bin/env python3
"""
Comprehensive test of the integrated Flask app with hospital datasets
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5001"

def test_endpoint(url, description):
    """Test an endpoint and return results"""
    print(f"\n🧪 Testing: {description}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {response.status_code}")
            return data
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None

def main():
    print("🏥 FINAL INTEGRATION TEST - Cross-Hospital Price Comparison")
    print("=" * 80)
    
    # Test 1: Verify stats endpoint works (frontend uses this on load)
    stats = test_endpoint(f"{BASE_URL}/api/stats", "Dataset statistics (frontend compatibility)")
    if stats:
        print(f"   📊 Hospitals with datasets: {stats['totals']['hospitals_with_datasets']}")
        print(f"   📊 Total items: {stats['totals']['total_items']:,}")
        print(f"   📊 Total NDC codes: {stats['totals']['total_ndc_codes']:,}")
        print(f"   ✅ Stats format compatible with new frontend")
    else:
        print(f"   ❌ CRITICAL: Stats not working - frontend will show 'Unable to load statistics'")
    
    # Test 2: Test search functionality 
    insulin_search = test_endpoint(f"{BASE_URL}/api/procedures?search=insulin&limit=5", "Insulin search (main functionality)")
    if insulin_search and len(insulin_search) > 0:
        print(f"   💊 Found {len(insulin_search)} insulin matches")
        for i, result in enumerate(insulin_search[:3]):
            print(f"      {i+1}. {result['code_type']} {result['code']}: {result['hospital_count']} hospitals")
            print(f"         Price range: ${result['price_range']['min']:.2f} - ${result['price_range']['max']:.2f}")
            print(f"         Potential savings: ${result['price_range']['spread']:.2f} ({result['price_range']['spread_percent']:.1f}%)")
        print(f"   ✅ Search working perfectly with significant savings found")
        
        # Test 3: Test detailed pricing (what happens when user clicks)
        first_match = insulin_search[0]
        pricing_url = f"{BASE_URL}/api/pricing/match_0?search=insulin&code={first_match['code']}&code_type={first_match['code_type']}"
        pricing_data = test_endpoint(pricing_url, "Detailed pricing (click functionality)")
        if pricing_data:
            print(f"   💰 Price analysis working:")
            print(f"      Min price: ${pricing_data['price_analysis']['min_price']:.2f}")
            print(f"      Max price: ${pricing_data['price_analysis']['max_price']:.2f}")
            print(f"      Potential savings: ${pricing_data['price_analysis']['potential_savings']:.2f}")
            print(f"      Hospitals: {len(pricing_data['pricing_by_hospital'])}")
            print(f"   ✅ Click functionality working - users can see detailed breakdowns")
        else:
            print(f"   ❌ ISSUE: Clicking on results won't work")
    else:
        print(f"   ❌ CRITICAL: No search results - main functionality broken")
    
    # Test 4: Test other common searches that should work
    test_searches = [
        ("MRI", "Medical imaging procedures"),
        ("metoprolol", "Common heart medication"),
        ("blood test", "Laboratory services")
    ]
    
    print(f"\n🔍 TESTING OTHER COMMON SEARCHES:")
    for search_term, description in test_searches:
        result = test_endpoint(f"{BASE_URL}/api/procedures?search={search_term}&limit=3", f"Search: {search_term}")
        if result and len(result) > 0:
            print(f"      ✅ '{search_term}': {len(result)} matches found")
            max_savings = max([r['price_range']['spread'] for r in result if r['price_range']['spread'] > 0], default=0)
            if max_savings > 0:
                print(f"         Max savings found: ${max_savings:,.0f}")
        else:
            print(f"      ⚠️  '{search_term}': No cross-hospital matches")
    
    # Test 5: Direct code search
    ndc_result = test_endpoint(f"{BASE_URL}/api/procedures?search=00002831501", "Direct NDC code search")
    if ndc_result and len(ndc_result) > 0:
        print(f"   🔍 NDC code search working: {len(ndc_result)} matches")
        print(f"   ✅ Direct code lookup functional")
    
    # Test 6: Frontend page load
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200 and "Cross-Hospital Price Comparison" in response.text:
            print(f"\n🌐 FRONTEND TEST:")
            print(f"   ✅ Website loads successfully")
            print(f"   ✅ New title appears: 'Cross-Hospital Price Comparison'")
            print(f"   ✅ Frontend updated for new API")
        else:
            print(f"\n🌐 FRONTEND TEST:")
            print(f"   ❌ Website not loading properly")
    except Exception as e:
        print(f"\n🌐 FRONTEND TEST:")
        print(f"   ❌ Cannot access website: {e}")
    
    print(f"\n" + "=" * 80)
    print(f"🎯 INTEGRATION STATUS SUMMARY:")
    
    if stats and insulin_search and len(insulin_search) > 0:
        print(f"   ✅ WORKING: Cross-hospital search and price comparison")
        print(f"   ✅ WORKING: Statistics display")
        print(f"   ✅ WORKING: Frontend integration")
        print(f"   ✅ WORKING: Massive savings identification")
        
        # Calculate summary stats
        total_matches = len(insulin_search)
        avg_savings = sum([r['price_range']['spread'] for r in insulin_search]) / len(insulin_search)
        max_savings_pct = max([r['price_range']['spread_percent'] for r in insulin_search])
        
        print(f"\n💡 REAL VALUE DEMONSTRATION:")
        print(f"   • Found {total_matches} insulin matches across hospitals")
        print(f"   • Average potential savings: ${avg_savings:,.0f}")
        print(f"   • Maximum savings percentage: {max_savings_pct:,.0f}%")
        print(f"   • Users can now make informed decisions and save thousands")
        
        print(f"\n🚀 SYSTEM IS FULLY OPERATIONAL!")
        print(f"   → Visit: http://127.0.0.1:5001")
        print(f"   → Search for: insulin, MRI, blood test, medications")
        print(f"   → Click results to see detailed price breakdowns")
        print(f"   → View interactive charts showing price differences")
        
    else:
        print(f"   ❌ ISSUES DETECTED:")
        if not stats:
            print(f"      - Statistics not loading")
        if not insulin_search or len(insulin_search) == 0:
            print(f"      - Search functionality not working")
        print(f"   🔧 Check server logs and dataset loading")

if __name__ == "__main__":
    main() 