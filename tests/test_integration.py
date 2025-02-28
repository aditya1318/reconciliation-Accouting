"""
Tests for the integrated OCR, Email, and Reconciliation functionality.
"""

import os
import unittest
import tempfile
import pandas as pd
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime

from bank_recon.ocr_processor import OCRProcessor
from bank_recon.email_processor import EmailProcessor
from bank_recon.reconciler import BankReconciler
from bank_recon.report_generator import ReconciliationReportGenerator
from bank_recon.integration import IntegratedReconciliationSystem


class TestIntegration(unittest.TestCase):
    """Test case for the integrated reconciliation system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files directory
        self.test_files_dir = os.path.join(self.temp_dir, 'test_files')
        os.makedirs(self.test_files_dir, exist_ok=True)
        
        # Create sample bank statement
        self.bank_data = pd.DataFrame({
            'date': [pd.Timestamp('2025-05-20'), pd.Timestamp('2025-05-28')],
            'narration': ['PAYMENT TO TEST VENDOR REF TEST123456789', 'PAYMENT FROM ABC VENDORS INVOICE #ABC-2024-28'],
            'debit': [2360.00, 0.00],
            'credit': [0.00, 8850.00],
            'balance': [7640.00, 16490.00]
        })
        
        self.bank_path = os.path.join(self.temp_dir, 'bank_statement.xlsx')
        self.bank_data.to_excel(self.bank_path, index=False)
        
        # Create sample invoice text files
        self.create_sample_invoices()
        
        # Initialize mock OCR processor
        self.mock_ocr = MagicMock(spec=OCRProcessor)
        self.mock_ocr.batch_process_directory.return_value = pd.DataFrame([
            {
                'transaction_id': 'OCR_TEST2025001',
                'invoice_number': 'TEST-2025-001',
                'invoice_date': pd.Timestamp('2025-05-20'),
                'total_amount': 2360.00,
                'vendor_name': 'Test Vendor Ltd.',
                'date': pd.Timestamp('2025-05-20'),
                'description': 'Invoice: TEST-2025-001 | Vendor: Test Vendor Ltd.',
                'reference': 'TEST123456789',
                'amount': 2360.00,
                'file_path': os.path.join(self.test_files_dir, 'invoice1.txt')
            },
            {
                'transaction_id': 'OCR_ABC202428',
                'invoice_number': 'ABC-2024-28',
                'invoice_date': pd.Timestamp('2025-05-28'),
                'total_amount': 8850.00,
                'vendor_name': 'ABC Vendors',
                'date': pd.Timestamp('2025-05-28'),
                'description': 'Invoice: ABC-2024-28 | Vendor: ABC Vendors',
                'reference': 'ABC-2024-28',
                'amount': 8850.00,
                'file_path': os.path.join(self.test_files_dir, 'invoice2.txt')
            }
        ])
        
        # Initialize mock email processor
        self.mock_email = MagicMock(spec=EmailProcessor)
        self.mock_email.fetch_emails.return_value = [
            {
                'message_id': '<test123@example.com>',
                'from_email': 'vendor@example.com',
                'subject': 'Invoice ABC-2024-28',
                'processed_attachments': [
                    {
                        'filename': 'invoice.pdf',
                        'ocr_processed': True,
                        'ocr_data': {
                            'invoice_number': 'ABC-2024-28',
                            'invoice_date': '2025-05-28',
                            'total_amount': 8850.00,
                            'vendor_name': 'ABC Vendors'
                        }
                    }
                ]
            }
        ]
        
        self.mock_email.create_reconciliation_records_from_emails.return_value = pd.DataFrame([
            {
                'transaction_id': 'EMAIL_test123',
                'date': pd.Timestamp('2025-05-28'),
                'description': 'Invoice from ABC Vendors - invoice.pdf',
                'reference': 'ABC-2024-28',
                'amount': 8850.00,
                'source_email': 'vendor@example.com'
            }
        ])
        
        # Initialize components
        self.reconciler = BankReconciler()
        self.report_generator = ReconciliationReportGenerator(output_dir=self.temp_dir)
        
        # Initialize the integrated system
        self.integrated_system = IntegratedReconciliationSystem(
            ocr_processor=self.mock_ocr,
            email_processor=self.mock_email,
            reconciler=self.reconciler,
            report_generator=self.report_generator
        )
    
    def tearDown(self):
        """Clean up after test."""
        # Remove temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def create_sample_invoices(self):
        """Create sample invoice files for testing."""
        # Invoice 1
        invoice1 = """
