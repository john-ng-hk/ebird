#!/bin/bash

# Exit on any error
set -e

# Step 1: Run the local-scraper.py script
echo "Running local-scraper.py..."
home/ubuntu/ebird/ebird-venv/bin/python3 home/ubuntu/ebird/local-scraper.py

# Step 2: Upload the generated CSV to S3
echo "Uploading hk_birds.csv to S3 bucket..."
aws s3 cp home/ubuntu/ebird/ibird.cmpapp.top/hk_birds.csv s3://ibird.cmpapp.top/hk_birds.csv

echo "Script completed successfully!"