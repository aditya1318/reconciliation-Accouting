#!/usr/bin/env python
"""
Example script demonstrating the use of the flexible schema mapping framework.

This script shows how to:
1. Use SchemaMapper directly to process different data formats
2. Use the updated BankReconciler with SchemaMapper
3. Register and use custom schema configurations
"""

import os
import logging
import pandas as pd
import yaml
from datetime import datetime

from bank_recon.schema_mapper.mapper import SchemaMapper
from bank_recon.schema_mapper.registry import SchemaRegistry
from bank_recon.reconciler_updated import BankReconciler


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('schema_mapping_example')


def create_sample_schema():
    """Create a sample custom schema for demonstration."""
    logger = setup_logging()
    
    # Create required directories
    os.makedirs(os.path.join('examples', 'bank_schemas'), exist_ok=True)
    os.makedirs(os.path.join('examples', 'internal_schemas'), exist_ok=True)
    os.makedirs(os.path.join('examples', 'transformers'), exist_ok=True)
    
    # Define a custom schema for a fictional bank format
    custom_schema = {
        'name': 'ACME Bank',
        'id': 'acme_bank',
        'version': '1.0.0',
        'description': 'Schema configuration for ACME Bank statements',
        
        'source': {
            'supported_formats': ['csv', 'excel'],
            'encoding': 'utf-8',
            'csv_options': {
                'delimiter': ',',
                'header_row': 0
            },
            'excel_options': {
                'header_row': 0
            },
            'detection_rules': {
                'column_patterns': [
                    'Transaction Date',
                    'Debit Amount',
                    'Credit Amount',
                    'Description',
                    'Balance'
                ]
            }
        },
        
        'field_mappings': {
            'date': {
                'source': 'Transaction Date',
                'type': 'date',
                'required': True,
                'format': '%d-%m-%Y'
            },
            'debit': {
                'source': 'Debit Amount',
                'type': 'decimal',
                'required': False,
                'transform': 'clean_amount'
            },
            'credit': {
                'source': 'Credit Amount',
                'type': 'decimal',
                'required': False,
                'transform': 'clean_amount'
            },
            'narration': {
                'source': 'Description',
                'type': 'string',
                'required': True,
                'transform': 'clean_description'
            },
            'balance': {
                'source': 'Balance',
                'type': 'decimal',
                'required': True,
                'transform': 'clean_amount'
            }
        },
        
        'derived_fields': {
            'payment_method': {
                'transform': 'extract_payment_method',
                'source': 'narration',
                'type': 'string'
            },
            'reference_id': {
                'transform': 'extract_reference_id',
                'source': 'narration',
                'type': 'string'
            }
        },
        
        'validation_rules': [
            {
                'rule': 'not_null',
                'field': 'date',
                'error_message': 'Transaction date cannot be null'
            },
            {
                'rule': 'custom',
                'expression': 'not (df["debit"].isna() & df["credit"].isna())',
                'error_message': 'Either debit or credit must have a value'
            }
        ],
        
        'audit': {
            'enabled': True,
            'track_fields': ['date', 'narration', 'debit', 'credit'],
            'track_transformations': True
        }
    }
    
    # Make sure directories exist
    os.makedirs(os.path.join('examples', 'bank_schemas'), exist_ok=True)
    os.makedirs(os.path.join('examples', 'internal_schemas'), exist_ok=True)
    os.makedirs(os.path.join('examples', 'transformers'), exist_ok=True)
    
    # Save the schema to the bank_schemas directory where SchemaRegistry expects it
    custom_schema_path = os.path.join('examples', 'bank_schemas', 'acme_bank.yaml')
    with open(custom_schema_path, 'w') as f:
        yaml.dump(custom_schema, f, sort_keys=False, indent=2)
    
    # Create internal schema
    internal_schema = {
        'name': 'Sample Internal Records',
        'id': 'sample_internal',
        'version': '1.0.0',
        'description': 'Schema configuration for sample internal records',
        'source': {
            'supported_formats': ['csv', 'excel'],
            'encoding': 'utf-8',
            'csv_options': {
                'delimiter': ',',
                'header_row': 0
            },
            'excel_options': {
                'header_row': 0
            },
            'detection_rules': {
                'column_patterns': [
                    'Date',
                    'Description',
                    'Amount',
                    'Reference'
                ]
            }
        },
        'field_mappings': {
            'date': {
                'source': 'Date',
                'type': 'date',
                'required': True
            },
            'description': {
                'source': 'Description',
                'type': 'string',
                'required': True
            },
            'amount': {
                'source': 'Amount',
                'type': 'decimal',
                'required': True
            },
            'reference': {
                'source': 'Reference',
                'type': 'string',
                'required': False
            }
        },
        'validation_rules': [
            {
                'rule': 'not_null',
                'field': 'date',
                'error_message': 'Date cannot be null'
            },
            {
                'rule': 'not_null',
                'field': 'amount',
                'error_message': 'Amount cannot be null'
            }
        ],
        'audit': {
            'enabled': True,
            'track_fields': ['date', 'description', 'amount', 'reference'],
            'track_transformations': True
        }
    }
    
    # Save the internal schema
    internal_schema_path = os.path.join('examples', 'internal_schemas', 'sample_internal.yaml')
    with open(internal_schema_path, 'w') as f:
        yaml.dump(internal_schema, f, sort_keys=False, indent=2)
    
    logger.info(f"Created custom bank schema: {custom_schema_path}")
    logger.info(f"Created custom internal schema: {internal_schema_path}")
    
    return custom_schema_path, internal_schema_path


