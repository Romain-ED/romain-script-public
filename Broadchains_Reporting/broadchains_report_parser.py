#!/usr/bin/env python3
"""
Broadchains Report Parser v1.1.0

Description:
    This script processes CSV files from Broadchains reporting system by:
    1. Keeping only required columns
    2. Adding three new calculated columns:
       - Tag: Combines UDH (minus last 4 chars), recipient number, and time info
         a) When UDH present: "{udh_prefix}-{to}-{hhmm}" (hours and minutes only)
         b) When UDH blank: "{to}-{hhmmss}" (includes hours, minutes, seconds)
       - Total Parts: Calculated from UDH - hex2dec(left(right(udh,4),2))
       - Part Num: Calculated from UDH - hex2dec(right(udh,2))
    3. Breaking down output into one file per day based on date_received
    4. Providing summary statistics about the processing
    5. Ensures message_body values are enclosed in double quotes

Author: Romain EDIN
Company: Vonage
Created: May 2025

Usage:
    python broadchains_report_parser.py input.csv [output_dir]

Changelog:
    v1.0.0 (2025-05-08) - Initial version
    - Basic CSV processing functionality
    - Split files by date
    - Added UDH parsing logic
    - Added colorized logging
    v1.0.1 (2025-05-08) - Added message_body formatting
    - Added double quotes around message_body values that don't have them
    v1.0.2 (2025-05-08) - Fixed message_body quote handling
    - Improved quote handling to ensure exactly one quote at start and end
    v1.0.3 (2025-05-08) - Fixed triple quotes issue
    - Fixed issue with triple quotes appearing in message_body
    v1.0.4 (2025-05-08) - Improved quote preservation
    - Added logic to preserve message_body values that already have correct quotes
    v1.0.5 (2025-05-08) - Fixed CSV quote handling
    - Completely redesigned message_body processing to avoid quote escaping issues
    v1.0.6 (2025-05-08) - Fixed missing quotes
    - Ensured message_body field always appears with quotes in output
    v1.0.7 (2025-05-08) - Fixed triple quotes issue
    - Directly modifies the CSV after writing to remove triple quotes
    v1.0.8 (2025-05-08) - Improved empty value handling
    - Changed NaN values to empty strings in output
    v1.0.9 (2025-05-09) - Enhanced Tag column
    - Added timestamp (HHMMSS) from date_received to the Tag column
    v1.1.0 (2025-05-09) - Improved Tag format
    - Removed leading dash in Tag when UDH is blank
    - Changed time format: HHMM for UDH present, HHMMSS for UDH blank
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

# Try to import colorama, but handle case when it's not installed
try:
    import colorama
    from colorama import Fore, Back, Style
    # Initialize colorama
    colorama.init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    # Create dummy color classes if colorama is not available
    print("Warning: colorama module not found. Install with: pip install colorama")
    print("Continuing without colored output...\n")
    
    class DummyColor:
        def __getattr__(self, name):
            return ""
    
    class DummyStyle:
        def __getattr__(self, name):
            return ""
    
    Fore = DummyColor()
    Back = DummyColor()
    Style = DummyStyle()
    HAS_COLORAMA = False

# Function to fix triple quotes in files
def fix_triple_quotes(file_path):
    """Fix triple quotes in CSV file by replacing them with single quotes."""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Replace triple quotes with single quotes
        content = content.replace('"""', '"')
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
            
        return True
    except Exception as e:
        logger.error(f"Error fixing quotes in {file_path}: {e}")
        return False

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

def process_message_body(message):
    """Process message_body to ensure proper formatting without quote duplication."""
    if pd.isna(message) or message is None:
        return ''
    
    # Convert to string and strip whitespace
    message = str(message).strip()
    
    # Remove any quotes completely
    message = message.replace('"', '')
    
    # Return clean message - quotes will be added properly later
    return message

