#!/bin/bash
echo "🚀 PremiumKiller Deploy Starting..."

# Update & Install
apt update && apt install python3-pip git screen nano curl -y

# Python deps
pip3 install -r requirements.txt

# PM2 (Production ready)
npm install -g pm2

echo "✅ Deploy Complete! Edit config.py then:"
echo "pm2 start ban_bot.py --interpreter python3 --name KillerBot"
echo "pm2 save && pm2 startup"
