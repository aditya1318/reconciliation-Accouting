#!/usr/bin/env python
"""
Example script demonstrating OCR and Email integration in the Indian Bank Reconciliation System.

This script shows how to:
1. Extract data from financial documents using OCR
2. Send and receive emails with financial documents
3. Use the integrated workflow for reconciliation

Usage:
    python ocr_email_example.py --mode [ocr|email|integrated] [options]
"""

import os
import argparse
import pandas as pd
from datetime import datetime
import logging

from bank_recon.ocr_processor import OCRProcessor
from bank_recon.email_processor import EmailProcessor
from bank_recon.integration import IntegratedReconciliationSystem


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('ocr_email_example')


def ocr_example(args):
    """Demonstrate OCR functionality."""
    logger = setup_logging()
    logger.info("Starting OCR example")
    
    # Initialize OCR processor
    ocr = OCRProcessor()
    
    if args.file:
        # Process a single file
        logger.info(f"Processing file: {args.file}")
        result = ocr.process_document(args.file)
        
        if isinstance(result, pd.DataFrame):
            logger.info(f"Extracted {len(result)} records")
            print("\nExtracted Data:")
            print(result)
            
            # Save to file if requested
            if args.output:
                if args.output.endswith('.xlsx'):
                    result.to_excel(args.output, index=False)
                elif args.output.endswith('.csv'):
                    result.to_csv(args.output, index=False)
                else:
                    result.to_json(args.output, orient='records')
                logger.info(f"Results saved to {args.output}")
        else:
            logger.error("OCR processing failed")
    
    elif args.directory:
        # Process a directory of files
        logger.info(f"Processing directory: {args.directory}")
        results = ocr.batch_process_directory(
            args.directory,
            recursive=args.recursive
        )
        
        if isinstance(results, pd.DataFrame):
            logger.info(f"Extracted {len(results)} records from {args.directory}")
            print("\nExtracted Data (first 5 records):")
            print(results.head())
            
            # Save to file if requested
            if args.output:
                if args.output.endswith('.xlsx'):
                    results.to_excel(args.output, index=False)
                elif args.output.endswith('.csv'):
                    results.to_csv(args.output, index=False)
                else:
                    results.to_json(args.output, orient='records')
                logger.info(f"Results saved to {args.output}")
        else:
            logger.error("Directory processing failed")
    
    else:
        logger.error("No file or directory specified")


def email_example(args):
    """Demonstrate email functionality."""
    logger = setup_logging()
    logger.info("Starting email example")
    
    # Load environment variables from .env file if it exists
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize email processor
    try:
        email_processor = EmailProcessor(env_file='.env')
        logger.info("Email processor initialized")
    except Exception as e:
        logger.error(f"Failed to initialize email processor: {e}")
        return
    
    if args.action == 'send':
        # Send an email with attachment
        if not args.recipient or not args.attachment:
            logger.error("Both recipient and attachment are required for sending email")
            return
        
        subject = args.subject or f"Financial Document - {datetime.now().strftime('%Y-%m-%d')}"
        body = args.body or "Please find attached the financial document for your reference."
        
        logger.info(f"Sending email to {args.recipient} with subject '{subject}'")
        result = email_processor.send_invoice(
            to_email=args.recipient,
            subject=subject,
            invoice_path=args.attachment,
            body_text=body
        )
        
        if result:
            logger.info("Email sent successfully")
        else:
            logger.error("Failed to send email")
    
    elif args.action == 'receive':
        # Receive emails and process attachments
        logger.info("Fetching emails")
        emails = email_processor.fetch_emails(
            folder=args.folder or 'INBOX',
            search_criteria=args.criteria or 'UNSEEN',
            limit=args.limit or 10,
            process_attachments=True
        )
        
        if emails:
            logger.info(f"Fetched {len(emails)} emails")
            
            # Create reconciliation records from emails
            records = email_processor.create_reconciliation_records_from_emails(
                emails,
                output_format='dataframe',
                save_to_file=args.output
            )
            
            if isinstance(records, pd.DataFrame) and not records.empty:
                logger.info(f"Created {len(records)} reconciliation records")
                print("\nExtracted Records (first 5):")
                print(records.head())
            else:
                logger.warning("No reconciliation records created from emails")
        else:
            logger.warning("No emails found matching criteria")