def create_tag(row):
    """
    Create Tag column by combining UDH (without last 4 chars), to field, and time from date_received.
    
    Different formats are used depending on whether UDH is present:
    - With UDH: {udh_prefix}-{to}-{hhmm} (hour and minute only)
    - Without UDH: {to}-{hhmmss} (hour, minute, and seconds)
    """
    udh = row.get('udh', None)
    to = row.get('to', '')
    date_received = row.get('date_received', None)
    
    # Create base tag based on whether UDH is present
    if udh is None or pd.isna(udh) or str(udh).strip() == '':
        # UDH is not present - use just the 'to' value
        has_udh = False
        base_tag = f"{to}"
    else:
        # UDH is present - use UDH prefix and 'to' value
        has_udh = True
        udh_str = str(udh)
        udh_prefix = udh_str[:-4] if len(udh_str) > 4 else udh_str
        base_tag = f"{udh_prefix}-{to}"
    
    # Add time component from date_received with different format based on UDH presence
    time_suffix = ""
    if date_received is not None and not pd.isna(date_received):
        try:
            # Extract time components based on data type
            if isinstance(date_received, pd.Timestamp) or isinstance(date_received, datetime):
                if has_udh:
                    # For UDH present: use HHMM format
                    time_suffix = f"-{date_received.hour:02d}{date_received.minute:02d}"
                else:
                    # For UDH not present: use HHMMSS format
                    time_suffix = f"-{date_received.hour:02d}{date_received.minute:02d}{date_received.second:02d}"
            else:
                # Parse string to datetime if it's not already
                dt = pd.to_datetime(date_received)
                if has_udh:
                    # For UDH present: use HHMM format
                    time_suffix = f"-{dt.hour:02d}{dt.minute:02d}"
                else:
                    # For UDH not present: use HHMMSS format
                    time_suffix = f"-{dt.hour:02d}{dt.minute:02d}{dt.second:02d}"
        except Exception as e:
            # If any error occurs during time extraction, leave time_suffix empty
            logger.debug(f"Could not extract time from date_received: {date_received}, Error: {e}")
    
    # Return final tag with time suffix
    return f"{base_tag}{time_suffix}"

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
        # Note: Add quoting=csv.QUOTE_NONE to prevent pandas from adding quotes
        chunks = pd.read_csv(input_file, chunksize=chunk_size, low_memory=False)

        # Prepare to track statistics
        total_rows_processed = 0
        files_created = {}
        message_bodies_quoted = 0
        
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
            
            # Ensure message_body has quotes
            message_bodies_without_quotes_count = 0
            if 'message_body' in df.columns:
                # Count messages without quotes before conversion
                message_bodies_without_quotes_count = sum(
                    not (str(val).startswith('"') and str(val).endswith('"') and str(val).count('"') == 2) 
                    for val in df['message_body'] if not pd.isna(val)
                )
                
                # Process message_body
                df['message_body'] = df['message_body'].apply(process_message_body)
                message_bodies_quoted += message_bodies_without_quotes_count
                
                logger.info(f"{Fore.BLUE}Processed {Fore.YELLOW}{message_bodies_without_quotes_count:,}{Fore.BLUE} message bodies in this chunk{Style.RESET_ALL}")
            
            # Parse date_received for Tag column and for splitting by day
            logger.info("Parsing dates for Tag column and day splitting...")
            
            # Ensure date_received is properly formatted
            df['date_received'] = pd.to_datetime(df['date_received'], errors='coerce')
            
            # Remove rows with invalid dates
            invalid_dates = df['date_received'].isna().sum()
            if invalid_dates > 0:
                logger.warning(f"Found {invalid_dates} rows with invalid dates. These will be excluded.")
                df = df.dropna(subset=['date_received'])
            
            # Add the three new columns
            logger.info("Adding new calculated columns...")
            
            # 1. Tag with new time component
            df['Tag'] = df.apply(create_tag, axis=1)
            
            # Debug output for first few rows of first chunk
            if i == 0:
                for idx, row in df.head(3).iterrows():
                    logger.info(f"Row {idx} - UDH: '{row.get('udh', 'N/A')}', To: '{row.get('to', 'N/A')}'")
                    logger.info(f"Row {idx} - Date Received: '{row.get('date_received', 'N/A')}'")
                    logger.info(f"Row {idx} - Tag: '{row.get('Tag', 'N/A')}'")
                    if 'message_body' in row:
                        logger.info(f"Row {idx} - Message Body: {row.get('message_body', 'N/A')}")
            
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
            
            # Extract date part only (without time)
            df['date_key'] = df['date_received'].dt.date
            
            # After processing, log stats about empty/filled tag columns
            empty_tags = (df['Tag'] == "").sum()
            filled_tags = len(df) - empty_tags
            logger.info(f"{Fore.BLUE}Tags generated: {Fore.GREEN}{filled_tags:,} filled, {Fore.YELLOW}{empty_tags:,} empty{Style.RESET_ALL}")
            
            # Group by date and write each group to a separate file
            date_groups = df.groupby('date_key')
            logger.info(f"{Fore.BLUE}Writing data to {len(date_groups)} date-specific files...{Style.RESET_ALL}")
            
            for date, group in date_groups:
                # Remove the temporary date_key column
                group = group.drop('date_key', axis=1)
                
                # Replace NaN values with empty strings
                group = group.fillna('')
                
                # Create filename based on date
                date_str = date.strftime('%Y-%m-%d')
                filename = f"{api_key}-{date_str}.csv"
                filepath = output_path / filename
                
                # Check if file already exists (for append mode)
                file_exists = os.path.isfile(filepath)
                
                # Use csv module directly with explicit quoting configuration
                if not file_exists:
                    # Create new file with header
                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                        writer.writerow(group.columns)
                
                # Write the data
                with open(filepath, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                    for _, row in group.iterrows():
                        writer.writerow(row.tolist())
                
                # After writing, fix any triple quotes in the file
                fix_triple_quotes(filepath)
                
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
    logger.info(f"{Fore.GREEN}Message bodies quoted: {Style.BRIGHT}{message_bodies_quoted:,}")
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
        "total_output_size": total_output_size,
        "message_bodies_quoted": message_bodies_quoted
    }

