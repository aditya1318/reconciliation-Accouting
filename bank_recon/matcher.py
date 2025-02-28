"""
Transaction Matching module for Indian bank reconciliation.

This module provides algorithms for matching transactions between
bank statements and internal accounting records, with specific
support for India-specific transaction formats and identifiers.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
import re


class TransactionMatcher:
    """
    Matches transactions between bank statements and internal records.
    Handles India-specific transaction formats and provides flexible
    matching algorithms with configurable tolerances.
    """

    def __init__(self, 
                 date_tolerance_days=3, 
                 amount_tolerance_percentage=0.01, 
                 description_match_threshold=80,
                 ignore_case=True,
                 match_on_gst_inclusive=True):
        """
        Initialize the transaction matcher with configurable parameters.
        
        Args:
            date_tolerance_days (int): Maximum days difference for date matching.
            amount_tolerance_percentage (float): Maximum percentage difference in amounts.
            description_match_threshold (int): Threshold for fuzzy description matching (0-100).
            ignore_case (bool): Whether to ignore case in description matching.
            match_on_gst_inclusive (bool): Whether to attempt matching with GST-inclusive amounts.
        """
        self.date_tolerance_days = date_tolerance_days
        self.amount_tolerance_percentage = amount_tolerance_percentage
        self.description_match_threshold = description_match_threshold
        self.ignore_case = ignore_case
        self.match_on_gst_inclusive = match_on_gst_inclusive

    def match_transactions(self, bank_df, internal_df, match_criteria=None):
        """
        Match transactions between bank statement and internal records.
        
        Args:
            bank_df (pandas.DataFrame): Standardized bank statement dataframe.
            internal_df (pandas.DataFrame): Internal accounting records dataframe.
            match_criteria (dict, optional): Criteria weights for matching algorithm.
                Default is {'amount': 0.5, 'date': 0.3, 'description': 0.2}
                
        Returns:
            tuple: (matched_df, unmatched_bank_df, unmatched_internal_df, partial_matches_df)
        """
        if match_criteria is None:
            match_criteria = {'amount': 0.5, 'date': 0.3, 'description': 0.2}
        
        # Make copies to avoid modifying the originals
        bank_df = bank_df.copy()
        internal_df = internal_df.copy()
        
        # Standardize column names and formats
        bank_df, internal_df = self._standardize_dataframes(bank_df, internal_df)
        
        # Add match status columns
        bank_df['match_status'] = 'UNMATCHED'
        internal_df['match_status'] = 'UNMATCHED'
        
        # Initialize result dataframes
        matched_transactions = []
        partial_matches = []
        
        # Process each bank transaction
        for idx, bank_tx in bank_df.iterrows():
            # Find potential matches
            potential_matches = self._find_potential_matches(bank_tx, internal_df)
            
            if not potential_matches.empty:
                # Calculate match scores
                potential_matches['match_score'] = potential_matches.apply(
                    lambda row: self._calculate_match_score(bank_tx, row, match_criteria), 
                    axis=1
                )
                
                # Sort by match score (highest first)
                potential_matches = potential_matches.sort_values('match_score', ascending=False)
                
                best_match = potential_matches.iloc[0]
                best_match_score = best_match['match_score']
                
                # If we have an excellent match, consider it matched
                if best_match_score >= 0.9:
                    match_info = {
                        'bank_transaction_id': bank_tx['transaction_id'],
                        'internal_transaction_id': best_match['transaction_id'],
                        'match_score': best_match_score,
                        'match_status': 'MATCHED',
                        'match_type': self._determine_match_type(bank_tx, best_match),
                        'bank_amount': self._get_signed_amount(bank_tx),
                        'internal_amount': best_match['amount'],
                        'bank_date': bank_tx['date'],
                        'internal_date': best_match['date'],
                        'amount_difference': abs(self._get_signed_amount(bank_tx) - best_match['amount']),
                        'date_difference': abs((bank_tx['date'] - best_match['date']).days),
                        'bank_description': bank_tx.get('narration', ''),
                        'internal_description': best_match.get('description', '')
                    }
                    
                    # Update match status
                    bank_df.at[idx, 'match_status'] = 'MATCHED'
                    internal_idx = best_match.name
                    internal_df.at[internal_idx, 'match_status'] = 'MATCHED'
                    
                    matched_transactions.append(match_info)
                    
                # If we have a decent match but not excellent, consider it a partial match
                elif best_match_score >= 0.7:
                    match_info = {
                        'bank_transaction_id': bank_tx['transaction_id'],
                        'internal_transaction_id': best_match['transaction_id'],
                        'match_score': best_match_score,
                        'match_status': 'PARTIAL_MATCH',
                        'match_type': self._determine_match_type(bank_tx, best_match),
                        'bank_amount': self._get_signed_amount(bank_tx),
                        'internal_amount': best_match['amount'],
                        'bank_date': bank_tx['date'],
                        'internal_date': best_match['date'],
                        'amount_difference': abs(self._get_signed_amount(bank_tx) - best_match['amount']),
                        'date_difference': abs((bank_tx['date'] - best_match['date']).days),
                        'bank_description': bank_tx.get('narration', ''),
                        'internal_description': best_match.get('description', '')
                    }
                    
                    # Update match status for bank, but not for internal record (may match with another transaction)
                    bank_df.at[idx, 'match_status'] = 'PARTIAL_MATCH'
                    
                    partial_matches.append(match_info)
        
        # Create matched transactions dataframe
        if matched_transactions:
            matched_df = pd.DataFrame(matched_transactions)
        else:
            matched_df = pd.DataFrame(columns=[
                'bank_transaction_id', 'internal_transaction_id', 'match_score', 
                'match_status', 'match_type', 'bank_amount', 'internal_amount',
                'bank_date', 'internal_date', 'amount_difference', 'date_difference',
                'bank_description', 'internal_description'
            ])
        
        # Create partial matches dataframe
        if partial_matches:
            partial_matches_df = pd.DataFrame(partial_matches)
        else:
            partial_matches_df = pd.DataFrame(columns=[
                'bank_transaction_id', 'internal_transaction_id', 'match_score', 
                'match_status', 'match_type', 'bank_amount', 'internal_amount',
                'bank_date', 'internal_date', 'amount_difference', 'date_difference',
                'bank_description', 'internal_description'
            ])
        
        # Get unmatched transactions
        unmatched_bank_df = bank_df[bank_df['match_status'] == 'UNMATCHED']
        unmatched_internal_df = internal_df[internal_df['match_status'] == 'UNMATCHED']
        
        return matched_df, unmatched_bank_df, unmatched_internal_df, partial_matches_df
    
    def _standardize_dataframes(self, bank_df, internal_df):
        """
        Standardize the dataframes to ensure they have compatible columns.
        
        Args:
            bank_df (pandas.DataFrame): Bank statement dataframe.
            internal_df (pandas.DataFrame): Internal records dataframe.
            
        Returns:
            tuple: (standardized_bank_df, standardized_internal_df)
        """
        # Ensure date columns are datetime
        if 'date' in bank_df.columns:
            bank_df['date'] = pd.to_datetime(bank_df['date'], errors='coerce')
        
        if 'date' in internal_df.columns:
            internal_df['date'] = pd.to_datetime(internal_df['date'], errors='coerce')
        
        # Add signed amount column to bank_df for easier comparison
        bank_df['signed_amount'] = self._calculate_signed_amounts(bank_df)
        
        # If internal_df doesn't have a signed amount, assume it's already signed
        if 'amount' not in internal_df.columns:
            if 'debit' in internal_df.columns and 'credit' in internal_df.columns:
                internal_df['amount'] = internal_df['credit'].fillna(0) - internal_df['debit'].fillna(0)
            else:
                # Try to determine the signed amount from whatever columns are available
                internal_df['amount'] = 0
                
        # Add transaction_id if not present in internal_df
        if 'transaction_id' not in internal_df.columns:
            internal_df['transaction_id'] = [f"INT_{i}" for i in range(len(internal_df))]
            
        return bank_df, internal_df
    
    def _calculate_signed_amounts(self, df):
        """
        Calculate signed amounts (positive for credits, negative for debits).
        
        Args:
            df (pandas.DataFrame): Bank statement dataframe.
            
        Returns:
            pandas.Series: Series of signed amounts.
        """
        if 'debit' in df.columns and 'credit' in df.columns:
            return df['credit'].fillna(0) - df['debit'].fillna(0)
        elif 'debit' in df.columns:
            return -df['debit'].fillna(0)
        elif 'credit' in df.columns:
            return df['credit'].fillna(0)
        else:
            return pd.Series([0] * len(df))
    
    def _get_signed_amount(self, row):
        """
        Get the signed amount from a transaction row.
        
        Args:
            row (pandas.Series): Transaction row.
            
        Returns:
            float: Signed amount.
        """
        if 'signed_amount' in row:
            return row['signed_amount']
        elif 'debit' in row and 'credit' in row:
            return row.get('credit', 0) - row.get('debit', 0)
        elif 'debit' in row:
            return -row.get('debit', 0)
        elif 'credit' in row:
            return row.get('credit', 0)
        else:
            return 0
    
    def _find_potential_matches(self, bank_tx, internal_df):
        """
        Find potential matches for a bank transaction in internal records.
        
        Args:
            bank_tx (pandas.Series): Bank transaction.
            internal_df (pandas.DataFrame): Internal records dataframe.
            
        Returns:
            pandas.DataFrame: Filtered dataframe of potential matches.
        """
        # Filter by date range
        bank_date = bank_tx['date']
        date_min = bank_date - timedelta(days=self.date_tolerance_days)
        date_max = bank_date + timedelta(days=self.date_tolerance_days)
        
        date_filter = (internal_df['date'] >= date_min) & (internal_df['date'] <= date_max)
        
        # Get the transaction amount
        bank_amount = self._get_signed_amount(bank_tx)
        
        # Calculate allowed amount range
        amount_min = bank_amount * (1 - self.amount_tolerance_percentage)
        amount_max = bank_amount * (1 + self.amount_tolerance_percentage)
        
        # If the amount is negative, swap min and max
        if bank_amount < 0:
            amount_min, amount_max = amount_max, amount_min
            
        # Filter by amount range
        amount_filter = (internal_df['amount'] >= amount_min) & (internal_df['amount'] <= amount_max)
        
        # Combine filters
        potential_matches = internal_df[date_filter & amount_filter].copy()
        
        # If GST inclusive matching is enabled, try with GST adjusted amount
        if self.match_on_gst_inclusive and bank_tx.get('has_gst', False) and potential_matches.empty:
            # Try with 18% GST (most common rate)
            gst_adjusted_amount = bank_amount / 1.18
            
            gst_amount_min = gst_adjusted_amount * (1 - self.amount_tolerance_percentage)
            gst_amount_max = gst_adjusted_amount * (1 + self.amount_tolerance_percentage)
            
            # If the amount is negative, swap min and max
            if gst_adjusted_amount < 0:
                gst_amount_min, gst_amount_max = gst_amount_max, gst_amount_min
                
            # Filter by GST-adjusted amount range
            gst_amount_filter = (internal_df['amount'] >= gst_amount_min) & \
                              (internal_df['amount'] <= gst_amount_max)
            
            potential_matches = internal_df[date_filter & gst_amount_filter].copy()
            
        # Already matched transactions are not potential matches
        potential_matches = potential_matches[potential_matches['match_status'] != 'MATCHED']
        
        return potential_matches
    
    def _calculate_match_score(self, bank_tx, internal_tx, criteria_weights):
        """
        Calculate a match score between a bank transaction and an internal transaction.
        
        Args:
            bank_tx (pandas.Series): Bank transaction.
            internal_tx (pandas.Series): Internal transaction.
            criteria_weights (dict): Weights for different matching criteria.
            
        Returns:
            float: Match score between 0 and 1.
        """
        # Calculate individual scores
        date_score = self._calculate_date_score(bank_tx, internal_tx)
        amount_score = self._calculate_amount_score(bank_tx, internal_tx)
        description_score = self._calculate_description_score(bank_tx, internal_tx)
        reference_score = self._calculate_reference_score(bank_tx, internal_tx)
        
        # If we have a reference match, prioritize it
        if reference_score > 0.9:
            return 0.7 * reference_score + 0.2 * amount_score + 0.1 * date_score
        
        # Otherwise use the weighted criteria
        total_score = (
            criteria_weights.get('date', 0.3) * date_score +
            criteria_weights.get('amount', 0.5) * amount_score +
            criteria_weights.get('description', 0.2) * description_score
        )
        
        return total_score
    
    def _calculate_date_score(self, bank_tx, internal_tx):
        """
        Calculate a score for date matching.
        
        Args:
            bank_tx (pandas.Series): Bank transaction.
            internal_tx (pandas.Series): Internal transaction.
            
        Returns:
            float: Date match score between 0 and 1.
        """
        day_difference = abs((bank_tx['date'] - internal_tx['date']).days)
        
        if day_difference == 0:
            return 1.0
        elif day_difference <= self.date_tolerance_days:
            return 1.0 - (day_difference / (self.date_tolerance_days + 1))
        else:
            return 0.0
    
    def _calculate_amount_score(self, bank_tx, internal_tx):
        """
        Calculate a score for amount matching.
        
        Args:
            bank_tx (pandas.Series): Bank transaction.
            internal_tx (pandas.Series): Internal transaction.
            
        Returns:
            float: Amount match score between 0 and 1.
        """
        bank_amount = self._get_signed_amount(bank_tx)
        internal_amount = internal_tx['amount']
        
        # Check for exact match
        if bank_amount == internal_amount:
            return 1.0
        
        # Calculate percentage difference
        max_amount = max(abs(bank_amount), abs(internal_amount))
        if max_amount == 0:
            return 1.0 if bank_amount == internal_amount else 0.0
        
        percentage_diff = abs(bank_amount - internal_amount) / max_amount
        
        if percentage_diff <= self.amount_tolerance_percentage:
            return 1.0 - (percentage_diff / (self.amount_tolerance_percentage * 1.01))
        
        # Check for GST-inclusive match
        if bank_tx.get('has_gst', False):
            # Try with 18% GST (most common rate)
            gst_adjusted_bank_amount = bank_amount / 1.18
            gst_percentage_diff = abs(gst_adjusted_bank_amount - internal_amount) / max(abs(gst_adjusted_bank_amount), abs(internal_amount))
            
            if gst_percentage_diff <= self.amount_tolerance_percentage:
                return 0.9 * (1.0 - (gst_percentage_diff / (self.amount_tolerance_percentage * 1.01)))
        
        # Check for TDS match
        if bank_tx.get('has_tds', False):
            # Try with 10% TDS (common rate)
            tds_adjusted_internal_amount = internal_amount / 0.9
            tds_percentage_diff = abs(bank_amount - tds_adjusted_internal_amount) / max(abs(bank_amount), abs(tds_adjusted_internal_amount))
            
            if tds_percentage_diff <= self.amount_tolerance_percentage:
                return 0.9 * (1.0 - (tds_percentage_diff / (self.amount_tolerance_percentage * 1.01)))
        
        return 0.0
    
    def _calculate_description_score(self, bank_tx, internal_tx):
        """
        Calculate a score for description matching using fuzzy matching.
        
        Args:
            bank_tx (pandas.Series): Bank transaction.
            internal_tx (pandas.Series): Internal transaction.
            
        Returns:
            float: Description match score between 0 and 1.
        """
        bank_desc = str(bank_tx.get('narration', ''))
        internal_desc = str(internal_tx.get('description', ''))
        
        if not bank_desc or not internal_desc:
            return 0.0
        
        if self.ignore_case:
            bank_desc = bank_desc.upper()
            internal_desc = internal_desc.upper()
        
        # Calculate ratio using fuzzywuzzy
        ratio = fuzz.token_sort_ratio(bank_desc, internal_desc)
        
        if ratio >= self.description_match_threshold:
            return ratio / 100.0
        
        return 0.0
    
    def _calculate_reference_score(self, bank_tx, internal_tx):
        """
        Calculate a score for reference ID matching.
        
        Args:
            bank_tx (pandas.Series): Bank transaction.
            internal_tx (pandas.Series): Internal transaction.
            
        Returns:
            float: Reference match score between 0 and 1.
        """
        # Check for matching reference IDs
        bank_ref = str(bank_tx.get('ref_no', ''))
        internal_ref = str(internal_tx.get('reference', ''))
        
        # Check if we have extracted a reference ID from the description
        bank_extracted_ref = str(bank_tx.get('reference_id', ''))
        
        # If we have direct match on reference numbers
        if bank_ref and internal_ref and (bank_ref == internal_ref):
            return 1.0
        
        # Check for extracted reference in internal reference
        if bank_extracted_ref and internal_ref and (bank_extracted_ref in internal_ref or internal_ref in bank_extracted_ref):
            return 0.95
        
        # Check if reference appears in description
        internal_desc = str(internal_tx.get('description', ''))
        if bank_ref and internal_desc:
            if bank_ref in internal_desc:
                return 0.9
        
        bank_desc = str(bank_tx.get('narration', ''))
        if internal_ref and bank_desc:
            if internal_ref in bank_desc:
                return 0.9
        
        return 0.0
    
    def _determine_match_type(self, bank_tx, internal_tx):
        """
        Determine the type of match between bank and internal transactions.
        
        Args:
            bank_tx (pandas.Series): Bank transaction.
            internal_tx (pandas.Series): Internal transaction.
            
        Returns:
            str: Match type (EXACT, AMOUNT_MISMATCH, DATE_MISMATCH, PARTIAL)
        """
        bank_amount = self._get_signed_amount(bank_tx)
        internal_amount = internal_tx['amount']
        
        # Check exact match
        if (bank_tx['date'] == internal_tx['date']) and (bank_amount == internal_amount):
            return 'EXACT'
        
        # Check amount mismatch
        if (bank_tx['date'] == internal_tx['date']) and (bank_amount != internal_amount):
            return 'AMOUNT_MISMATCH'
        
        # Check date mismatch
        if (bank_tx['date'] != internal_tx['date']) and (bank_amount == internal_amount):
            return 'DATE_MISMATCH'
        
        # Otherwise it's a partial match
        return 'PARTIAL'
    
    def suggest_matches(self, unmatched_bank_df, unmatched_internal_df, 
                        top_n=3, min_score=0.6):
        """
        Suggest potential matches for unmatched transactions.
        
        Args:
            unmatched_bank_df (pandas.DataFrame): Unmatched bank transactions.
            unmatched_internal_df (pandas.DataFrame): Unmatched internal transactions.
            top_n (int): Number of top suggestions to return for each transaction.
            min_score (float): Minimum score threshold for suggestions.
            
        Returns:
            dict: Dictionary of suggested matches with scores.
        """
        suggestions = {}
        
        # Ensure we have copied dataframes
        unmatched_bank_df = unmatched_bank_df.copy()
        unmatched_internal_df = unmatched_internal_df.copy()
        
        # Standardize dataframes
        unmatched_bank_df, unmatched_internal_df = self._standardize_dataframes(
            unmatched_bank_df, unmatched_internal_df
        )
        
        for idx, bank_tx in unmatched_bank_df.iterrows():
            tx_id = bank_tx['transaction_id']
            
            # Relax constraints for suggestion
            suggestions[tx_id] = []
            
            # Try with relaxed date tolerance
            relaxed_date_tolerance = self.date_tolerance_days * 2
            date_min = bank_tx['date'] - timedelta(days=relaxed_date_tolerance)
            date_max = bank_tx['date'] + timedelta(days=relaxed_date_tolerance)
            
            date_filter = (unmatched_internal_df['date'] >= date_min) & \
                         (unmatched_internal_df['date'] <= date_max)
            
            bank_amount = self._get_signed_amount(bank_tx)
            
            # Try with relaxed amount tolerance
            relaxed_amount_tolerance = self.amount_tolerance_percentage * 3
            amount_min = bank_amount * (1 - relaxed_amount_tolerance)
            amount_max = bank_amount * (1 + relaxed_amount_tolerance)
            
            # If the amount is negative, swap min and max
            if bank_amount < 0:
                amount_min, amount_max = amount_max, amount_min
                
            amount_filter = (unmatched_internal_df['amount'] >= amount_min) & \
                          (unmatched_internal_df['amount'] <= amount_max)
            
            # Combine filters
            candidates = unmatched_internal_df[date_filter | amount_filter].copy()
            
            if not candidates.empty:
                # Calculate match scores
                candidates['match_score'] = candidates.apply(
                    lambda row: self._calculate_match_score(
                        bank_tx, row, {'amount': 0.5, 'date': 0.3, 'description': 0.2}
                    ), 
                    axis=1
                )
                
                # Filter by minimum score
                candidates = candidates[candidates['match_score'] >= min_score]
                
                # Sort by score
                candidates = candidates.sort_values('match_score', ascending=False)
                
                # Get top suggestions
                for i, (candidate_idx, candidate) in enumerate(candidates.head(top_n).iterrows()):
                    suggestion = {
                        'internal_transaction_id': candidate['transaction_id'],
                        'match_score': candidate['match_score'],
                        'internal_amount': candidate['amount'],
                        'internal_date': candidate['date'],
                        'bank_amount': bank_amount,
                        'bank_date': bank_tx['date'],
                        'internal_description': candidate.get('description', ''),
                        'bank_description': bank_tx.get('narration', '')
                    }
                    
                    suggestions[tx_id].append(suggestion)
        
        return suggestions