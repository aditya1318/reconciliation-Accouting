#!/usr/bin/env python
"""
Test script to demonstrate different schema formats for bank reconciliation.

This script demonstrates:
1. Loading and processing ICICI Bank statements with a custom schema
2. Loading and processing QuickBooks internal records with a custom schema
3. Validating data against schema rules
4. Matching transactions between the bank and internal formats
"""

import os
import logging
import pandas as pd
from datetime import datetime
import yaml

from bank_recon.schema_mapper.mapper import SchemaMapper
from bank_recon.matcher import TransactionMatcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('schema_formats_test')

def test_icici_bank_schema():
    """Test the ICICI Bank schema with sample data."""
    logger.info("=== Testing ICICI Bank Schema ===")
    
    # Initialize SchemaMapper with custom config directory
    schema_mapper = SchemaMapper(config_dir='examples', logger=logger)
    
    # Process bank statement
    bank_file = 'examples/data/icici_bank_statement.csv'
    logger.info(f"Processing ICICI bank statement from {bank_file}")
    
    try:
        icici_df, process_info = schema_mapper.process_bank_statement(
            bank_file, schema_id='icici_bank'
        )
        
        # Log validation results
        logger.info(f"Validation result: {'Valid' if process_info['is_valid'] else 'Invalid'}")
        if not process_info['is_valid']:
            logger.warning(f"Validation errors: {process_info['validation_errors']}")
        
        # Display the transformed data
        logger.info(f"Processed {len(icici_df)} bank transactions")
        print("\nTransformed ICICI Bank Data:")
        print(icici_df.head())
        
        # Add default transaction_id if not present
        if 'transaction_id' not in icici_df.columns:
            icici_df['transaction_id'] = [f"ICICI_{i}" for i in range(len(icici_df))]
            
        return icici_df
        
    except Exception as e:
        logger.error(f"Error processing ICICI bank statement: {e}", exc_info=True)
        raise

def test_quickbooks_schema():
    """Test the QuickBooks schema with sample data."""
    logger.info("\n=== Testing QuickBooks Schema ===")
    
    # Initialize SchemaMapper with custom config directory
    schema_mapper = SchemaMapper(config_dir='examples', logger=logger)
    
    # Process internal records
    internal_file = 'examples/data/quickbooks_records.csv'
    logger.info(f"Processing QuickBooks records from {internal_file}")
    
    try:
        qb_df, process_info = schema_mapper.process_internal_records(
            internal_file, schema_id='quickbooks'
        )
        
        # Log validation results
        logger.info(f"Validation result: {'Valid' if process_info['is_valid'] else 'Invalid'}")
        if not process_info['is_valid']:
            logger.warning(f"Validation errors: {process_info['validation_errors']}")
        
        # Display the transformed data
        logger.info(f"Processed {len(qb_df)} internal transactions")
        print("\nTransformed QuickBooks Data:")
        print(qb_df.head())
        
        # Add default transaction_id if not present
        if 'transaction_id' not in qb_df.columns:
            qb_df['transaction_id'] = [f"QB_{i}" for i in range(len(qb_df))]
            
        return qb_df
        
    except Exception as e:
        logger.error(f"Error processing QuickBooks records: {e}", exc_info=True)
        raise

def match_transactions(bank_df, internal_df):
    """Match transactions between bank statement and internal records."""
    logger.info("\n=== Matching Transactions ===")
    
    # Initialize TransactionMatcher
    matcher = TransactionMatcher(
        date_tolerance_days=2,
        amount_tolerance_percentage=0.01,
        description_match_threshold=70
    )
    
    # Standardize dataframes
    bank_df, internal_df = matcher._standardize_dataframes(bank_df, internal_df)
    
    # Match transactions
    matched_df, unmatched_bank_df, unmatched_internal_df, partial_matches_df = matcher.match_transactions(
        bank_df, internal_df, {'amount': 0.5, 'date': 0.3, 'description': 0.2}
    )
    
    # Display results
    match_rate = (len(matched_df) / len(bank_df)) * 100 if len(bank_df) > 0 else 0
    
    print("\nMatching Results:")
    print(f"Total Bank Transactions: {len(bank_df)}")
    print(f"Total Internal Records: {len(internal_df)}")
    print(f"Matched Transactions: {len(matched_df)}")
    print(f"Match Rate: {match_rate:.2f}%")
    print(f"Unmatched Bank Transactions: {len(unmatched_bank_df)}")
    print(f"Unmatched Internal Records: {len(unmatched_internal_df)}")
    
    if not matched_df.empty:
        print("\nMatched Transactions:")
        for i, match in enumerate(matched_df.iterrows()):
            match = match[1]  # Get the Series (row data)
            print(f"Match {i+1}: Bank: {match['bank_date']} {match['bank_amount']} - "
                  f"Internal: {match['internal_date']} {match['internal_amount']} - "
                  f"Score: {match['match_score']:.2f} - Type: {match['match_type']}")
    
    return {
        'matched': matched_df,
        'unmatched_bank': unmatched_bank_df,
        'unmatched_internal': unmatched_internal_df,
        'partial_matches': partial_matches_df
    }

