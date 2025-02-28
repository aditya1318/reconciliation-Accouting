"""
Indian Bank Reconciliation System

A comprehensive reconciliation system specifically designed for Indian bank statements,
featuring OCR document processing and email integration capabilities.
"""

from .reconciler import BankReconciler
from .parser import BankStatementParser
from .matcher import TransactionMatcher
from .report_generator import ReconciliationReportGenerator
from .ocr_processor import OCRProcessor
from .email_processor import EmailProcessor
from .integration import IntegratedReconciliationSystem

__all__ = [
    'BankReconciler',
    'BankStatementParser',
    'TransactionMatcher',
    'ReconciliationReportGenerator',
    'OCRProcessor',
    'EmailProcessor',
    'IntegratedReconciliationSystem'
]
"""
Bank Reconciliation System for Indian Bank Statements

A comprehensive system for reconciling bank statements with internal records,
specifically designed for Indian banking formats and transaction systems.
"""

__version__ = '0.1.0'