#!/bin/bash

echo "🚀 Starting TikTok Viral Engine Dashboard..."
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Starting Streamlit app..."
streamlit run app.py --logger.level=info