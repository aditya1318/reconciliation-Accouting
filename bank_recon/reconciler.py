"""
Bank Reconciliation Engine for Indian bank statements.

This module serves as the main entry point for the reconciliation process,
coordinating the parsing, matching, and reporting components.
"""

import os
import pandas as pd
from datetime import datetime
import logging
from .parser import BankStatementParser
from .matcher import TransactionMatcher


class BankReconciler:
    """
    Main reconciliation engine for matching bank transactions with internal records.
    
    This class orchestrates the entire reconciliation process including:
    1. Loading and parsing bank statements
    2. Matching transactions with internal records
    3. Generating reconciliation reports
    """
    
    def __init__(self, 
                 date_tolerance_days=3,
                 amount_tolerance_percentage=0.01,
                 description_match_threshold=80,
                 match_criteria=None,
                 config_path=None,
                 logger=None):
        """
        Initialize the bank reconciler with the specified parameters.
        
        Args:
            date_tolerance_days (int): Maximum days difference for date matching.
            amount_tolerance_percentage (float): Maximum percentage difference for amount matching.
            description_match_threshold (int): Threshold for fuzzy description matching (0-100).
            match_criteria (dict, optional): Criteria weights for matching algorithm.
                Default is {'amount': 0.5, 'date': 0.3, 'description': 0.2}
            config_path (str, optional): Path to the bank formats configuration file.
            logger (logging.Logger, optional): Logger for recording reconciliation process.
        """
        self.date_tolerance_days = date_tolerance_days
        self.amount_tolerance_percentage = amount_tolerance_percentage
        self.description_match_threshold = description_match_threshold
        
        if match_criteria is None:
            self.match_criteria = {'amount': 0.5, 'date': 0.3, 'description': 0.2}
        else:
            self.match_criteria = match_criteria
            
        # Setup logger
        if logger is None:
            self.logger = logging.getLogger('bank_reconciliation')
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger
            
        # Initialize parser and matcher
        self.parser = BankStatementParser(config_path=config_path)
        self.matcher = TransactionMatcher(
            date_tolerance_days=date_tolerance_days,
            amount_tolerance_percentage=amount_tolerance_percentage,
            description_match_threshold=description_match_threshold
        )
        
        # Store reconciliation results
        self.matched_transactions = None
        self.unmatched_bank_transactions = None
        self.unmatched_internal_transactions = None
        self.partial_matches = None
        self.match_suggestions = None
        
    def reconcile(self, bank_statement_path, internal_records_path, 
                 bank=None, sheet_name=0, internal_date_format=None):
        """
        Perform reconciliation between bank statement and internal records.
        
        Args:
            bank_statement_path (str): Path to bank statement file (CSV/Excel).
            internal_records_path (str): Path to internal records file (CSV/Excel).
            bank (str, optional): Bank identifier for specific parsing rules.
            sheet_name (int or str, optional): Sheet name/index for Excel files.
            internal_date_format (str, optional): Date format for internal records.
            
        Returns:
            dict: Reconciliation results summary.
        """
        start_time = datetime.now()
        self.logger.info(f"Starting reconciliation process at {start_time}")
        
        # Parse bank statement
        self.logger.info(f"Parsing bank statement from {bank_statement_path}")
        bank_df = self.parser.parse(bank_statement_path, bank=bank, sheet_name=sheet_name)
        self.logger.info(f"Parsed {len(bank_df)} bank transactions")
        
        # Parse internal records
        self.logger.info(f"Loading internal records from {internal_records_path}")
        internal_df = self._load_internal_records(internal_records_path, sheet_name, internal_date_format)
        self.logger.info(f"Loaded {len(internal_df)} internal records")
        
        # Match transactions
        self.logger.info("Matching transactions...")
        results = self.matcher.match_transactions(bank_df, internal_df, self.match_criteria)
        self.matched_transactions, self.unmatched_bank_transactions, \
        self.unmatched_internal_transactions, self.partial_matches = results
        
        # Generate match suggestions for unmatched transactions
        if not self.unmatched_bank_transactions.empty:
            self.logger.info("Generating match suggestions for unmatched transactions...")
            self.match_suggestions = self.matcher.suggest_matches(
                self.unmatched_bank_transactions, 
                self.unmatched_internal_transactions
            )
        
        # Calculate summary statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        summary = {
            'total_bank_transactions': len(bank_df),
            'total_internal_records': len(internal_df),
            'matched_count': len(self.matched_transactions),
            'unmatched_bank_count': len(self.unmatched_bank_transactions),
            'unmatched_internal_count': len(self.unmatched_internal_transactions),
            'partial_matches_count': len(self.partial_matches),
            'match_rate': (len(self.matched_transactions) / len(bank_df)) if len(bank_df) > 0 else 0,
            'reconciliation_time_seconds': duration,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
        
        self.logger.info(f"Reconciliation completed. "
                        f"Matched {summary['matched_count']} of {summary['total_bank_transactions']} "
                        f"transactions ({summary['match_rate']*100:.2f}%)")
        
        return summary
    
    def _load_internal_records(self, file_path, sheet_name=0, date_format=None):
        """
        Load internal accounting records from file.
        
        Args:
            file_path (str): Path to internal records file (CSV/Excel).
            sheet_name (int or str, optional): Sheet name/index for Excel files.
            date_format (str, optional): Format string for parsing dates.
            
        Returns:
            pandas.DataFrame: Processed internal records.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Process dates
        date_cols = [col for col in df.columns if 'date' in col.lower()]
        for col in date_cols:
            if date_format:
                df[col] = pd.to_datetime(df[col], format=date_format, errors='coerce')
            else:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                
        # Ensure primary date column exists
        if 'date' not in df.columns and len(date_cols) > 0:
            df['date'] = df[date_cols[0]]
                
        # Standardize amount columns
        if 'amount' not in df.columns:
            # Try to determine the signed amount from whatever columns are available
            if 'debit' in df.columns and 'credit' in df.columns:
                df['amount'] = df['credit'].fillna(0) - df['debit'].fillna(0)
            elif 'debit' in df.columns:
                df['amount'] = -df['debit'].fillna(0)
            elif 'credit' in df.columns:
                df['amount'] = df['credit'].fillna(0)
            else:
                # Look for columns that might contain amount information
                amount_cols = [col for col in df.columns if any(term in col.lower() 
                                                              for term in ['amount', 'amt', 'sum', 'total'])]
                if amount_cols:
                    df['amount'] = df[amount_cols[0]]
                else:
                    raise ValueError("Could not determine amount column in internal records")
        
        # Ensure numeric amount
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Create transaction_id if not present
        if 'transaction_id' not in df.columns:
            df['transaction_id'] = [f"INT_{i}" for i in range(len(df))]
            
        # Ensure description column
        if 'description' not in df.columns:
            desc_cols = [col for col in df.columns if any(term in col.lower() 
                                                      for term in ['desc', 'narration', 'particulars', 'details'])]
            if desc_cols:
                df['description'] = df[desc_cols[0]]
            else:
                df['description'] = ''
                
        # Add reference column if not present
        if 'reference' not in df.columns:
            ref_cols = [col for col in df.columns if any(term in col.lower() 
                                                     for term in ['ref', 'cheque', 'chq', 'number', 'num', 'id'])]
            if ref_cols:
                df['reference'] = df[ref_cols[0]]
            else:
                df['reference'] = ''
                
        return df

    def get_reconciliation_summary(self, include_transactions=False):
        """
        Get detailed reconciliation summary information.
        
        Args:
            include_transactions (bool): Whether to include full transaction lists in summary.
            
        Returns:
            dict: Detailed reconciliation summary.
        """
        if self.matched_transactions is None:
            raise ValueError("Cannot generate summary. Run reconcile() first.")
            
        # Calculate amount totals
        matched_total = self.matched_transactions['bank_amount'].sum() if not self.matched_transactions.empty else 0
        unmatched_bank_total = self._calculate_signed_amount_sum(self.unmatched_bank_transactions) if not self.unmatched_bank_transactions.empty else 0
        unmatched_internal_total = self.unmatched_internal_transactions['amount'].sum() if not self.unmatched_internal_transactions.empty else 0
        partial_matches_total = self.partial_matches['bank_amount'].sum() if not self.partial_matches.empty else 0
        
        # Calculate statistics by match type
        match_type_stats = {}
        if not self.matched_transactions.empty:
            match_type_counts = self.matched_transactions['match_type'].value_counts().to_dict()
            match_type_stats = {
                match_type: {
                    'count': count,
                    'percentage': (count / len(self.matched_transactions)) * 100
                }
                for match_type, count in match_type_counts.items()
            }
            
        summary = {
            'statistics': {
                'total_bank_transactions': len(self.matched_transactions) + len(self.unmatched_bank_transactions) + len(self.partial_matches) if self.matched_transactions is not None else 0,
                'matched_count': len(self.matched_transactions) if self.matched_transactions is not None else 0,
                'unmatched_bank_count': len(self.unmatched_bank_transactions) if self.unmatched_bank_transactions is not None else 0,
                'unmatched_internal_count': len(self.unmatched_internal_transactions) if self.unmatched_internal_transactions is not None else 0,
                'partial_matches_count': len(self.partial_matches) if self.partial_matches is not None else 0,
                'matched_amount_total': matched_total,
                'unmatched_bank_amount_total': unmatched_bank_total,
                'unmatched_internal_amount_total': unmatched_internal_total,
                'partial_matches_amount_total': partial_matches_total,
                'match_types': match_type_stats
            }
        }
        
        if include_transactions:
            summary['matched_transactions'] = self.matched_transactions.to_dict('records') if self.matched_transactions is not None else []
            summary['unmatched_bank_transactions'] = self.unmatched_bank_transactions.to_dict('records') if self.unmatched_bank_transactions is not None else []
            summary['unmatched_internal_transactions'] = self.unmatched_internal_transactions.to_dict('records') if self.unmatched_internal_transactions is not None else []
            summary['partial_matches'] = self.partial_matches.to_dict('records') if self.partial_matches is not None else []
            summary['match_suggestions'] = self.match_suggestions if self.match_suggestions is not None else {}
            
        return summary
    
    def _calculate_signed_amount_sum(self, df):
        """Calculate sum of signed amounts in the dataframe."""
        if df.empty:
            return 0
            
        if 'signed_amount' in df.columns:
            return df['signed_amount'].sum()
        elif 'debit' in df.columns and 'credit' in df.columns:
            return (df['credit'].fillna(0) - df['debit'].fillna(0)).sum()
        elif 'amount' in df.columns:
            return df['amount'].sum()
        else:
            return 0