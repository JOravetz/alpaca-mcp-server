#!/bin/bash
# Quick P&L Dashboard Updater
# Usage: ./quick_pnl.sh [date]
# Example: ./quick_pnl.sh 2025-08-25

DATE=${1:-$(date +%Y-%m-%d)}
echo "🚀 Quick P&L Dashboard Update for $DATE"
./update_pnl_dashboard.py --date "$DATE"