#!/usr/bin/env python
"""
Example script demonstrating how to use the Indian Bank Reconciliation System.

This script shows how to use the bank_recon package to reconcile bank statements
with internal accounting records and generate reconciliation reports.
"""

import os
import pandas as pd
from datetime import datetime
import logging

from bank_recon.parser import BankStatementParser
from bank_recon.reconciler import BankReconciler
from bank_recon.report_generator import ReconciliationReportGenerator


def setup_logging():
    """Set up logger for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('bank_recon_example')


def create_sample_bank_statement(output_path):
    """Create a sample bank statement file for demonstration."""
    # Sample HDFC bank statement with a variety of transaction types
    data = {
        'Date': [
            '01/04/2024', '05/04/2024', '10/04/2024', '15/04/2024', 
            '18/04/2024', '20/04/2024', '25/04/2024', '28/04/2024'
        ],
        'Value Date': [
            '01/04/2024', '05/04/2024', '10/04/2024', '15/04/2024', 
            '18/04/2024', '20/04/2024', '25/04/2024', '28/04/2024'
        ],
        'Narration': [
            'UPI/123456789012/PAYMENT TO TATA POWER FROM ADITYA',
            'NEFT/SBIN545454/SALARY PAYMENT FROM INFOSYS LIMITED',
            'UPI/987654321098/PAYMENT TO SWIGGY FROM ADITYA',
            'IMPS/P2A/121212121212/PAYMENT FROM ANIL KUMAR GST@18%',
            'CHQ/123456/PAYMENT TO HDFC CREDIT CARD',
            'UPI/456789123456/PAYMENT TO AMAZON.IN',
            'ATM/WITHDRAWAL/HDFC0000123/ANDHERI EAST',
            'NEFT/AXIS9876543/TDS DEDUCTED BY XYZ CORP'
        ],
        'Chq/Ref Number': [
            'UPI123456789012', 'NEFT0000545454', 'UPI987654321098', 
            'IMPS121212121212', '123456', 'UPI456789123456', 
            'ATM123456', 'NEFTAXIS9876543'
        ],
        'Withdrawal Amt': [
            2500.00, 0, 750.50, 0, 15000.00, 4299.00, 10000.00, 0
        ],
        'Deposit Amt': [
            0, 75000.00, 0, 11800.00, 0, 0, 0, 750.00
        ],
        'Closing Balance': [
            47500.00, 122500.00, 121749.50, 133549.50, 118549.50, 114250.50, 104250.50, 105000.50
        ]
    }
    
    df = pd.DataFrame(data)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to Excel file
    df.to_excel(output_path, index=False)
    
    return output_path


def create_sample_internal_records(output_path):
    """Create sample internal accounting records for demonstration."""
    # Sample internal accounting records
    data = {
        'date': [
            '2024-04-01', '2024-04-05', '2024-04-10', '2024-04-16', 
            '2024-04-19', '2024-04-20', '2024-04-25', '2024-04-28',
            '2024-04-30' # Additional unmatched record
        ],
        'reference': [
            'UPI123456789012', 'NEFT0000545454', 'UPI987654321098', 
            'INV/2024/0412', '123456', 'UPI456789123456', 
            'ATM123456', 'TDS-XYZ-2024',
            'PENDING-PAYMENT'
        ],
        'description': [
            'Payment to Tata Power', 'Salary from Infosys Ltd', 'Payment to Swiggy', 
            'Payment from Anil Kumar for services', 'Credit card bill payment', 
            'Amazon.in purchase', 'Cash withdrawal', 'TDS deduction',
            'Internet bill payment'
        ],
        'amount': [
            -2500.00, 75000.00, -750.50, 10000.00, -15000.00, -4299.00, -10000.00, 750.00,
            -2999.00
        ],
    }
    
    df = pd.DataFrame(data)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to Excel file
    df.to_excel(output_path, index=False)
    
    return output_path


def main():
    """Run the example reconciliation process."""
    logger = setup_logging()
    logger.info("Starting Indian Bank Reconciliation Example")
    
    # Create sample files in the 'examples' directory
    examples_dir = 'examples'
    os.makedirs(examples_dir, exist_ok=True)
    
    bank_statement_path = os.path.join(examples_dir, 'sample_hdfc_statement.xlsx')
    internal_records_path = os.path.join(examples_dir, 'sample_internal_records.xlsx')
    
    logger.info("Creating sample data files...")
    create_sample_bank_statement(bank_statement_path)
    create_sample_internal_records(internal_records_path)
    
    # Initialize the reconciler with reconciliation parameters
    logger.info("Initializing reconciler...")
    reconciler = BankReconciler(
        date_tolerance_days=2,                # Allow up to 2 days difference in dates
        amount_tolerance_percentage=0.05,     # Allow up to 5% difference in amounts
        description_match_threshold=75,       # Fuzzy matching threshold for descriptions
        match_criteria={
            'amount': 0.6,                    # Weight for amount matching
            'date': 0.3,                      # Weight for date matching
            'description': 0.1                # Weight for description matching
        }
    )
    
    # Run reconciliation process
    logger.info("Running reconciliation...")
    summary = reconciler.reconcile(
        bank_statement_path=bank_statement_path,
        internal_records_path=internal_records_path,
        bank='hdfc',                          # Specify the bank for parsing
        sheet_name=0                          # Use first sheet in each Excel file
    )
    
    # Display reconciliation summary
    logger.info("Reconciliation Results:")
    logger.info(f"Total Bank Transactions: {summary['total_bank_transactions']}")
    logger.info(f"Matched Transactions: {summary['matched_count']}")
    logger.info(f"Unmatched Bank Transactions: {summary['unmatched_bank_count']}")
    logger.info(f"Unmatched Internal Records: {summary['unmatched_internal_count']}")
    logger.info(f"Partial Matches: {summary['partial_matches_count']}")
    match_rate = summary['match_rate'] * 100
    logger.info(f"Match Rate: {match_rate:.2f}%")
    
    # Generate reports
    reports_dir = os.path.join(examples_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    report_generator = ReconciliationReportGenerator(
        output_dir=reports_dir,
        logger=logger
    )
    
    # Generate reports in different formats
    logger.info("Generating reports...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"reconciliation_example_{timestamp}"
    
    # Excel report (includes all data in different sheets)
    excel_path = report_generator.generate_excel_report(
        reconciler=reconciler,
        output_path=os.path.join(reports_dir, f"{filename_base}.xlsx")
    )
    logger.info(f"Excel report generated: {excel_path}")
    
    # CSV reports (multiple files, one for each component)
    csv_reports = report_generator.generate_csv_reports(
        reconciler=reconciler,
        base_filename=filename_base
    )
    logger.info(f"CSV reports generated in: {reports_dir}")
    
    # HTML report (single file with all data)
    html_path = report_generator.generate_html_report(
        reconciler=reconciler,
        output_path=os.path.join(reports_dir, f"{filename_base}.html")
    )
    logger.info(f"HTML report generated: {html_path}")
    
    # JSON report (all data in JSON format)
    json_path = report_generator.generate_json_report(
        reconciler=reconciler,
        output_path=os.path.join(reports_dir, f"{filename_base}.json")
    )
    logger.info(f"JSON report generated: {json_path}")
    
    logger.info("Example completed successfully!")
    logger.info(f"Reports available in: {reports_dir}")


if __name__ == "__main__":
    main()