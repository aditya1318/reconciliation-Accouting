"""
Command Line Interface for Indian Bank Reconciliation System.

This module provides a CLI interface to the bank reconciliation system,
allowing users to perform reconciliation operations from the command line,
including OCR processing and email integration.
"""

import argparse
import os
import sys
import logging
from datetime import datetime
import json
from dotenv import load_dotenv

from .parser import BankStatementParser
from .reconciler import BankReconciler
from .report_generator import ReconciliationReportGenerator
from .ocr_processor import OCRProcessor
from .email_processor import EmailProcessor
from .integration import IntegratedReconciliationSystem


def setup_logging(verbose=False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('bank_recon_cli')


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Indian Bank Reconciliation System with OCR and Email Integration',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Create subparsers for different operation modes
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # === Traditional Reconciliation Command ===
    recon_parser = subparsers.add_parser('reconcile', help='Perform traditional bank reconciliation')
    recon_parser.add_argument('--bank-statement', '-b', required=True,
                        help='Path to bank statement file (CSV/Excel)')
    recon_parser.add_argument('--internal-records', '-i', required=True,
                        help='Path to internal records file (CSV/Excel)')
    recon_parser.add_argument('--bank', '-bn',
                        help='Bank identifier (e.g., hdfc, sbi, icici, axis, yes_bank)')
    recon_parser.add_argument('--sheet-name', '-s', default=0,
                        help='Sheet name or index for Excel files (default: 0)')
    recon_parser.add_argument('--internal-date-format', '-df',
                        help='Date format for internal records (e.g., %%d/%%m/%%Y)')
    
    # Matching parameters
    recon_parser.add_argument('--date-tolerance', '-dt', type=int, default=3,
                        help='Maximum days difference for date matching')
    recon_parser.add_argument('--amount-tolerance', '-at', type=float, default=0.01,
                        help='Maximum percentage difference for amount matching')
    recon_parser.add_argument('--description-threshold', '-tm', type=int, default=80,
                        help='Threshold for fuzzy description matching (0-100)')
    
    # Report generation
    recon_parser.add_argument('--output-dir', '-o', default='./reports',
                        help='Directory for saving reports')
    recon_parser.add_argument('--report-format', '-rf', choices=['excel', 'csv', 'html', 'json', 'all'],
                        default='excel', help='Report format(s) to generate')
    recon_parser.add_argument('--filename', '-f',
                        help='Base filename for reports (default: timestamp-based)')
    
    # Other options
    recon_parser.add_argument('--config', '-c',
                        help='Path to custom bank formats configuration file')
    
    # === OCR Processing Command ===
    ocr_parser = subparsers.add_parser('ocr', help='Process documents using OCR')
    ocr_parser.add_argument('--documents-dir', '-d', required=True,
                      help='Directory containing documents to process')
    ocr_parser.add_argument('--output-path', '-o',
                      help='Path to save extracted data (CSV, Excel, or JSON)')
    ocr_parser.add_argument('--recursive', '-r', action='store_true',
                      help='Recursively process documents in subdirectories')
    ocr_parser.add_argument('--tesseract-path', '-t',
                      help='Path to tesseract executable (if not in PATH)')
    
    # === Email Processing Command ===
    email_parser = subparsers.add_parser('email', help='Send or receive emails')
    email_subparsers = email_parser.add_subparsers(dest='email_command', help='Email command')
    
    # Send invoice
    send_parser = email_subparsers.add_parser('send', help='Send invoice via email')
    send_parser.add_argument('--to', '-t', required=True,
                       help='Recipient email address(es), comma-separated')
    send_parser.add_argument('--subject', '-s', required=True,
                       help='Email subject')
    send_parser.add_argument('--invoice', '-i', required=True,
                       help='Path to invoice file to attach')
    send_parser.add_argument('--body', '-b',
                       help='Email body text (or path to text file)')
    send_parser.add_argument('--attachments', '-a',
                       help='Additional attachments, comma-separated')
    send_parser.add_argument('--cc',
                       help='CC email address(es), comma-separated')
    send_parser.add_argument('--bcc',
                       help='BCC email address(es), comma-separated')
    send_parser.add_argument('--env-file', '-e',
                       help='Path to .env file with email credentials')
    
    # Receive and process emails
    receive_parser = email_subparsers.add_parser('receive', help='Receive and process emails')
    receive_parser.add_argument('--folder', '-f', default='INBOX',
                          help='Email folder to process')
    receive_parser.add_argument('--criteria', '-c', default='UNSEEN',
                          help='Search criteria for emails')
    receive_parser.add_argument('--limit', '-l', type=int, default=10,
                          help='Maximum number of emails to process')
    receive_parser.add_argument('--days', '-d', type=int, default=30,
                          help='Process emails from the last X days')
    receive_parser.add_argument('--output-path', '-o',
                          help='Path to save extracted data')
    receive_parser.add_argument('--move-to', '-m',
                          help='Folder to move processed emails to')
    receive_parser.add_argument('--env-file', '-e',
                          help='Path to .env file with email credentials')
    
    # === Integrated Workflow Command ===
    integrated_parser = subparsers.add_parser('integrated', help='Run integrated workflow with OCR and email')
    integrated_parser.add_argument('--bank-statement', '-b', required=True,
                             help='Path to bank statement file (CSV/Excel)')
    integrated_parser.add_argument('--documents-dir', '-d',
                             help='Directory containing documents to process')
    integrated_parser.add_argument('--use-email', '-e', action='store_true',
                             help='Fetch and process emails')
    integrated_parser.add_argument('--email-criteria', '-ec', default='UNSEEN',
                             help='Search criteria for emails')
    integrated_parser.add_argument('--bank', '-bn',
                             help='Bank identifier (e.g., hdfc, sbi, icici, axis, yes_bank)')
    integrated_parser.add_argument('--output-dir', '-o', default='./reports',
                             help='Directory for saving reports')
    integrated_parser.add_argument('--report-format', '-rf',
                             choices=['excel', 'csv', 'html', 'json', 'all'],
                             default='all', help='Report format(s) to generate')
    integrated_parser.add_argument('--config', '-c',
                             help='Path to custom bank formats configuration file')
    integrated_parser.add_argument('--env-file',
                             help='Path to .env file with email credentials')
    integrated_parser.add_argument('--send-report', '-sr',
                             help='Email address(es) to send the report to')
    
    # Common options
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    
    return parser.parse_args()


def main():
    """Run the selected operation based on command line arguments."""
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    if not args.command:
        logger.error("No command specified. Use -h for help.")
        return 1
    
    try:
        # Load environment variables if env_file is provided
        if hasattr(args, 'env_file') and args.env_file:
            load_dotenv(args.env_file)
        
        # Execute the selected command
        if args.command == 'reconcile':
            return run_reconciliation(args, logger)
        elif args.command == 'ocr':
            return run_ocr_processing(args, logger)
        elif args.command == 'email':
            return run_email_command(args, logger)
        elif args.command == 'integrated':
            return run_integrated_workflow(args, logger)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
        
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=args.verbose)
        print(f"\nError: {e}")
        return 1


