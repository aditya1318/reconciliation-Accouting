"""
Parser module for Indian bank statements.

This module handles the parsing of bank statement data from various formats
(CSV, Excel, PDF) and standardizes them according to predefined configurations.
"""

import os
import pandas as pd
import yaml
from datetime import datetime
import re


class BankStatementParser:
    """Parser for Indian bank statements from different banks and formats."""

    def __init__(self, config_path=None):
        """
        Initialize the bank statement parser.

        Args:
            config_path (str, optional): Path to the bank formats configuration file.
                Defaults to '../config/bank_formats.yaml'.
        """
        if config_path is None:
            # Default config path relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(os.path.dirname(current_dir), 'config', 'bank_formats.yaml')
        
        with open(config_path, 'r') as file:
            self.bank_formats = yaml.safe_load(file)
    
    def detect_bank(self, df):
        """
        Detect which bank the statement belongs to based on column names.

        Args:
            df (pandas.DataFrame): The loaded bank statement dataframe.

        Returns:
            str: The detected bank identifier or None if not detected.
        """
        columns = set(df.columns.str.strip())
        
        for bank, config in self.bank_formats.items():
            bank_columns = set(config['columns'].values())
            # If a significant number of columns match, consider it a match
            match_count = len(columns.intersection(bank_columns))
            if match_count >= len(bank_columns) * 0.7:  # 70% threshold
                return bank
        
        return None
    
    def parse(self, file_path, bank=None, sheet_name=0):
        """
        Parse a bank statement file into a standardized format.
        
        Args:
            file_path (str): Path to the bank statement file.
            bank (str, optional): Bank identifier to use specific parsing rules.
                If None, will attempt to auto-detect.
            sheet_name (int or str, optional): Sheet to read for Excel files. Defaults to 0.
        
        Returns:
            pandas.DataFrame: Standardized bank statement dataframe.
            
        Raises:
            ValueError: If bank format cannot be detected or file format is unsupported.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Clean column names (remove whitespace)
        df.columns = df.columns.str.strip()
        
        if bank is None:
            bank = self.detect_bank(df)
            if bank is None:
                raise ValueError("Could not detect bank format. Please specify bank parameter.")
        
        if bank not in self.bank_formats:
            raise ValueError(f"Unsupported bank: {bank}")
        
        return self._standardize_data(df, bank)
    
    def _standardize_data(self, df, bank):
        """
        Standardize the dataframe according to the bank's format configuration.
        
        Args:
            df (pandas.DataFrame): Original bank statement dataframe.
            bank (str): Bank identifier.
            
        Returns:
            pandas.DataFrame: Standardized dataframe.
        """
        bank_config = self.bank_formats[bank]
        column_mapping = bank_config['columns']
        date_format = bank_config['date_format']
        
        # Rename columns to standardized names
        inverse_mapping = {v: k for k, v in column_mapping.items()}
        df = df.rename(columns=inverse_mapping)
        
        # Convert date columns
        for date_col in ['date', 'value_date']:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], format=date_format, errors='coerce')
        
        # Ensure numeric columns are numeric
        for amount_col in ['debit', 'credit', 'balance']:
            if amount_col in df.columns:
                df[amount_col] = self._clean_amount_column(df[amount_col])
        
        # Normalize transaction descriptions
        if 'narration' in df.columns:
            df['narration'] = df['narration'].astype(str).apply(self._normalize_description)
            
            # Extract Indian payment identifiers
            df['payment_method'] = df['narration'].apply(self._extract_payment_method)
            df['reference_id'] = df['narration'].apply(self._extract_reference_id)
            df['ifsc_code'] = df['narration'].apply(self._extract_ifsc_code)
            df['has_gst'] = df['narration'].apply(self._check_for_gst)
            df['has_tds'] = df['narration'].apply(self._check_for_tds)
        
        # Add a unique transaction ID
        df['transaction_id'] = self._generate_transaction_ids(df)
        
        # Return only standardized columns
        std_columns = ['transaction_id', 'date', 'value_date', 'ref_no', 'narration', 
                        'debit', 'credit', 'balance', 'payment_method', 'reference_id', 
                        'ifsc_code', 'has_gst', 'has_tds']
        
        # Filter for columns that actually exist in the dataframe
        available_columns = [col for col in std_columns if col in df.columns]
        return df[available_columns]
    
    def _clean_amount_column(self, column):
        """
        Clean amount columns by removing currency symbols, commas, etc.
        
        Args:
            column (pandas.Series): Amount column to clean.
            
        Returns:
            pandas.Series: Cleaned numeric column.
        """
        if column.dtype == 'object':
            # Convert to string first
            column = column.astype(str)
            # Remove currency symbols, commas, and convert to float
            column = column.str.replace('₹', '', regex=False)
            column = column.str.replace('Rs.', '', regex=False)
            column = column.str.replace('INR', '', regex=False)
            column = column.str.replace(',', '', regex=False)
            column = column.str.replace(' ', '', regex=False)
            column = pd.to_numeric(column, errors='coerce')
        return column
    
    def _normalize_description(self, desc):
        """
        Normalize transaction descriptions by removing extra spaces, standardizing case, etc.
        
        Args:
            desc (str): Transaction description.
            
        Returns:
            str: Normalized description.
        """
        if pd.isna(desc):
            return ""
        
        # Convert to uppercase
        desc = desc.upper()
        
        # Replace multiple spaces with a single space
        desc = re.sub(r'\s+', ' ', desc).strip()
        
        # Remove common prefixes
        prefixes = ["TRANSACTION DETAILS:", "NARRATION:", "DESCRIPTION:", "PARTICULARS:"]
        for prefix in prefixes:
            if desc.startswith(prefix):
                desc = desc[len(prefix):].strip()
        
        return desc
    
    def _extract_payment_method(self, desc):
        """
        Extract payment method (UPI, IMPS, NEFT, RTGS, etc.) from description.
        
        Args:
            desc (str): Transaction description.
            
        Returns:
            str: Payment method or empty string if not found.
        """
        payment_methods = {
            "UPI": r'UPI[/:\s]',
            "IMPS": r'IMPS[/:\s]',
            "NEFT": r'NEFT[/:\s]',
            "RTGS": r'RTGS[/:\s]',
            "FT": r'FT[/:\s]',
            "ACH": r'ACH[/:\s]',
            "CHEQUE": r'CHQ|CHEQUE|CQ\.?[/:\s]'
        }
        
        for method, pattern in payment_methods.items():
            if re.search(pattern, desc):
                return method
        
        return ""
    
    def _extract_reference_id(self, desc):
        """
        Extract reference IDs from transaction description.
        
        Args:
            desc (str): Transaction description.
            
        Returns:
            str: Reference ID or empty string if not found.
        """
        # UPI reference pattern (example: UPI/123456789012/PAYMENT)
        upi_match = re.search(r'UPI[/:\s][A-Z]*(\d{9,})', desc)
        if upi_match:
            return upi_match.group(1)
        
        # IMPS reference pattern (example: IMPS/P2A/123456789012/PAYMENT)
        imps_match = re.search(r'IMPS[/:\s][A-Z0-9/]*(\d{9,})', desc)
        if imps_match:
            return imps_match.group(1)
        
        # NEFT reference pattern
        neft_match = re.search(r'NEFT[/:\s]([A-Z0-9]{11,})', desc)
        if neft_match:
            return neft_match.group(1)
        
        # Generic reference pattern
        ref_match = re.search(r'REF\.?(?:NO)?[.:\s]?([A-Z0-9]{6,})', desc)
        if ref_match:
            return ref_match.group(1)
        
        return ""
    
    def _extract_ifsc_code(self, desc):
        """
        Extract IFSC code from transaction description.
        
        Args:
            desc (str): Transaction description.
            
        Returns:
            str: IFSC code or empty string if not found.
        """
        # IFSC code pattern (4 letters followed by 7 alphanumeric characters)
        ifsc_match = re.search(r'[A-Z]{4}0[A-Z0-9]{6}', desc)
        if ifsc_match:
            return ifsc_match.group(0)
        
        return ""
    
    def _check_for_gst(self, desc):
        """
        Check if transaction description mentions GST.
        
        Args:
            desc (str): Transaction description.
            
        Returns:
            bool: True if GST is mentioned, False otherwise.
        """
        gst_patterns = [r'GST', r'CGST', r'SGST', r'IGST', r'GSTIN']
        for pattern in gst_patterns:
            if re.search(pattern, desc):
                return True
        
        return False
    
    def _check_for_tds(self, desc):
        """
        Check if transaction description mentions TDS.
        
        Args:
            desc (str): Transaction description.
            
        Returns:
            bool: True if TDS is mentioned, False otherwise.
        """
        return bool(re.search(r'TDS', desc))
    
    def _generate_transaction_ids(self, df):
        """
        Generate unique transaction IDs for each transaction.
        
        Args:
            df (pandas.DataFrame): Bank statement dataframe.
            
        Returns:
            pandas.Series: Series of unique transaction IDs.
        """
        # Use date + amount + incremental counter for transactions on the same day with same amount
        # Convert date to string
        if 'date' in df.columns:
            date_str = df['date'].dt.strftime('%Y%m%d')
        else:
            # If date column doesn't exist, use index
            date_str = pd.Series([f"IDX{i:06d}" for i in range(len(df))])
        
        # Get amount (prefer debit, then credit)
        if 'debit' in df.columns and 'credit' in df.columns:
            amount = df['debit'].fillna(0) - df['credit'].fillna(0)
        elif 'debit' in df.columns:
            amount = df['debit'].fillna(0)
        elif 'credit' in df.columns:
            amount = -df['credit'].fillna(0)
        else:
            amount = pd.Series([0] * len(df))
        
        # Convert amount to string with fixed precision
        amount_str = amount.abs().map('{:.2f}'.format)
        
        # Combine date and amount
        combined = date_str + '_' + amount_str
        
        # Add counter for duplicates
        transaction_ids = []
        counter_dict = {}
        
        for idx, key in enumerate(combined):
            if key in counter_dict:
                counter_dict[key] += 1
                transaction_ids.append(f"{key}_{counter_dict[key]}")
            else:
                counter_dict[key] = 1
                transaction_ids.append(f"{key}_1")
        
        return transaction_ids