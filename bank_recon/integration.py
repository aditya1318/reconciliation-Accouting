"""
Integration module for combining OCR, Email, and Reconciliation functionality.

This module provides integration between the OCR processor, email processor, 
and reconciliation engine, allowing for an automated workflow from document 
extraction to reconciliation.
"""

import os
import logging
import pandas as pd
from datetime import datetime
import json
import tempfile
import shutil

from .ocr_processor import OCRProcessor
from .email_processor import EmailProcessor
from .reconciler import BankReconciler
from .report_generator import ReconciliationReportGenerator


class IntegratedReconciliationSystem:
    """
    Integrated system combining OCR, email, and reconciliation capabilities.
    Provides automated workflows for bank reconciliation with document processing.
    """
    
    def __init__(self, 
                 config_path=None,
                 ocr_processor=None,
                 email_processor=None,
                 reconciler=None,
                 report_generator=None,
                 logger=None):
        """
        Initialize the integrated reconciliation system.
        
        Args:
            config_path (str, optional): Path to the bank formats configuration file.
            ocr_processor (OCRProcessor, optional): OCR processor instance.
            email_processor (EmailProcessor, optional): Email processor instance.
            reconciler (BankReconciler, optional): Reconciler instance.
            report_generator (ReconciliationReportGenerator, optional): Report generator instance.
            logger (logging.Logger, optional): Logger for recording process.
        """
        # Setup logger
        if logger is None:
            self.logger = logging.getLogger('integrated_recon')
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger
        
        # Initialize components
        self.ocr_processor = ocr_processor or OCRProcessor(logger=self.logger)
        self.email_processor = email_processor
        self.reconciler = reconciler or BankReconciler(config_path=config_path, logger=self.logger)
        self.report_generator = report_generator or ReconciliationReportGenerator(logger=self.logger)
        
        # Temporary directory for storing processed files
        self.temp_dir = None
        
    def process_documents_directory(self, 
                                    documents_dir, 
                                    output_path=None,
                                    recursive=False):
        """
        Process all documents in a directory using OCR and create a dataset
        suitable for reconciliation.
        
        Args:
            documents_dir (str): Path to directory containing documents.
            output_path (str, optional): Path to save extracted data.
            recursive (bool, optional): Whether to search subdirectories.
            
        Returns:
            pandas.DataFrame: Extracted financial data ready for reconciliation.
        """
        self.logger.info(f"Processing documents in directory: {documents_dir}")
        
        # Process documents
        results = self.ocr_processor.batch_process_directory(
            documents_dir, 
            output_format='dataframe',
            recursive=recursive
        )
        
        if results.empty:
            self.logger.warning("No documents were successfully processed")
            return pd.DataFrame()
        
        self.logger.info(f"Successfully processed {len(results)} documents")
        
        # Save results if requested
        if output_path:
            if output_path.endswith('.csv'):
                results.to_csv(output_path, index=False)
            elif output_path.endswith('.xlsx'):
                results.to_excel(output_path, index=False)
            elif output_path.endswith('.json'):
                results.to_json(output_path, orient='records', date_format='iso')
            self.logger.info(f"Saved extracted data to {output_path}")
        
        return results
    
    def process_emails_for_reconciliation(self,
                                         email_search_criteria='UNSEEN',
                                         email_folder='INBOX',
                                         limit=50,
                                         since_days=30,
                                         move_processed=None,
                                         output_path=None):
        """
        Fetch emails, process attachments, and create a dataset for reconciliation.
        
        Args:
            email_search_criteria (str): IMAP search criteria for emails.
            email_folder (str): Email folder to search in.
            limit (int): Maximum number of emails to process.
            since_days (int): Process emails from the last X days.
            move_processed (str, optional): Folder to move processed emails to.
            output_path (str, optional): Path to save extracted data.
            
        Returns:
            pandas.DataFrame: Extracted financial data ready for reconciliation.
        """
        if not self.email_processor:
            self.logger.error("Email processor not configured")
            return pd.DataFrame()
        
        self.logger.info(f"Fetching emails from {email_folder} with criteria: {email_search_criteria}")
        
        # Fetch and process emails
        emails_data = self.email_processor.fetch_emails(
            folder=email_folder,
            search_criteria=email_search_criteria,
            limit=limit,
            since_days=since_days,
            process_attachments=True,
            move_processed=move_processed
        )
        
        if not emails_data:
            self.logger.warning("No emails were found or processed")
            return pd.DataFrame()
        
        self.logger.info(f"Processed {len(emails_data)} emails")
        
        # Convert to reconciliation records
        records_df = self.email_processor.create_reconciliation_records_from_emails(
            emails_data,
            output_format='dataframe',
            save_to_file=output_path
        )
        
        self.logger.info(f"Created {len(records_df)} reconciliation records from emails")
        return records_df
    
    def reconcile_with_ocr_data(self,
                               bank_statement_path,
                               ocr_data,
                               bank=None,
                               sheet_name=0,
                               output_dir='./reports',
                               report_format='all'):
        """
        Reconcile bank statement with data extracted via OCR.
        
        Args:
            bank_statement_path (str): Path to bank statement file.
            ocr_data (pandas.DataFrame): OCR-extracted data for reconciliation.
            bank (str, optional): Bank identifier.
            sheet_name (int or str, optional): Sheet name for Excel files.
            output_dir (str): Directory for reports.
            report_format (str): Report format ('excel', 'csv', 'html', 'json', 'all').
            
        Returns:
            dict: Reconciliation summary.
        """
        if ocr_data.empty:
            self.logger.error("No OCR data provided for reconciliation")
            return None
        
        self.logger.info(f"Starting reconciliation with OCR data against {bank_statement_path}")
        
        # Create a temporary file with the OCR data
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_path = temp_file.name
            ocr_data.to_excel(temp_path, index=False)
        
        try:
            # Perform reconciliation
            summary = self.reconciler.reconcile(
                bank_statement_path=bank_statement_path,
                internal_records_path=temp_path,
                bank=bank,
                sheet_name=sheet_name
            )
            
            self.logger.info(f"Reconciliation completed with match rate: {summary['match_rate']*100:.2f}%")
            
            # Create directory for reports
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate reports
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_base = f"ocr_reconciliation_{timestamp}"
            
            if report_format in ['excel', 'all']:
                excel_path = os.path.join(output_dir, f"{filename_base}.xlsx")
                self.report_generator.generate_excel_report(
                    reconciler=self.reconciler,
                    output_path=excel_path
                )
                self.logger.info(f"Excel report generated: {excel_path}")
            
            if report_format in ['csv', 'all']:
                csv_reports = self.report_generator.generate_csv_reports(
                    reconciler=self.reconciler,
                    base_filename=filename_base
                )
                self.logger.info(f"CSV reports generated in: {output_dir}")
            
            if report_format in ['html', 'all']:
                html_path = os.path.join(output_dir, f"{filename_base}.html")
                self.report_generator.generate_html_report(
                    reconciler=self.reconciler,
                    output_path=html_path
                )
                self.logger.info(f"HTML report generated: {html_path}")
            
            if report_format in ['json', 'all']:
                json_path = os.path.join(output_dir, f"{filename_base}.json")
                self.report_generator.generate_json_report(
                    reconciler=self.reconciler,
                    output_path=json_path
                )
                self.logger.info(f"JSON report generated: {json_path}")
            
            return summary
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def integrated_workflow(self,
                           bank_statement_path,
                           documents_dir=None,
                           use_email=False,
                           email_criteria='UNSEEN',
                           bank=None,
                           output_dir='./reports',
                           report_format='all'):
        """
        Run an integrated workflow combining document processing, 
        email fetching, and reconciliation.
        
        Args:
            bank_statement_path (str): Path to bank statement file.
            documents_dir (str, optional): Directory containing financial documents.
            use_email (bool): Whether to fetch and process emails.
            email_criteria (str): Email search criteria for fetching.
            bank (str, optional): Bank identifier.
            output_dir (str): Directory for reports.
            report_format (str): Report format.
            
        Returns:
            dict: Workflow results summary.
        """
        results = {
            'success': False,
            'document_processing': {'processed': 0, 'success': 0},
            'email_processing': {'processed': 0, 'success': 0},
            'reconciliation': None,
            'reports': {}
        }
        
        try:
            # Create temp directory for intermediate files
            self.temp_dir = tempfile.mkdtemp()
            
            all_records = []
            
            # Process documents if directory provided
            if documents_dir:
                self.logger.info(f"Processing documents from {documents_dir}")
                doc_records = self.process_documents_directory(
                    documents_dir=documents_dir,
                    output_path=os.path.join(self.temp_dir, 'ocr_data.xlsx'),
                    recursive=True
                )
                
                results['document_processing'] = {
                    'processed': len(doc_records),
                    'success': len(doc_records[~doc_records['transaction_id'].isna()]) if not doc_records.empty else 0
                }
                
                if not doc_records.empty:
                    all_records.append(doc_records)
            
            # Process emails if requested
            if use_email and self.email_processor:
                self.logger.info(f"Processing emails with criteria: {email_criteria}")
                email_records = self.process_emails_for_reconciliation(
                    email_search_criteria=email_criteria,
                    output_path=os.path.join(self.temp_dir, 'email_data.xlsx')
                )
                
                results['email_processing'] = {
                    'processed': len(email_records),
                    'success': len(email_records[~email_records['transaction_id'].isna()]) if not email_records.empty else 0
                }
                
                if not email_records.empty:
                    all_records.append(email_records)
            
            # Combine all records
            if all_records:
                combined_records = pd.concat(all_records, ignore_index=True)
                
                # Perform reconciliation
                self.logger.info("Starting reconciliation with combined data")
                summary = self.reconcile_with_ocr_data(
                    bank_statement_path=bank_statement_path,
                    ocr_data=combined_records,
                    bank=bank,
                    output_dir=output_dir,
                    report_format=report_format
                )
                
                results['reconciliation'] = summary
                # Make sure to set success to True only if reconciliation was successful
                results['success'] = summary is not None
                
                # Store report file paths
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename_base = f"integrated_reconciliation_{timestamp}"
                
                if report_format in ['excel', 'all']:
                    results['reports']['excel'] = os.path.join(output_dir, f"{filename_base}.xlsx")
                
                if report_format in ['html', 'all']:
                    results['reports']['html'] = os.path.join(output_dir, f"{filename_base}.html")
                
                if report_format in ['json', 'all']:
                    results['reports']['json'] = os.path.join(output_dir, f"{filename_base}.json")
                
                if report_format in ['csv', 'all']:
                    results['reports']['csv'] = os.path.join(output_dir, f"{filename_base}_matched.csv")
            else:
                self.logger.warning("No records were extracted from documents or emails")
                results['success'] = False
                
            return results
            
        except Exception as e:
            self.logger.error(f"Error in integrated workflow: {e}")
            results['error'] = str(e)
            return results
            
        finally:
            # Clean up temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                except:
                    self.logger.warning(f"Could not delete temporary directory: {self.temp_dir}")
    
    def send_reconciliation_report(self,
                                  recipients,
                                  report_path,
                                  subject=None,
                                  body_text=None,
                                  include_summary=True):
        """
        Send reconciliation report via email.
        
        Args:
            recipients (str or list): Email recipient(s).
            report_path (str): Path to the reconciliation report file.
            subject (str, optional): Email subject.
            body_text (str, optional): Email body text.
            include_summary (bool): Whether to include reconciliation summary in the email.
            
        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        if not self.email_processor:
            self.logger.error("Email processor not configured")
            return False
        
        if not os.path.exists(report_path):
            self.logger.error(f"Report file not found: {report_path}")
            return False
        
        # Create default subject if not provided
        if subject is None:
            filename = os.path.basename(report_path)
            subject = f"Bank Reconciliation Report: {filename}"
        
        # Create default body text if not provided
        if body_text is None:
            body_text = f"""
            Dear Sir/Madam,
            
            Please find attached the bank reconciliation report for your reference.
            
            Date: {datetime.now().strftime('%Y-%m-%d')}
            """
            
        # Add summary information if requested
        if include_summary and hasattr(self.reconciler, 'get_reconciliation_summary'):
            try:
                summary = self.reconciler.get_reconciliation_summary()
                stats = summary.get('statistics', {})
                
                if stats:
                    summary_text = "\n\nSummary of Reconciliation:\n"
                    summary_text += f"- Total Bank Transactions: {stats.get('total_bank_transactions', 'N/A')}\n"
                    summary_text += f"- Matched Transactions: {stats.get('matched_count', 'N/A')}\n"
                    match_rate = stats.get('matched_count', 0) / stats.get('total_bank_transactions', 1) * 100 if stats.get('total_bank_transactions', 0) > 0 else 0
                    summary_text += f"- Match Rate: {match_rate:.2f}%\n"
                    summary_text += f"- Unmatched Bank Transactions: {stats.get('unmatched_bank_count', 'N/A')}\n"
                    summary_text += f"- Unmatched Internal Records: {stats.get('unmatched_internal_count', 'N/A')}\n"
                    
                    body_text += summary_text
            except Exception as e:
                self.logger.warning(f"Could not include reconciliation summary: {e}")
        
        # Send the email
        result = self.email_processor.send_invoice(
            to_email=recipients,
            subject=subject,
            invoice_path=report_path,  # Using the report as attachment
            body_text=body_text
        )
        
        if result:
            self.logger.info(f"Reconciliation report emailed to {recipients}")
        else:
            self.logger.error(f"Failed to send reconciliation report email")
            
        return result