def run_reconciliation(args, logger):
    """Run the traditional reconciliation process."""
    logger.info("Starting traditional bank reconciliation")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize reconciler with specified parameters
    reconciler = BankReconciler(
        date_tolerance_days=args.date_tolerance,
        amount_tolerance_percentage=args.amount_tolerance,
        description_match_threshold=args.description_threshold,
        config_path=args.config,
        logger=logger
    )
    
    # Perform reconciliation
    logger.info("Running reconciliation process...")
    summary = reconciler.reconcile(
        bank_statement_path=args.bank_statement,
        internal_records_path=args.internal_records,
        bank=args.bank,
        sheet_name=args.sheet_name,
        internal_date_format=args.internal_date_format
    )
    
    # Generate reports
    report_generator = ReconciliationReportGenerator(
        output_dir=args.output_dir,
        logger=logger
    )
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = args.filename or f"reconciliation_{timestamp}"
    
    reports = {}
    
    if args.report_format in ['excel', 'all']:
        excel_path = os.path.join(args.output_dir, f"{filename_base}.xlsx")
        reports['excel'] = report_generator.generate_excel_report(
            reconciler=reconciler,
            output_path=excel_path
        )
        
    if args.report_format in ['csv', 'all']:
        csv_reports = report_generator.generate_csv_reports(
            reconciler=reconciler,
            base_filename=filename_base
        )
        reports['csv'] = csv_reports
        
    if args.report_format in ['html', 'all']:
        html_path = os.path.join(args.output_dir, f"{filename_base}.html")
        reports['html'] = report_generator.generate_html_report(
            reconciler=reconciler,
            output_path=html_path
        )
        
    if args.report_format in ['json', 'all']:
        json_path = os.path.join(args.output_dir, f"{filename_base}.json")
        reports['json'] = report_generator.generate_json_report(
            reconciler=reconciler,
            output_path=json_path
        )
    
    # Print summary to stdout
    print("\n==== Reconciliation Summary ====")
    print(f"Total Bank Transactions: {summary['total_bank_transactions']}")
    print(f"Matched Transactions: {summary['matched_count']}")
    print(f"Unmatched Bank Transactions: {summary['unmatched_bank_count']}")
    print(f"Unmatched Internal Records: {summary['unmatched_internal_count']}")
    print(f"Partial Matches: {summary['partial_matches_count']}")
    
    match_rate = (summary['matched_count'] / summary['total_bank_transactions']) * 100 if summary['total_bank_transactions'] > 0 else 0
    print(f"Match Rate: {match_rate:.2f}%")
    
    print("\n==== Generated Reports ====")
    for report_type, report_path in reports.items():
        if isinstance(report_path, dict):
            print(f"{report_type.upper()} Reports:")
            for sub_type, path in report_path.items():
                print(f"  - {sub_type}: {path}")
        else:
            print(f"{report_type.upper()}: {report_path}")
    
    logger.info("Reconciliation process completed successfully")
    return 0


