#!/usr/bin/env python
"""
Example script demonstrating GST and TDS handling in the Indian Bank Reconciliation System.

This script focuses specifically on reconciliation scenarios involving:
1. GST-inclusive amounts (common in Indian invoices)
2. TDS deductions (Tax Deducted at Source)
3. Multiple payment references common in Indian banking
"""

import os
import pandas as pd
import logging
from datetime import datetime

from bank_recon.reconciler import BankReconciler
from bank_recon.report_generator import ReconciliationReportGenerator


def setup_logging():
    """Set up logger for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('gst_tds_example')


def create_gst_tds_bank_statement(output_path):
    """Create a sample bank statement file with GST and TDS transactions."""
    # Sample bank statement with GST and TDS scenarios
    data = {
        'Date': [
            '01/05/2024', '05/05/2024', '10/05/2024', '15/05/2024', 
            '20/05/2024', '25/05/2024'
        ],
        'Value Date': [
            '01/05/2024', '05/05/2024', '10/05/2024', '15/05/2024', 
            '20/05/2024', '25/05/2024'
        ],
        'Narration': [
            'UPI/987654321098/GST INVOICE PAYMENT FROM ABC ENTERPRISES CGST+SGST 18%',
            'NEFT/SBIN123456/INVOICE#INV-2024-001 PAYMENT INCLUSIVE OF GST',
            'TRF/IMPS/P2A/121212121212/PAYMENT FROM XYZ CORP TDS DEDUCTED @10%',
            'UPI/765432109876/RENT PAYMENT TO LANDLORD TDS DEDUCTED',
            'RTGS/HDFC987654/CONSULTING SERVICES GST@18% PAID TO INFOSYS',
            'CHQ/987654/PAYMENT FROM TATA CONSULTANCY LIMITED WITH 2% TDS DEDUCTION'
        ],
        'Chq/Ref Number': [
            'UPI987654321098', 'NEFTSBIN123456', 'IMPS121212121212', 
            'UPI765432109876', 'RTGSHDFC987654', '987654'
        ],
        'Withdrawal Amt': [
            0, 0, 0, 45000.00, 59000.00, 0
        ],
        'Deposit Amt': [
            23600.00, 29500.00, 36000.00, 0, 0, 98000.00
        ],
        'Closing Balance': [
            123600.00, 153100.00, 189100.00, 144100.00, 85100.00, 183100.00
        ]
    }
    
    df = pd.DataFrame(data)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to Excel file
    df.to_excel(output_path, index=False)
    
    return output_path


def create_gst_tds_internal_records(output_path):
    """Create sample internal accounting records with GST and TDS transactions."""
    # Sample internal accounting records without GST added
    data = {
        'date': [
            '2024-05-01', '2024-05-05', '2024-05-11', '2024-05-15', 
            '2024-05-21', '2024-05-25'
        ],
        'reference': [
            'INV-ABC-2024-05-01', 'INV-2024-001', 'INV-XYZ-2024-05', 
            'RENT-MAY-2024', 'PO-INFY-2024-123', 'TCS-PAYMENT-MAY'
        ],
        'description': [
            'Invoice payment from ABC Enterprises', 'Invoice payment', 
            'Payment from XYZ Corporation', 'Rent payment to Mr. Sharma', 
            'Consulting services to Infosys', 'Payment from TCS'
        ],
        'amount': [
            # Base amount without GST (18% less)
            20000.00,
            # Base amount without GST
            25000.00,
            # Payment amount after 10% TDS deduction
            36000.00,
            # Rent payment with TDS consideration
            -50000.00,
            # Payment for consulting services without GST
            -50000.00,
            # Original payment amount before TDS deduction
            100000.00
        ],
    }
    
    df = pd.DataFrame(data)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to Excel file
    df.to_excel(output_path, index=False)
    
    return output_path


def main():
    """Run GST and TDS reconciliation example."""
    logger = setup_logging()
    logger.info("Starting GST and TDS Reconciliation Example")
    
    # Create sample files in the 'examples' directory
    examples_dir = 'examples'
    gst_tds_dir = os.path.join(examples_dir, 'gst_tds_example')
    os.makedirs(gst_tds_dir, exist_ok=True)
    
    bank_statement_path = os.path.join(gst_tds_dir, 'sample_gst_tds_bank_statement.xlsx')
    internal_records_path = os.path.join(gst_tds_dir, 'sample_gst_tds_internal_records.xlsx')
    
    logger.info("Creating sample GST/TDS transaction data files...")
    create_gst_tds_bank_statement(bank_statement_path)
    create_gst_tds_internal_records(internal_records_path)
    
    # Initialize reconciler with parameters optimized for GST/TDS scenarios
    logger.info("Initializing reconciler with GST/TDS-friendly parameters...")
    reconciler = BankReconciler(
        date_tolerance_days=3,                # Allow up to 3 days difference
        amount_tolerance_percentage=0.20,     # Allow up to 20% difference for GST/TDS variations
        description_match_threshold=70,       # Lower threshold for more flexible matching
        match_criteria={
            'amount': 0.4,                    # Lower weight for amount (since GST/TDS causes variations)
            'date': 0.4,                      # Higher weight for date
            'description': 0.2                # Moderate weight for description
        }
    )
    
    # Run reconciliation process
    logger.info("Running GST/TDS reconciliation...")
    summary = reconciler.reconcile(
        bank_statement_path=bank_statement_path,
        internal_records_path=internal_records_path,
        bank='hdfc'                          # Using HDFC format for example
    )
    
    # Display reconciliation summary
    logger.info("GST/TDS Reconciliation Results:")
    logger.info(f"Total Bank Transactions: {summary['total_bank_transactions']}")
    logger.info(f"Matched Transactions: {summary['matched_count']}")
    logger.info(f"Unmatched Bank Transactions: {summary['unmatched_bank_count']}")
    logger.info(f"Unmatched Internal Records: {summary['unmatched_internal_count']}")
    logger.info(f"Partial Matches: {summary['partial_matches_count']}")
    match_rate = summary['match_rate'] * 100
    logger.info(f"Match Rate: {match_rate:.2f}%")
    
    # Generate HTML report for easy visualization
    reports_dir = os.path.join(gst_tds_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    report_generator = ReconciliationReportGenerator(
        output_dir=reports_dir,
        logger=logger
    )
    
    # Generate HTML report with highlighted GST/TDS matches
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    html_path = report_generator.generate_html_report(
        reconciler=reconciler,
        output_path=os.path.join(reports_dir, f"gst_tds_reconciliation_{timestamp}.html")
    )
    
    # Explain the GST/TDS handling features
    print("\n===== GST and TDS Handling Features =====")
    print("\n1. GST Handling:")
    print("   - Automatically detects GST mentions in transaction descriptions")
    print("   - Adjusts for common GST rates (18%) when matching amounts")
    print("   - Example: Bank shows ₹23,600 (with GST) while internal record shows ₹20,000 (base amount)")
    
    print("\n2. TDS Handling:")
    print("   - Identifies TDS deductions in transaction descriptions")
    print("   - Accounts for standard TDS rates (2%, 10%) when comparing amounts")
    print("   - Example: Bank shows ₹98,000 (after 2% TDS) while internal record shows ₹100,000 (original amount)")
    
    print("\n3. Amount Tolerance:")
    print("   - Uses higher tolerance for transactions with GST/TDS indicators")
    print("   - Applies different matching weights for better reconciliation")
    
    logger.info(f"GST/TDS example HTML report generated at: {html_path}")
    logger.info("GST/TDS Example completed successfully!")


if __name__ == "__main__":
    main()