def create_sample_data():
    """Create sample data for demonstration."""
    logger = setup_logging()
    
    # Create a directory for sample data
    os.makedirs('examples/data', exist_ok=True)
    
    # Create a sample bank statement
    bank_data = [
        {
            'Transaction Date': '15-01-2025',
            'Debit Amount': 5000.00,
            'Credit Amount': None,
            'Description': 'UPI PAYMENT TO AMAZON INDIA',
            'Balance': 95000.00
        },
        {
            'Transaction Date': '18-01-2025',
            'Debit Amount': None,
            'Credit Amount': 12000.00,
            'Description': 'SALARY CREDIT FROM ABC CORP',
            'Balance': 107000.00
        },
        {
            'Transaction Date': '20-01-2025',
            'Debit Amount': 2500.00,
            'Credit Amount': None,
            'Description': 'NEFT PAYMENT TO RENT REF123456',
            'Balance': 104500.00
        },
        {
            'Transaction Date': '25-01-2025',
            'Debit Amount': 1200.00,
            'Credit Amount': None,
            'Description': 'BILL PAYMENT - ELECTRICITY BILL',
            'Balance': 103300.00
        },
        {
            'Transaction Date': '28-01-2025',
            'Debit Amount': None,
            'Credit Amount': 7500.00,
            'Description': 'FD INTEREST CREDIT',
            'Balance': 110800.00
        }
    ]
    
    # Create sample internal records
    internal_data = [
        {
            'Date': '2025-01-15',
            'Description': 'Payment to Amazon',
            'Amount': -5000.00,
            'Reference': 'AMZ123'
        },
        {
            'Date': '2025-01-18',
            'Description': 'Salary Credit',
            'Amount': 12000.00,
            'Reference': 'SAL-JAN'
        },
        {
            'Date': '2025-01-20',
            'Description': 'Rent Payment',
            'Amount': -2500.00,
            'Reference': 'RENT-JAN'
        },
        {
            'Date': '2025-01-26',  # Slight date mismatch
            'Description': 'Electricity Bill',
            'Amount': -1200.00,
            'Reference': 'ELEC-JAN'
        },
        {
            'Date': '2025-01-28',
            'Description': 'Fixed Deposit Interest',
            'Amount': 7500.00,
            'Reference': 'FD-INT'
        },
        {
            'Date': '2025-01-30',
            'Description': 'Internet Bill',  # Unmatched transaction
            'Amount': -1000.00,
            'Reference': 'NET-JAN'
        }
    ]
    
    # Save as CSV
    bank_df = pd.DataFrame(bank_data)
    internal_df = pd.DataFrame(internal_data)
    
    bank_path = os.path.join('examples', 'data', 'acme_bank_statement.csv')
    internal_path = os.path.join('examples', 'data', 'internal_records.csv')
    
    bank_df.to_csv(bank_path, index=False)
    internal_df.to_csv(internal_path, index=False)
    
    logger.info(f"Created sample bank statement: {bank_path}")
    logger.info(f"Created sample internal records: {internal_path}")
    
    return bank_path, internal_path


def example_schema_mapper_direct_usage():
    """Example of using SchemaMapper directly."""
    logger = setup_logging()
    logger.info("=== Direct SchemaMapper Usage Example ===")
    
    # Create sample data and schemas
    bank_schema_path, internal_schema_path = create_sample_schema()
    bank_path, internal_path = create_sample_data()
    
    # Initialize SchemaMapper with custom config directory
    custom_config_dir = 'examples'
    schema_mapper = SchemaMapper(config_dir=custom_config_dir, logger=logger)
    
    # Process bank statement
    logger.info("Processing bank statement with SchemaMapper...")
    bank_df, process_info = schema_mapper.process_bank_statement(
        bank_path, schema_id='acme_bank'
    )
    
    logger.info(f"Processed {len(bank_df)} bank transactions")
    logger.info(f"Validation result: {'Valid' if process_info['is_valid'] else 'Invalid'}")
    
    # Display the transformed data
    print("\nTransformed Bank Data:")
    print(bank_df.head())
    
    # Example of processing internal records
    logger.info("\nProcessing internal records...")
    
    # Refresh the schema registry to ensure our schemas are loaded
    schema_mapper.refresh_schemas()
    
    # Use the sample_internal schema now available in examples/internal_schemas/
    
    internal_df, internal_info = schema_mapper.process_internal_records(
        internal_path, schema_id='sample_internal'
    )
    
    logger.info(f"Processed {len(internal_df)} internal records")
    
    # Display the transformed data
    print("\nTransformed Internal Data:")
    print(internal_df.head())
    
    return bank_df, internal_df


