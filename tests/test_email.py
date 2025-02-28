"""
Tests for the email processor and integration with the reconciliation system.

Note: These tests focus on the internal logic rather than actual email sending/receiving,
which would require mock servers or real credentials.
"""

import os
import unittest
import tempfile
import pandas as pd
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime

from bank_recon.email_processor import EmailProcessor
from bank_recon.ocr_processor import OCRProcessor


class TestEmailProcessor(unittest.TestCase):
    """Test case for the email processor functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock OCR processor
        self.mock_ocr = MagicMock(spec=OCRProcessor)
        self.mock_ocr.process_bytes.return_value = {
            'invoice_number': 'TEST-2025-001',
            'invoice_date': '2025-05-20',
            'total_amount': 2360.00,
            'vendor_name': 'Test Vendor Ltd.',
            'customer_name': 'Test Customer'
        }
        
        # Create EmailProcessor with mock components
        with patch.dict('os.environ', {
            'SMTP_SERVER': 'smtp.example.com',
            'SMTP_PORT': '587',
            'IMAP_SERVER': 'imap.example.com',
            'IMAP_PORT': '993',
            'EMAIL_USERNAME': 'test@example.com',
            'EMAIL_PASSWORD': 'password',
            'FROM_EMAIL': 'test@example.com'
        }):
            self.email_processor = EmailProcessor(ocr_processor=self.mock_ocr)
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a simple invoice text file for testing
        self.invoice_text = "This is a test invoice"
        self.invoice_path = os.path.join(self.temp_dir, 'test_invoice.txt')
        with open(self.invoice_path, 'w') as f:
            f.write(self.invoice_text)
    
    def tearDown(self):
        """Clean up after test."""
        # Remove temporary directory and its contents
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('smtplib.SMTP')
    def test_send_invoice(self, mock_smtp):
        """Test sending an invoice email."""
        # Configure mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Call the method
        result = self.email_processor.send_invoice(
            to_email='recipient@example.com',
            subject='Test Invoice',
            invoice_path=self.invoice_path,
            body_text='Please find attached invoice.'
        )
        
        # Check the result
        self.assertTrue(result)
        
        # Verify SMTP was called correctly
        mock_smtp.assert_called_once_with('smtp.example.com', 587)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with('test@example.com', 'password')
        mock_smtp_instance.sendmail.assert_called_once()
        
        # Check sendmail arguments
        args = mock_smtp_instance.sendmail.call_args[0]
        self.assertEqual(args[0], 'test@example.com')
        self.assertEqual(args[1], 'recipient@example.com')
        self.assertIn('Subject: Test Invoice', args[2])
    
    @patch('imaplib.IMAP4_SSL')
    def test_fetch_emails(self, mock_imap):
        """Test fetching emails."""
        # Configure mock
        mock_imap_instance = MagicMock()
        mock_imap.return_value = mock_imap_instance
        
        # Mock the search response
        mock_imap_instance.search.return_value = ('OK', [b'1 2 3'])
        
        # Mock the fetch response for a single email
        email_data = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Invoice
Content-Type: multipart/mixed; boundary="boundary"

--boundary
Content-Type: text/plain

Test email body
--boundary
Content-Type: application/pdf
Content-Disposition: attachment; filename="invoice.pdf"

PDF content here
--boundary--
"""
        mock_imap_instance.fetch.return_value = ('OK', [(b'1', (b'RFC822', email_data))])
        
        # Call the method
        emails = self.email_processor.fetch_emails(
            folder='INBOX',
            search_criteria='UNSEEN',
            limit=10,
            process_attachments=True
        )
        
        # Check the result
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]['subject'], 'Test Invoice')
        self.assertEqual(emails[0]['from_email'], 'sender@example.com')
        self.assertIn('attachments', emails[0])
        
        # Check that OCR processor was called for PDF attachment
        if emails[0]['attachments']:
            self.mock_ocr.process_bytes.assert_called()
    
    def test_validate_emails(self):
        """Test email validation."""
        # Valid emails
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.in',
            'user-name@example.org'
        ]
        
        # Invalid emails
        invalid_emails = [
            'not_an_email',
            'missing@domain',
            '@missing.user',
            'spaces in@email.com'
        ]
        
        # Test with a mix of valid and invalid
        mixed_emails = valid_emails + invalid_emails
        result = self.email_processor._validate_emails(mixed_emails)
        
        # Should only return the valid ones
        self.assertEqual(len(result), len(valid_emails))
        for email in valid_emails:
            self.assertIn(email, result)
    
    def test_create_reconciliation_records(self):
        """Test creating reconciliation records from email data."""
        # Create sample email data
        emails_data = [{
            'message_id': '<test123@example.com>',
            'date': '2025-05-20',
            'from_email': 'vendor@example.com',
            'subject': 'Invoice TEST-2025-001',
            'processed_attachments': [{
                'filename': 'invoice.pdf',
                'ocr_processed': True,
                'ocr_data': {
                    'invoice_number': 'TEST-2025-001',
                    'invoice_date': '2025-05-20',
                    'total_amount': 2360.00,
                    'vendor_name': 'Test Vendor Ltd.'
                }
            }]
        }]
        
        # Call the method
        records = self.email_processor.create_reconciliation_records_from_emails(
            emails_data,
            output_format='dataframe'
        )
        
        # Check the result
        self.assertIsInstance(records, pd.DataFrame)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.iloc[0]['amount'], 2360.00)
        self.assertEqual(records.iloc[0]['reference'], 'TEST-2025-001')
        self.assertEqual(records.iloc[0]['source_email'], 'vendor@example.com')
        
        # Check that the transaction_id was created
        self.assertTrue('transaction_id' in records.columns)
        self.assertTrue('EMAIL_' in records.iloc[0]['transaction_id'])


