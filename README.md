# Hospital Pricing Transparency Tool

A minimalistic tool for comparing hospital procedure prices across different healthcare facilities.

## Overview

This tool helps patients and healthcare consumers compare prices for medical procedures across different hospitals. It leverages the hospital price transparency data that hospitals are required to publish under federal regulations.

## Features

- 🏥 **Hospital Database**: Store and manage pricing data from multiple hospitals
- 💰 **Price Comparison**: Compare cash prices and insurance rates across facilities
- 🔍 **Procedure Search**: Find specific procedures and their pricing
- 📊 **Visual Analytics**: Charts and graphs for price analysis
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database**:
   ```bash
   python init_db.py
   ```

3. **Load Sample Data**:
   ```bash
   python load_sample_data.py
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```

5. **Open your browser** to `http://localhost:5000`

## Data Sources

The tool can import data from:
- Hospital-published machine-readable files (CSV, JSON)
- Manual entry for specific procedures
- Public transparency databases

## Usage

1. **Search for a procedure** (e.g., "MRI Brain", "Knee Replacement")
2. **Select hospitals** to compare
3. **View pricing breakdown** including:
   - Cash/self-pay prices
   - Insurance negotiated rates
   - Average prices across facilities
4. **Export results** for further analysis

## Contributing

We welcome contributions to improve hospital pricing transparency! Please see our contributing guidelines.

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is for informational purposes only. Always verify pricing directly with healthcare providers before making medical decisions. 