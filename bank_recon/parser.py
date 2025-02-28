"""
Parser module for Indian bank statements.

This module handles the parsing of bank statement data from various formats
(CSV, Excel, PDF) and standardizes them according to predefined configurations.
"""

import os
from typing import Optional
import pandas as pd
import yaml
from datetime import datetime
import re
import logging

from .schema_mapper.mapper import SchemaMapper  # Import the SchemaMapper


class BankStatementParser:
    """Parser for Indian bank statements from different banks and formats."""

    def __init__(self, config_path=None, schema_mapper: Optional[SchemaMapper] = None, logger=None):
        """
        Initialize the bank statement parser.

        Args:
            config_path (str, optional):  Deprecated. Now uses schema_mapper.
            schema_mapper (SchemaMapper, optional): Instance of SchemaMapper.
            logger (logging.Logger, optional): Logger.
        """
        self.logger = logger or logging.getLogger('BankStatementParser')
        self.schema_mapper = schema_mapper or SchemaMapper()

        if config_path:
            self.logger.warning("The config_path argument is deprecated and will be ignored. "
                                "BankStatementParser now uses SchemaMapper for configuration.")

    def parse(self, file_path, bank=None, sheet_name=0):
        """
        Parse a bank statement file into a standardized format.

        Args:
            file_path (str): Path to the bank statement file.
            bank (str, optional): Bank identifier to use specific parsing rules.
                If None, will attempt to auto-detect.
            sheet_name (int or str, optional): Sheet name/index for Excel files. Defaults to 0.

        Returns:
            pandas.DataFrame: Standardized bank statement dataframe.

        Raises:
            ValueError: If bank format cannot be detected or file format is unsupported.
        """
        try:
            # Use SchemaMapper to process the bank statement
            df, process_info = self.schema_mapper.process_bank_statement(file_path, schema_id=bank)

            if not process_info['is_valid']:
                self.logger.warning(f"Data validation issues found during parsing: {process_info['validation_errors']}")

            return df

        except Exception as e:
            self.logger.error(f"Failed to parse bank statement: {e}")
            raise

    # Remove the methods that are now handled by the schema mapper
    # def detect_bank(self, df): ...
    # def _standardize_data(self, df, bank): ...
    # def _clean_amount_column(self, column): ...
    # def _normalize_description(self, desc): ...
    # def _extract_payment_method(self, desc): ...
    # def _extract_reference_id(self, desc): ...
    # def _extract_ifsc_code(self, desc): ...
    # def _check_for_gst(self, desc): ...
    # def _check_for_tds(self, desc): ...
    # def _generate_transaction_ids(self, df): ...