def main():
    """Main function to handle command-line arguments and start processing."""
    # Print welcome banner
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'BROADCHAINS REPORT PARSER v1.1.0':^80}")
    print(f"{Fore.CYAN}{'Created by Romain EDIN for Vonage':^80}")
    print(f"{Fore.CYAN}{'='*80}\n")
    
    if len(sys.argv) < 2:
        logger.error(f"{Fore.RED}Usage: python broadchains_report_parser.py input.csv [output_dir]{Style.RESET_ALL}")
        sys.exit(1)
    
    input_file = sys.argv[1]
    # Default output directory is 'output' in the current directory
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    logger.info(f"\n{Fore.GREEN}CSV Processor started{Style.RESET_ALL}")
    logger.info(f"{Fore.BLUE}Python version: {sys.version}{Style.RESET_ALL}\n")
    
    stats = process_csv(input_file, output_dir)
    
    if stats:
        logger.info(f"\n{Fore.GREEN}{Style.BRIGHT}CSV processing completed successfully!{Style.RESET_ALL}")
        if stats.get("message_bodies_quoted", 0) > 0:
            logger.info(f"{Fore.GREEN}{Style.BRIGHT}Added quotes to {stats['message_bodies_quoted']:,} message bodies{Style.RESET_ALL}")
    else:
        logger.error(f"\n{Fore.RED}{Style.BRIGHT}CSV processing failed. Check logs for details.{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'END OF PROCESSING':^80}")
    print(f"{Fore.CYAN}{'='*80}\n")

if __name__ == "__main__":
    main()