def example_bank_reconciler_usage():
    """Example of using BankReconciler with SchemaMapper."""
    logger = setup_logging()
    logger.info("\n=== BankReconciler with SchemaMapper Example ===")
    
    # Get the sample data paths
    bank_path, internal_path = create_sample_data()
    
    # Initialize BankReconciler
    reconciler = BankReconciler(
        date_tolerance_days=2,
        amount_tolerance_percentage=0.01,
        description_match_threshold=70,
        logger=logger
    )
    
    # Replace the schema_mapper in the BankReconciler with our custom one
    custom_schema_mapper = SchemaMapper(config_dir='examples', logger=logger)
    reconciler.schema_mapper = custom_schema_mapper
    
    # Also need to update the parser's schema_mapper since it's initialized separately
    reconciler.parser.schema_mapper = custom_schema_mapper
    
    # Process the statements manually to add transaction_ids
    logger.info("Processing bank statement...")
    bank_df, bank_info = custom_schema_mapper.process_bank_statement(
        bank_path, schema_id='acme_bank'
    )
    
    # Add transaction_id to bank DataFrame if it doesn't exist
    if 'transaction_id' not in bank_df.columns:
        bank_df['transaction_id'] = [f"BANK_{i}" for i in range(len(bank_df))]
    
    logger.info("Processing internal records...")
    internal_df, internal_info = custom_schema_mapper.process_internal_records(
        internal_path, schema_id='sample_internal'
    )
    
    # Add transaction_id to internal DataFrame if it doesn't exist
    if 'transaction_id' not in internal_df.columns:
        internal_df['transaction_id'] = [f"INT_{i}" for i in range(len(internal_df))]
    
    # Match the transactions directly
    logger.info("Matching transactions...")
    results = reconciler.matcher.match_transactions(bank_df, internal_df, reconciler.match_criteria)
    reconciler.matched_transactions, reconciler.unmatched_bank_transactions, \
    reconciler.unmatched_internal_transactions, reconciler.partial_matches = results
    
    # Calculate summary statistics
    summary = {
        'total_bank_transactions': len(bank_df),
        'total_internal_records': len(internal_df),
        'matched_count': len(reconciler.matched_transactions),
        'unmatched_bank_count': len(reconciler.unmatched_bank_transactions),
        'unmatched_internal_count': len(reconciler.unmatched_internal_transactions),
        'match_rate': (len(reconciler.matched_transactions) / len(bank_df)) if len(bank_df) > 0 else 0
    }
    
    # Display reconciliation summary
    print("\nReconciliation Summary:")
    print(f"Total Bank Transactions: {summary['total_bank_transactions']}")
    print(f"Total Internal Records: {summary['total_internal_records']}")
    print(f"Matched Transactions: {summary['matched_count']}")
    print(f"Match Rate: {summary['match_rate'] * 100:.2f}%")
    print(f"Unmatched Bank Transactions: {summary['unmatched_bank_count']}")
    print(f"Unmatched Internal Records: {summary['unmatched_internal_count']}")
    
    # Display matched transactions
    if not reconciler.matched_transactions.empty:
        print("\nMatched Transactions (first 3):")
        for i, match in enumerate(reconciler.matched_transactions.head(3).to_dict('records')):
            print(f"Match {i+1}: Bank: {match['bank_date']} {match['bank_amount']} - "
                  f"Internal: {match['internal_date']} {match['internal_amount']} - "
                  f"Type: {match['match_type']}")
    
    # Get detailed reconciliation summary
    detailed_summary = reconciler.get_reconciliation_summary(include_transactions=True)
    
    # Display matched transactions
    if detailed_summary.get('matched_transactions'):
        print("\nMatched Transactions (first 3):")
        for i, match in enumerate(detailed_summary['matched_transactions'][:3]):
            print(f"Match {i+1}: Bank: {match['bank_date']} {match['bank_amount']} - "
                  f"Internal: {match['internal_date']} {match['internal_amount']} - "
                  f"Type: {match['match_type']}")
    
    return summary


def main():
    logger = setup_logging()
    logger.info("Starting Schema Mapping Framework Example")
    
    try:
        # Example 1: Direct SchemaMapper usage
        bank_df, internal_df = example_schema_mapper_direct_usage()
        
        # Example 2: BankReconciler with SchemaMapper
        summary = example_bank_reconciler_usage()
        
        logger.info("Schema Mapping Framework Example completed successfully")
        
    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)


if __name__ == '__main__':
    main()