def print_schema_examples():
    """Print examples of the bank and internal schema formats."""
    try:
        with open('examples/bank_schemas/icici_bank.yaml', 'r') as f:
            icici_schema = yaml.safe_load(f)
        
        with open('examples/internal_schemas/quickbooks.yaml', 'r') as f:
            qb_schema = yaml.safe_load(f)
        
        with open('examples/bank_schemas/sbi_bank.yaml', 'r') as f:
            sbi_schema = yaml.safe_load(f)
        
        with open('examples/internal_schemas/zoho_books.yaml', 'r') as f:
            zoho_schema = yaml.safe_load(f)
            
        print("\n=== ICICI Bank Schema Format ===")
        print("Name:", icici_schema['name'])
        print("ID:", icici_schema['id'])
        print("Version:", icici_schema['version'])
        print("Description:", icici_schema['description'])
        print("Field mappings (sample):")
        for i, (key, value) in enumerate(icici_schema['field_mappings'].items()):
            if i >= 3:
                break
            print(f"  {key}: {value}")
        print("...")
        
        print("\n=== SBI Bank Schema Format ===")
        print("Name:", sbi_schema['name'])
        print("ID:", sbi_schema['id'])
        print("Additional features: Pre-processing rules, Custom validation expressions")
        
        print("\n=== QuickBooks Schema Format ===")
        print("Name:", qb_schema['name'])
        print("ID:", qb_schema['id'])
        print("Field mappings (sample):")
        for i, (key, value) in enumerate(qb_schema['field_mappings'].items()):
            if i >= 3:
                break
            print(f"  {key}: {value}")
        print("...")
        
        print("\n=== Zoho Books Schema Format ===")
        print("Name:", zoho_schema['name'])
        print("ID:", zoho_schema['id'])
        print("Additional features: Entity type derivation, Pre-processing text replacement")
        
        # Load and display the complex schemas
        try:
            with open('examples/bank_schemas/multi_currency_bank.yaml', 'r') as f:
                multi_currency_schema = yaml.safe_load(f)
            
            with open('examples/internal_schemas/advanced_erp.yaml', 'r') as f:
                advanced_erp_schema = yaml.safe_load(f)
            
            with open('examples/bank_schemas/ocr_pdf_bank.yaml', 'r') as f:
                ocr_pdf_schema = yaml.safe_load(f)
            
            print("\n\n=== COMPLEX SCHEMA EXAMPLES ===")
            
            print("\n=== Multi-Currency Bank Schema ===")
            print("Name:", multi_currency_schema['name'])
            print("ID:", multi_currency_schema['id'])
            print("Description:", multi_currency_schema['description'])
            print("Unique features:")
            print("- Multi-currency support with currency conversion")
            print("- Support for nested JSON structures")
            print("- Advanced date and amount processing")
            print("- Complex derived fields for financial analysis")
            print("Field count:", len(multi_currency_schema['field_mappings']))
            print("Derived field count:", len(multi_currency_schema['derived_fields']))
            print("Validation rules:", len(multi_currency_schema['validation_rules']))
            
            print("\n=== Advanced ERP Schema ===")
            print("Name:", advanced_erp_schema['name'])
            print("ID:", advanced_erp_schema['id'])
            print("Description:", advanced_erp_schema['description'])
            print("Unique features:")
            print("- Support for XML, JSON, and complex data formats")
            print("- Hierarchical account structures")
            print("- Fiscal year and period calculations")
            print("- Journal balancing validation")
            print("- Tax calculation and tracking")
            print("- Financial impact assessment")
            print("Field count:", len(advanced_erp_schema['field_mappings']))
            print("Derived field count:", len(advanced_erp_schema['derived_fields']))
            print("Validation rules:", len(advanced_erp_schema['validation_rules']))
            
            print("\n=== OCR PDF Bank Schema ===")
            print("Name:", ocr_pdf_schema['name'])
            print("ID:", ocr_pdf_schema['id'])
            print("Description:", ocr_pdf_schema['description'])
            print("Unique features:")
            print("- OCR-specific PDF extraction options")
            print("- Multiple date format handling")
            print("- OCR error correction rules")
            print("- Confidence scoring for extracted data")
            print("- Custom functions for data cleaning and validation")
            print("- Balance continuity checking")
            if 'functions' in ocr_pdf_schema:
                print("Custom functions:", len(ocr_pdf_schema['functions']))
            print("Field count:", len(ocr_pdf_schema['field_mappings']))
            print("Derived field count:", len(ocr_pdf_schema['derived_fields']))
            print("Validation rules:", len(ocr_pdf_schema['validation_rules']))
            
        except Exception as e:
            logger.error(f"Error loading complex schemas: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error printing schema examples: {e}", exc_info=True)
    
def main():
    """Main test function."""
    try:
        logger.info("Starting Schema Formats Test")
        
        # Print schema examples
        print_schema_examples()
        
        # Test ICICI Bank schema
        icici_df = test_icici_bank_schema()
        
        # Test QuickBooks schema
        qb_df = test_quickbooks_schema()
        
        # Match transactions
        match_results = match_transactions(icici_df, qb_df)
        
        logger.info("Schema Formats Test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)

if __name__ == '__main__':
    main()