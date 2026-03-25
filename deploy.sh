#!/bin/bash
# ──────────────────────────────────────────────────────────────
#  deploy.sh  —  Package and upload your bot to AWS Lambda
#
#  Run this script from the folder containing your .py files.
#  Prerequisites:
#    1. AWS CLI installed  →  https://aws.amazon.com/cli/
#    2. AWS CLI configured →  run: aws configure
#       (enter your Access Key ID, Secret, region: ap-south-1)
#    3. Lambda function already created in AWS Console (see README)
# ──────────────────────────────────────────────────────────────

FUNCTION_NAME="job-monitor-bot"   # ← must match the name you gave in AWS Console
REGION="ap-south-1"               # ← Mumbai (closest to India, lowest latency)

echo "📦 Step 1: Installing dependencies into ./package/"
rm -rf package deployment.zip
mkdir package
pip install -r requirements.txt -t ./package/ --quiet

echo "📂 Step 2: Copying your source files into package"
cp job_monitor.py    ./package/
cp company_scrapers.py ./package/
cp config.py         ./package/

echo "🗜️  Step 3: Zipping everything"
cd package && zip -r ../deployment.zip . -q && cd ..
echo "   deployment.zip size: $(du -sh deployment.zip | cut -f1)"

echo "🚀 Step 4: Uploading to Lambda"
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://deployment.zip \
    --region "$REGION"

echo ""
echo "✅ Done! Your Lambda is updated."
echo "   Check logs at: https://console.aws.amazon.com/cloudwatch/home?region=${REGION}#logsV2:log-groups"