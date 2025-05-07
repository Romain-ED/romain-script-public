#!/usr/bin/env python3
"""
CSV Processor - Process large CSV files and perform data manipulations
This script processes CSV files by:
1. Keeping only required columns
2. Adding three new calculated columns (Tag, Total Parts, Part Num)
3. Breaking down output into one file per day based on date_received
4. Providing summary statistics about the processing

Usage:
    python csv_processor.py input.csv [output_dir]
"""

import os
import sys
import csv
import time
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path
import colorama
from colorama import Fore, Back, Style

# Initialize colorama
colorama.init(autoreset=True)

# Configure logging with custom formatter for colors
class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels"""
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            levelname_color = self.COLORS[levelname] + levelname + Style.RESET_ALL
            record.levelname = levelname_color
        return super().format(record)

# Set up console handler with color formatter
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Set up file handler with regular formatter
file_handler = logging.FileHandler('csv_processor.log')
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.handlers.clear()  # Remove any existing handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.propagate = False  # Prevent duplicate logs

# List of required columns that should be kept
REQUIRED_COLUMNS = [
    "account_id", "message_id", "direction", "from", "to", "forced_from", 
    "message_body", "concatenated", "network", "network_name", "country", 
    "country_name", "date_received", "date_finalized", "latency", "status", 
    "error_code", "error_code_description", "currency", "total_price", "udh"
]

def hex_to_dec(hex_value):
    """Convert hexadecimal value to decimal."""
    if pd.isna(hex_value) or hex_value is None or str(hex_value).strip() == '':
        return '1'
    
    try:
        hex_str = str(hex_value).strip()
        # Skip if value starts with letters (likely not a hex value)
        if hex_str and hex_str[0].isalpha():
            return '1'
        return str(int(hex_str, 16))
    except ValueError:
        logger.debug(f"Could not convert '{hex_value}' to decimal: invalid hex")
        return '1'  # Default value in case of error

def process_csv(input_file, output_dir):
    """Process the CSV file and create output files split by day."""
    start_time = time.time()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Extract API key from the filename
    filename = Path(input_file).name
    api_key = filename.split('_')[2] if '_' in filename else 'unknown'
    
    logger.info(f"\n{Fore.BLUE}Starting to process file: {Fore.YELLOW}{input_file}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Output directory: {Fore.YELLOW}{output_dir}{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}API Key: {Fore.YELLOW}{api_key}{Style.RESET_ALL}\n")
    
    try:
        # Check if file exists
        if not os.path.exists(input_file):
            logger.error(f"Input file not found: {input_file}")
            return

        # Get file size for logging
        file_size = os.path.getsize(input_file) / (1024 * 1024)  # Convert to MB
        logger.info(f"Input file size: {file_size:.2f} MB")

        # Use pandas to read and process the CSV
        logger.info("Reading CSV file using pandas with chunking...")

        # Read first row to get column names
        df_header = pd.read_csv(input_file, nrows=0)
        header = df_header.columns.tolist()
        logger.info(f"CSV header columns: {header}")

        # Check for required columns
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in header]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return
            
        # Process the CSV in chunks to handle large files
        chunk_size = 100000  # Adjust based on available memory
        chunks = pd.read_csv(input_file, chunksize=chunk_size, low_memory=False)

        # Prepare to track statistics
        total_rows_processed = 0
        files_created = {}
        
        for i, chunk in enumerate(chunks):
            chunk_start = time.time()
            logger.info(f"\n{Fore.BLUE}Processing chunk {i+1} with {Fore.YELLOW}{len(chunk):,}{Fore.BLUE} rows...{Style.RESET_ALL}")
            
            
            # Create a new DataFrame with only required columns to avoid SettingWithCopyWarning
            df = pd.DataFrame()
            for col in REQUIRED_COLUMNS:
                if col in chunk.columns:
                    df[col] = chunk[col]
                else:
                    logger.warning(f"Column '{col}' not found in the CSV. Adding empty column.")
                    df[col] = ''
            
            # Add the three new columns
            logger.info("Adding new calculated columns...")
            
            # 1. Tag: ONLY add tag if udh is not empty
            def create_tag(row):
                udh = row.get('udh', None)
                to = row.get('to', '')
                
                # If UDH is empty, return "-to"
                if udh is None or pd.isna(udh) or str(udh).strip() == '':
                    return f"-{to}"
                
                # Otherwise return udh (without last 4 chars) + "-" + to
                udh_str = str(udh)
                udh_prefix = udh_str[:-4] if len(udh_str) > 4 else udh_str
                return f"{udh_prefix}-{to}"
            
            # Debug output for first few rows of first chunk
            if i == 0:
                for idx, row in df.head(3).iterrows():
                    logger.info(f"Row {idx} - UDH: '{row.get('udh', 'N/A')}', To: '{row.get('to', 'N/A')}'")
            
            # Apply the tag function
            df['Tag'] = df.apply(create_tag, axis=1)
            
            # Extract UDH parts safely
            def extract_total_parts(udh):
                if pd.isna(udh) or str(udh).strip() == '':
                    return '1'
                
                # According to formula: hex2dec(left(right(udh,4),2))
                udh_str = str(udh)
                if len(udh_str) >= 4:
                    right_four = udh_str[-4:]  # Get the rightmost 4 characters
                    left_two = right_four[:2]  # Get the leftmost 2 of those
                    return hex_to_dec(left_two)
                return '1'
                
            def extract_part_num(udh):
                if pd.notna(udh) and len(str(udh)) >= 2:
                    # Check if it's a string that could be a hex value
                    udh_str = str(udh)
                    if len(udh_str) >= 2 and udh_str[-2:].isalnum():
                        return hex_to_dec(udh_str[-2:])
                return '1'
            
            # 2. Total Parts based on UDH
            df['Total Parts'] = df['udh'].apply(extract_total_parts)
            
            # 3. Part Num based on UDH
            df['Part Num'] = df['udh'].apply(extract_part_num)
            
            # Parse date_received to split by day
            logger.info("Parsing dates to split by day...")
            
            # Ensure date_received is properly formatted
            df['date_received'] = pd.to_datetime(df['date_received'], errors='coerce')
            
            # Remove rows with invalid dates
            invalid_dates = df['date_received'].isna().sum()
            if invalid_dates > 0:
                logger.warning(f"Found {invalid_dates} rows with invalid dates. These will be excluded.")
                df = df.dropna(subset=['date_received'])
            
            # Extract date part only (without time)
            df['date_key'] = df['date_received'].dt.date
            
            # After processing, log stats about empty/filled tag columns
            empty_tags = (df['Tag'] == "").sum()
            filled_tags = len(df) - empty_tags
            logger.info(f"{Fore.BLUE}Tags generated: {Fore.GREEN}{filled_tags:,} filled, {Fore.YELLOW}{empty_tags:,} empty{Style.RESET_ALL}")
            
            # Group by date and write each group to a separate file
            date_groups = df.groupby('date_key')
            logger.info(f"{Fore.BLUE}Writing data to {len(date_groups)} date-specific files...{Style.RESET_ALL}")
            
                # Remove the temporary date_key column
                group = group.drop('date_key', axis=1)
                
                # Create filename based on date
                date_str = date.strftime('%Y-%m-%d')
                filename = f"{api_key}-{date_str}.csv"
                filepath = output_path / filename
                
                # Check if file already exists (for append mode)
                file_exists = os.path.isfile(filepath)
                
                # Write the data
                group.to_csv(filepath, mode='a', index=False, header=not file_exists)
                
                # Track statistics
                if date_str in files_created:
                    files_created[date_str] += len(group)
                else:
                    files_created[date_str] = len(group)
                    
                logger.debug(f"Added {len(group)} rows to {filename}")
            
            total_rows_processed += len(df)
            chunk_time = time.time() - chunk_start
            logger.info(f"Chunk {i+1} processed in {chunk_time:.2f} seconds. Total rows so far: {total_rows_processed}")
    except Exception as e:
        logger.error(f"Error processing CSV: {e}", exc_info=True)
        return

    # Calculate and log summary statistics
    elapsed_time = time.time() - start_time
    logger.info(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*50}")
    logger.info(f"{Fore.CYAN}{Style.BRIGHT}PROCESSING SUMMARY")
    logger.info(f"{Fore.CYAN}{Style.BRIGHT}{'='*50}")
    logger.info(f"\n{Fore.GREEN}Total rows processed: {Style.BRIGHT}{total_rows_processed:,}")
    logger.info(f"{Fore.GREEN}Number of output files created: {Style.BRIGHT}{len(files_created)}")
    logger.info(f"{Fore.GREEN}Processing time: {Style.BRIGHT}{elapsed_time:.2f} seconds\n")
    
    logger.info(f"{Fore.CYAN}Files created:")
    
    total_output_size = 0
    for date_str, row_count in sorted(files_created.items()):
        filepath = output_path / f"{api_key}-{date_str}.csv"
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # Convert to MB
        total_output_size += file_size
        logger.info(f"  {Fore.YELLOW}► {filepath.name}: {Style.BRIGHT}{row_count:,} rows, {file_size:.2f} MB")
    
    logger.info(f"\n{Fore.GREEN}Total output size: {Style.BRIGHT}{total_output_size:.2f} MB")
    logger.info(f"{Fore.CYAN}{Style.BRIGHT}{'='*50}\n")
    
    return {
        "total_rows": total_rows_processed,
        "files_created": len(files_created),
        "processing_time": elapsed_time,
        "total_output_size": total_output_size
    }

def main():
    """Main function to handle command-line arguments and start processing."""
    # Print welcome banner
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'CSV PROCESSOR':^80}")
    print(f"{Fore.CYAN}{'='*80}\n")
    
    if len(sys.argv) < 2:
        logger.error(f"{Fore.RED}Usage: python csv_processor.py input.csv [output_dir]{Style.RESET_ALL}")
        sys.exit(1)
    
    input_file = sys.argv[1]
    # Default output directory is 'output' in the current directory
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    logger.info(f"\n{Fore.GREEN}CSV Processor started{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Python version: {sys.version}{Style.RESET_ALL}\n")
    
    stats = process_csv(input_file, output_dir)
    
    if stats:
        logger.info(f"\n{Fore.GREEN}{Style.BRIGHT}CSV processing completed successfully!{Style.RESET_ALL}")
    else:
        logger.error(f"\n{Fore.RED}{Style.BRIGHT}CSV processing failed. Check logs for details.{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'END OF PROCESSING':^80}")
    print(f"{Fore.CYAN}{'='*80}\n")

if __name__ == "__main__":
    main()