INVOICE

Invoice Number: TEST-2025-001
Date: 20/05/2025
Total: Rs. 2,360.00
Vendor: Test Vendor Ltd.
Reference: TEST123456789
        """
        
        with open(os.path.join(self.test_files_dir, 'invoice1.txt'), 'w') as f:
            f.write(invoice1)
        
        # Invoice 2
        invoice2 = """
INVOICE

Invoice Number: ABC-2024-28
Date: 28/05/2025
Total: Rs. 8,850.00
Vendor: ABC Vendors
Reference: ABC-2024-28
        """
        
        with open(os.path.join(self.test_files_dir, 'invoice2.txt'), 'w') as f:
            f.write(invoice2)
    
    def test_process_documents_directory(self):
        """Test processing documents directory."""
        # Call the method
        result = self.integrated_system.process_documents_directory(
            documents_dir=self.test_files_dir,
            output_path=os.path.join(self.temp_dir, 'ocr_results.xlsx')
        )
        
        # Check the result
        self.assertEqual(len(result), 2)
        
        # Verify mock was called correctly
        self.mock_ocr.batch_process_directory.assert_called_once_with(
            self.test_files_dir, output_format='dataframe', recursive=False
        )
    
    def test_process_emails_for_reconciliation(self):
        """Test processing emails for reconciliation."""
        # Call the method
        result = self.integrated_system.process_emails_for_reconciliation(
            email_search_criteria='UNSEEN',
            email_folder='INBOX',
            limit=10,
            output_path=os.path.join(self.temp_dir, 'email_results.xlsx')
        )
        
        # Check the result
        self.assertEqual(len(result), 1)
        
        # Verify mocks were called correctly
        self.mock_email.fetch_emails.assert_called_once()
        self.mock_email.create_reconciliation_records_from_emails.assert_called_once()
    
    def test_reconcile_with_ocr_data(self):
        """Test reconciliation with OCR data."""
        # Prepare OCR data
        ocr_data = pd.DataFrame([
            {
                'transaction_id': 'OCR_TEST2025001',
                'date': pd.Timestamp('2025-05-20'),
                'description': 'Invoice: TEST-2025-001 | Vendor: Test Vendor Ltd.',
                'reference': 'TEST123456789',
                'amount': 2360.00
            },
            {
                'transaction_id': 'OCR_ABC202428',
                'date': pd.Timestamp('2025-05-28'),
                'description': 'Invoice: ABC-2024-28 | Vendor: ABC Vendors',
                'reference': 'ABC-2024-28',
                'amount': 8850.00
            }
        ])
        
        # Call the method
        result = self.integrated_system.reconcile_with_ocr_data(
            bank_statement_path=self.bank_path,
            ocr_data=ocr_data,
            output_dir=self.temp_dir,
            report_format='all'
        )
        
        # Check the result
        self.assertIsNotNone(result)
        self.assertEqual(result['total_bank_transactions'], 2)
        self.assertGreaterEqual(result['matched_count'], 1)  # At least one match
        
        # Check that reports were generated
        self.assertTrue(any(f.endswith('.xlsx') for f in os.listdir(self.temp_dir)))
        self.assertTrue(any(f.endswith('.html') for f in os.listdir(self.temp_dir)))
    
    def test_integrated_workflow(self):
        """Test the fully integrated workflow."""
        # Call the method
        result = self.integrated_system.integrated_workflow(
            bank_statement_path=self.bank_path,
            documents_dir=self.test_files_dir,
            use_email=True,
            email_criteria='UNSEEN',
            output_dir=self.temp_dir,
            report_format='all'
        )
        
        # Check the result
        self.assertTrue(result['success'])
        self.assertEqual(result['document_processing']['processed'], 2)
        self.assertEqual(result['email_processing']['processed'], 1)
        self.assertIsNotNone(result['reconciliation'])
        self.assertGreaterEqual(result['reconciliation']['matched_count'], 1)
        
        # Verify that the workflow called the expected methods
        self.mock_ocr.batch_process_directory.assert_called_once()
        self.mock_email.fetch_emails.assert_called_once()
        
        # Check that reports were generated
        self.assertIn('reports', result)
        self.assertTrue(len(result['reports']) >= 1)


if __name__ == '__main__':
    unittest.main()