def run_ocr_processing(args, logger):
    """Run OCR document processing."""
    logger.info(f"Starting OCR processing of documents in {args.documents_dir}")
    
    # Initialize OCR processor
    ocr_processor = OCRProcessor(
        tesseract_cmd=args.tesseract_path,
        logger=logger
    )
    
    # Determine output format from file extension
    output_format = 'dataframe'
    if args.output_path:
        ext = os.path.splitext(args.output_path)[1].lower()
        if ext == '.json':
            output_format = 'json'
        elif ext in ['.csv', '.xlsx', '.xls']:
            output_format = 'dataframe'
    
    # Process documents
    results = ocr_processor.batch_process_directory(
        args.documents_dir,
        output_format=output_format,
        recursive=args.recursive
    )
    
    # Save results if output path provided
    if args.output_path:
        output_dir = os.path.dirname(args.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        if output_format == 'dataframe':
            if args.output_path.endswith('.csv'):
                results.to_csv(args.output_path, index=False)
            else:
                results.to_excel(args.output_path, index=False)
        elif output_format == 'json':
            with open(args.output_path, 'w', encoding='utf-8') as f:
                f.write(results)
        
        logger.info(f"Saved OCR results to {args.output_path}")
    
    # Print summary
    if isinstance(results, pd.DataFrame):
        count = len(results)
    else:
        count = len(json.loads(results)) if output_format == 'json' else 0
        
    print(f"\n==== OCR Processing Results ====")
    print(f"Documents processed: {count}")
    print(f"Results saved to: {args.output_path if args.output_path else 'not saved'}")
    
    logger.info("OCR processing completed successfully")
    return 0


def run_email_command(args, logger):
    """Run email sending or receiving commands."""
    if not args.email_command:
        logger.error("No email command specified (send/receive)")
        return 1
    
    # Load email configuration from environment variables
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = os.getenv('SMTP_PORT')
    imap_server = os.getenv('IMAP_SERVER')
    imap_port = os.getenv('IMAP_PORT')
    username = os.getenv('EMAIL_USERNAME')
    password = os.getenv('EMAIL_PASSWORD')
    from_email = os.getenv('FROM_EMAIL')
    
    # Initialize email processor
    try:
        email_processor = EmailProcessor(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            imap_server=imap_server,
            imap_port=imap_port,
            username=username,
            password=password,
            from_email=from_email,
            env_file=args.env_file,
            logger=logger
        )
    except ValueError as e:
        logger.error(f"Email configuration error: {e}")
        print(f"\nError: Email configuration is incomplete. Please provide an .env file or set environment variables.")
        return 1
    
    # Execute the appropriate email command
    if args.email_command == 'send':
        return run_email_send(args, email_processor, logger)
    elif args.email_command == 'receive':
        return run_email_receive(args, email_processor, logger)
    else:
        logger.error(f"Unknown email command: {args.email_command}")
        return 1


def run_email_send(args, email_processor, logger):
    """Send an invoice via email."""
    logger.info(f"Sending invoice email to {args.to}")
    
    # Process email body
    body_text = args.body
    if body_text and os.path.isfile(body_text):
        with open(body_text, 'r', encoding='utf-8') as f:
            body_text = f.read()
    
    # Process attachments
    additional_attachments = []
    if args.attachments:
        additional_attachments = [a.strip() for a in args.attachments.split(',')]
    
    # Send the email
    success = email_processor.send_invoice(
        to_email=args.to.split(','),
        subject=args.subject,
        invoice_path=args.invoice,
        body_text=body_text,
        additional_attachments=additional_attachments,
        cc_emails=args.cc.split(',') if args.cc else None,
        bcc_emails=args.bcc.split(',') if args.bcc else None
    )
    
    if success:
        print("\n==== Email Result ====")
        print(f"Invoice email sent successfully to {args.to}")
        print(f"Subject: {args.subject}")
        print(f"Invoice file: {args.invoice}")
        logger.info("Email sent successfully")
        return 0
    else:
        print("\n==== Email Error ====")
        print("Failed to send invoice email. Check logs for details.")
        return 1


def run_email_receive(args, email_processor, logger):
    """Receive and process emails."""
    logger.info(f"Fetching emails from {args.folder} with criteria: {args.criteria}")
    
    # Create OCR processor for email attachment processing
    ocr_processor = OCRProcessor(logger=logger)
    email_processor.ocr_processor = ocr_processor
    
    # Fetch and process emails
    emails_data = email_processor.fetch_emails(
        folder=args.folder,
        search_criteria=args.criteria,
        limit=args.limit,
        since_days=args.days,
        process_attachments=True,
        move_processed=args.move_to
    )
    
    if not emails_data:
        print("\n==== Email Processing Results ====")
        print("No emails were found or processed.")
        return 0
    
    # Convert to reconciliation records
    records_df = email_processor.create_reconciliation_records_from_emails(
        emails_data,
        output_format='dataframe',
        save_to_file=args.output_path
    )
    
    # Print summary
    print("\n==== Email Processing Results ====")
    print(f"Emails processed: {len(emails_data)}")
    print(f"Financial records extracted: {len(records_df)}")
    
    if args.output_path:
        print(f"Results saved to: {args.output_path}")
    
    logger.info(f"Email processing completed. Processed {len(emails_data)} emails.")
    return 0


def run_integrated_workflow(args, logger):
    """Run integrated workflow with OCR and email processing."""
    logger.info("Starting integrated reconciliation workflow")
    
    # Load config
    config_path = args.config
    
    # Initialize OCR processor
    ocr_processor = OCRProcessor(logger=logger)
    
    # Initialize email processor if needed
    email_processor = None
    if args.use_email:
        # Load email configuration from environment variables
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = os.getenv('SMTP_PORT')
        imap_server = os.getenv('IMAP_SERVER')
        imap_port = os.getenv('IMAP_PORT')
        username = os.getenv('EMAIL_USERNAME')
        password = os.getenv('EMAIL_PASSWORD')
        from_email = os.getenv('FROM_EMAIL')
        
        try:
            email_processor = EmailProcessor(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                imap_server=imap_server,
                imap_port=imap_port,
                username=username,
                password=password,
                from_email=from_email,
                env_file=args.env_file,
                ocr_processor=ocr_processor,
                logger=logger
            )
        except ValueError as e:
            logger.error(f"Email configuration error: {e}")
            print(f"\nWarning: Email processing will be skipped due to incomplete configuration.")
    
    # Initialize reconciler
    reconciler = BankReconciler(
        config_path=config_path,
        logger=logger
    )
    
    # Initialize report generator
    report_generator = ReconciliationReportGenerator(
        output_dir=args.output_dir,
        logger=logger
    )
    
    # Initialize integrated system
    integrated_system = IntegratedReconciliationSystem(
        config_path=config_path,
        ocr_processor=ocr_processor,
        email_processor=email_processor,
        reconciler=reconciler,
        report_generator=report_generator,
        logger=logger
    )
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Run integrated workflow
    results = integrated_system.integrated_workflow(
        bank_statement_path=args.bank_statement,
        documents_dir=args.documents_dir,
        use_email=args.use_email,
        email_criteria=args.email_criteria,
        bank=args.bank,
        output_dir=args.output_dir,
        report_format=args.report_format
    )
    
    if not results or not results.get('success', False):
        print("\n==== Integrated Workflow Error ====")
        print(f"Workflow failed: {results.get('error', 'Unknown error')}")
        return 1
    
    # Print summary
    print("\n==== Integrated Workflow Results ====")
    print(f"Documents processed: {results['document_processing']['processed']}")
    print(f"Emails processed: {results['email_processing']['processed']}")
    
    if results.get('reconciliation'):
        summary = results['reconciliation']
        print("\n==== Reconciliation Summary ====")
        print(f"Total Bank Transactions: {summary['total_bank_transactions']}")
        print(f"Matched Transactions: {summary['matched_count']}")
        match_rate = (summary['matched_count'] / summary['total_bank_transactions']) * 100 if summary['total_bank_transactions'] > 0 else 0
        print(f"Match Rate: {match_rate:.2f}%")
    
    print("\n==== Generated Reports ====")
    for report_type, report_path in results.get('reports', {}).items():
        print(f"{report_type.upper()}: {report_path}")
    
    # Send report by email if requested
    if args.send_report and email_processor:
        # Find an appropriate report to send (prefer HTML, then Excel, then JSON)
        report_path = None
        for format_pref in ['html', 'excel', 'json']:
            if format_pref in results.get('reports', {}):
                report_path = results['reports'][format_pref]
                break
        
        if report_path:
            print(f"\nSending report to: {args.send_report}")
            success = integrated_system.send_reconciliation_report(
                recipients=args.send_report.split(','),
                report_path=report_path,
                include_summary=True
            )
            if success:
                print(f"Report email sent successfully")
            else:
                print(f"Failed to send report email")
    
    logger.info("Integrated workflow completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())