def integrated_example(args):
    """Demonstrate the integrated reconciliation workflow."""
    logger = setup_logging()
    logger.info("Starting integrated workflow example")
    
    # Check required arguments
    if not args.bank_statement:
        logger.error("Bank statement file is required")
        return
    
    # Initialize the integrated system
    system = IntegratedReconciliationSystem()
    logger.info("Integrated system initialized")
    
    # Set up output directory
    output_dir = args.output_dir or './recon_reports'
    os.makedirs(output_dir, exist_ok=True)
    
    # Run the integrated workflow
    try:
        result = system.integrated_workflow(
            bank_statement_path=args.bank_statement,
            documents_dir=args.documents_dir,
            use_email=args.use_email,
            email_criteria=args.email_criteria or 'UNSEEN',
            output_dir=output_dir,
            report_format=args.report_format or 'all'
        )
        
        if result and result.get('success'):
            logger.info("Integrated workflow completed successfully")
            
            # Print reconciliation statistics
            recon_stats = result.get('reconciliation', {})
            if recon_stats:
                print("\nReconciliation Summary:")
                print(f"Total Bank Transactions: {recon_stats.get('total_bank_transactions', 0)}")
                print(f"Matched Transactions: {recon_stats.get('matched_count', 0)}")
                print(f"Match Rate: {recon_stats.get('match_rate', 0) * 100:.2f}%")
                print(f"Unmatched Bank Transactions: {recon_stats.get('unmatched_bank_count', 0)}")
                print(f"Unmatched Internal Records: {recon_stats.get('unmatched_internal_count', 0)}")
            
            # Show generated reports
            if 'reports' in result:
                print("\nGenerated Reports:")
                for report_type, path in result['reports'].items():
                    print(f"- {report_type.upper()}: {path}")
        else:
            logger.error("Integrated workflow failed")
            if 'error' in result:
                print(f"Error: {result['error']}")
    
    except Exception as e:
        logger.error(f"Error in integrated workflow: {e}")


def main():
    """Main entry point for the example script."""
    parser = argparse.ArgumentParser(description="OCR and Email integration example")
    
    # Common arguments
    parser.add_argument('--output', help="Path to save output")
    
    # Create subparsers for different modes
    subparsers = parser.add_subparsers(dest='mode', help='Mode of operation')
    
    # OCR mode arguments
    ocr_parser = subparsers.add_parser('ocr', help='OCR processing')
    ocr_parser.add_argument('--file', help='Path to document file')
    ocr_parser.add_argument('--directory', help='Path to directory containing documents')
    ocr_parser.add_argument('--recursive', action='store_true', help='Process subdirectories')
    
    # Email mode arguments
    email_parser = subparsers.add_parser('email', help='Email processing')
    email_parser.add_argument('--action', choices=['send', 'receive'], required=True, 
                            help='Email action to perform')
    email_parser.add_argument('--recipient', help='Email recipient (for send)')
    email_parser.add_argument('--subject', help='Email subject (for send)')
    email_parser.add_argument('--body', help='Email body text (for send)')
    email_parser.add_argument('--attachment', help='Path to attachment (for send)')
    email_parser.add_argument('--folder', help='Email folder to check (for receive)')
    email_parser.add_argument('--criteria', help='Search criteria (for receive)')
    email_parser.add_argument('--limit', type=int, help='Maximum emails to process (for receive)')
    
    # Integrated mode arguments
    integrated_parser = subparsers.add_parser('integrated', help='Integrated workflow')
    integrated_parser.add_argument('--bank-statement', help='Path to bank statement file')
    integrated_parser.add_argument('--documents-dir', help='Path to documents directory')
    integrated_parser.add_argument('--use-email', action='store_true', help='Use email processing')
    integrated_parser.add_argument('--email-criteria', help='Email search criteria')
    integrated_parser.add_argument('--output-dir', help='Directory for output reports')
    integrated_parser.add_argument('--report-format', 
                                 choices=['excel', 'csv', 'html', 'json', 'all'],
                                 help='Report format')
    
    args = parser.parse_args()
    
    # Dispatch based on mode
    if args.mode == 'ocr':
        ocr_example(args)
    elif args.mode == 'email':
        email_example(args)
    elif args.mode == 'integrated':
        integrated_example(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()