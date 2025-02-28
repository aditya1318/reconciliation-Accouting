"""
Command Line Interface for Indian Bank Reconciliation System.

This module provides a CLI interface to the bank reconciliation system,
allowing users to perform reconciliation operations from the command line.
"""

import argparse
import os
import sys
import logging
from datetime import datetime
from .parser import BankStatementParser
from .reconciler import BankReconciler
from .report_generator import ReconciliationReportGenerator


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
        description='Indian Bank Reconciliation System',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--bank-statement', '-b', required=True,
                        help='Path to bank statement file (CSV/Excel)')
    parser.add_argument('--internal-records', '-i', required=True,
                        help='Path to internal records file (CSV/Excel)')
    parser.add_argument('--bank', '-bn', 
                        help='Bank identifier (e.g., hdfc, sbi, icici, axis, yes_bank)')
    parser.add_argument('--sheet-name', '-s', default=0,
                        help='Sheet name or index for Excel files (default: 0)')
    parser.add_argument('--internal-date-format', '-df', 
                        help='Date format for internal records (e.g., %%d/%%m/%%Y)')
    
    # Matching parameters
    parser.add_argument('--date-tolerance', '-dt', type=int, default=3,
                        help='Maximum days difference for date matching')
    parser.add_argument('--amount-tolerance', '-at', type=float, default=0.01,
                        help='Maximum percentage difference for amount matching')
    parser.add_argument('--description-threshold', '-tm', type=int, default=80,
                        help='Threshold for fuzzy description matching (0-100)')
    
    # Report generation
    parser.add_argument('--output-dir', '-o', default='./reports',
                        help='Directory for saving reports')
    parser.add_argument('--report-format', '-rf', choices=['excel', 'csv', 'html', 'json', 'all'],
                        default='excel', help='Report format(s) to generate')
    parser.add_argument('--filename', '-f',
                        help='Base filename for reports (default: timestamp-based)')
    
    # Other options
    parser.add_argument('--config', '-c', 
                        help='Path to custom bank formats configuration file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    
    return parser.parse_args()


def main():
    """Run the reconciliation process based on command line arguments."""
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    try:
        logger.info("Starting Indian Bank Reconciliation System")
        
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
        
    except Exception as e:
        logger.error(f"Error during reconciliation: {e}", exc_info=args.verbose)
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())