class TestEmailIntegration(unittest.TestCase):
    """Test integration of email processing with OCR and reconciliation."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock OCR processor for email attachment processing
        self.mock_ocr = MagicMock(spec=OCRProcessor)
        self.mock_ocr.process_bytes.return_value = {
            'invoice_number': 'TEST-2025-001',
            'invoice_date': '2025-05-20',
            'total_amount': 2360.00,
            'vendor_name': 'Test Vendor Ltd.'
        }
        
        # Create EmailProcessor with mock components
        with patch.dict('os.environ', {
            'SMTP_SERVER': 'smtp.example.com',
            'SMTP_PORT': '587',
            'IMAP_SERVER': 'imap.example.com',
            'IMAP_PORT': '993',
            'EMAIL_USERNAME': 'test@example.com',
            'EMAIL_PASSWORD': 'password',
            'FROM_EMAIL': 'test@example.com'
        }):
            self.email_processor = EmailProcessor(ocr_processor=self.mock_ocr)
    
    def tearDown(self):
        """Clean up after test."""
        # Remove temporary directory and its contents
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('imaplib.IMAP4_SSL')
    def test_email_to_reconciliation_workflow(self, mock_imap):
        """Test workflow from email fetching to reconciliation records."""
        # Configure mock
        mock_imap_instance = MagicMock()
        mock_imap.return_value = mock_imap_instance
        
        # Mock the search response
        mock_imap_instance.search.return_value = ('OK', [b'1'])
        
        # Create a PDF-like content for testing
        pdf_content = b'%PDF-1.5\nTest PDF content'
        
        # Mock the fetch response with a PDF attachment
        email_data = f"""From: vendor@example.com
To: accounting@mycompany.com
Subject: Invoice TEST-2025-001
Content-Type: multipart/mixed; boundary="boundary"

--boundary
Content-Type: text/plain

Please find attached invoice TEST-2025-001 for payment.
--boundary
Content-Type: application/pdf
Content-Disposition: attachment; filename="invoice.pdf"

{pdf_content.decode('latin1')}
--boundary--
""".encode('latin1')

        mock_imap_instance.fetch.return_value = ('OK', [(b'1', (b'RFC822', email_data))])
        
        # Run the email processing workflow
        emails = self.email_processor.fetch_emails(
            folder='INBOX',
            search_criteria='UNSEEN',
            limit=10,
            process_attachments=True
        )
        
        # Convert to reconciliation records
        records = self.email_processor.create_reconciliation_records_from_emails(
            emails,
            output_format='dataframe',
            save_to_file=os.path.join(self.temp_dir, 'email_records.xlsx')
        )
        
        # Verify the workflow
        self.assertEqual(len(emails), 1)
        self.assertEqual(len(records), 1)
        
        # Check reconciliation record fields
        self.assertEqual(records.iloc[0]['reference'], 'TEST-2025-001')
        self.assertEqual(records.iloc[0]['amount'], 2360.00)
        self.assertEqual(records.iloc[0]['source_email'], 'vendor@example.com')
        
        # Check that the output file was created
        output_file = os.path.join(self.temp_dir, 'email_records.xlsx')
        self.assertTrue(os.path.exists(output_file))


if __name__ == '__main__':
    unittest.main()