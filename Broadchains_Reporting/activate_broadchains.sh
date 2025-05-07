#!/bin/bash
# Activate the Python virtual environment for Broadchains Report Parser
source venv/bin/activate || . venv/bin/activate
echo "Broadchains Report Parser environment activated!"
echo "Run the parser with: python broadchains_report_parser.py input.csv [output_dir]"
