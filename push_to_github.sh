#!/bin/bash

# Quick Push Script for AgriTech Chat Assistant
# Run this AFTER creating the repository on GitHub

echo "🚀 Pushing AgriTech Chat Assistant to GitHub..."
echo "=============================================="
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    echo "❌ Error: Not in the correct directory"
    echo "Please run this script from: /Users/khush/Documents/GitHub/agritech-chat-assistant"
    exit 1
fi

echo "📁 Current directory: $(pwd)"
echo "👤 GitHub Username: khusa71"
echo "🔗 Repository: https://github.com/khusa71/agritech-chat-assistant"
echo ""

# Check git status
echo "📊 Git Status:"
git status --short
echo ""

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Repository pushed to GitHub!"
    echo ""
    echo "🔗 Your repository is now available at:"
    echo "https://github.com/khusa71/agritech-chat-assistant"
    echo ""
    echo "🌟 Repository Features:"
    echo "• Complete ChatGPT-style agricultural assistant"
    echo "• Production-ready FastAPI backend"
    echo "• Interactive Streamlit development interface"
    echo "• Real-time weather, soil, and market data"
    echo "• Comprehensive documentation"
    echo "• Ready to help farmers worldwide!"
    echo ""
    echo "🎉 Congratulations! Your AgriTech assistant is now on GitHub!"
else
    echo ""
    echo "❌ Push failed. Please check:"
    echo "1. Repository exists on GitHub: https://github.com/khusa71/agritech-chat-assistant"
    echo "2. You have push permissions"
    echo "3. Your GitHub credentials are correct"
    echo ""
    echo "If the repository doesn't exist, create it first at: https://github.com/new"
fi
