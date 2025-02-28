"""
Report Generator module for bank reconciliation.

This module handles generating reports from reconciliation results in various formats
(Excel, CSV, HTML) with India-specific formatting and categorization.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging


class ReconciliationReportGenerator:
    """
    Generates detailed reports from reconciliation results in various formats.
    
    Formats supported:
    - Excel (.xlsx)
    - CSV (.csv)
    - HTML (.html)
    - JSON (.json)
    """
    
    def __init__(self, output_dir=None, logger=None):
        """
        Initialize the report generator.
        
        Args:
            output_dir (str, optional): Directory for saving reports. 
                Defaults to current directory.
            logger (logging.Logger, optional): Logger for recording report generation.
        """
        self.output_dir = output_dir or os.getcwd()
        
        # Setup logger
        if logger is None:
            self.logger = logging.getLogger('recon_report_generator')
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger
    
    def generate_excel_report(self, reconciler, output_path=None, include_suggestions=True):
        """
        Generate a comprehensive Excel report with multiple sheets.
        
        Args:
            reconciler (BankReconciler): Reconciler with reconciliation results.
            output_path (str, optional): Path for saving the report.
                If None, a timestamped filename will be used.
            include_suggestions (bool): Whether to include match suggestions.
            
        Returns:
            str: Path to the generated report.
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_dir, f"reconciliation_report_{timestamp}.xlsx")
        
        self.logger.info(f"Generating Excel report at {output_path}")
        
        # Create Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = self._create_summary_dataframe(reconciler)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Matched transactions
            if reconciler.matched_transactions is not None and not reconciler.matched_transactions.empty:
                matched_df = self._prepare_matched_transactions(reconciler.matched_transactions)
                matched_df.to_excel(writer, sheet_name='Matched Transactions', index=False)
                
                # Write sheets by match type
                match_types = reconciler.matched_transactions['match_type'].unique()
                for match_type in match_types:
                    subset = reconciler.matched_transactions[reconciler.matched_transactions['match_type'] == match_type]
                    if not subset.empty:
                        prepared_df = self._prepare_matched_transactions(subset)
                        prepared_df.to_excel(writer, sheet_name=f'{match_type} Matches', index=False)
            
            # Unmatched bank transactions
            if reconciler.unmatched_bank_transactions is not None and not reconciler.unmatched_bank_transactions.empty:
                unmatched_bank_df = self._prepare_unmatched_bank_transactions(reconciler.unmatched_bank_transactions)
                unmatched_bank_df.to_excel(writer, sheet_name='Unmatched Bank', index=False)
            
            # Unmatched internal transactions
            if reconciler.unmatched_internal_transactions is not None and not reconciler.unmatched_internal_transactions.empty:
                unmatched_internal_df = self._prepare_unmatched_internal_transactions(reconciler.unmatched_internal_transactions)
                unmatched_internal_df.to_excel(writer, sheet_name='Unmatched Internal', index=False)
            
            # Partial matches
            if reconciler.partial_matches is not None and not reconciler.partial_matches.empty:
                partial_matches_df = self._prepare_matched_transactions(reconciler.partial_matches)
                partial_matches_df.to_excel(writer, sheet_name='Partial Matches', index=False)
            
            # Match suggestions
            if include_suggestions and reconciler.match_suggestions:
                suggestions_df = self._prepare_match_suggestions(reconciler.match_suggestions)
                suggestions_df.to_excel(writer, sheet_name='Suggestions', index=False)
        
        self.logger.info(f"Excel report generated successfully")
        return output_path
    
    def generate_csv_reports(self, reconciler, base_filename=None):
        """
        Generate multiple CSV files for different reconciliation components.
        
        Args:
            reconciler (BankReconciler): Reconciler with reconciliation results.
            base_filename (str, optional): Base name for CSV files.
                If None, a timestamped base name will be used.
            
        Returns:
            dict: Mapping of report types to their file paths.
        """
        if base_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"reconciliation_{timestamp}"
        
        output_files = {}
        
        # Summary
        summary_path = os.path.join(self.output_dir, f"{base_filename}_summary.csv")
        summary_df = self._create_summary_dataframe(reconciler)
        summary_df.to_csv(summary_path, index=False)
        output_files['summary'] = summary_path
        
        # Matched transactions
        if reconciler.matched_transactions is not None and not reconciler.matched_transactions.empty:
            matched_path = os.path.join(self.output_dir, f"{base_filename}_matched.csv")
            matched_df = self._prepare_matched_transactions(reconciler.matched_transactions)
            matched_df.to_csv(matched_path, index=False)
            output_files['matched'] = matched_path
        
        # Unmatched bank transactions
        if reconciler.unmatched_bank_transactions is not None and not reconciler.unmatched_bank_transactions.empty:
            unmatched_bank_path = os.path.join(self.output_dir, f"{base_filename}_unmatched_bank.csv")
            unmatched_bank_df = self._prepare_unmatched_bank_transactions(reconciler.unmatched_bank_transactions)
            unmatched_bank_df.to_csv(unmatched_bank_path, index=False)
            output_files['unmatched_bank'] = unmatched_bank_path
        
        # Unmatched internal transactions
        if reconciler.unmatched_internal_transactions is not None and not reconciler.unmatched_internal_transactions.empty:
            unmatched_internal_path = os.path.join(self.output_dir, f"{base_filename}_unmatched_internal.csv")
            unmatched_internal_df = self._prepare_unmatched_internal_transactions(reconciler.unmatched_internal_transactions)
            unmatched_internal_df.to_csv(unmatched_internal_path, index=False)
            output_files['unmatched_internal'] = unmatched_internal_path
        
        # Partial matches
        if reconciler.partial_matches is not None and not reconciler.partial_matches.empty:
            partial_path = os.path.join(self.output_dir, f"{base_filename}_partial_matches.csv")
            partial_df = self._prepare_matched_transactions(reconciler.partial_matches)
            partial_df.to_csv(partial_path, index=False)
            output_files['partial_matches'] = partial_path
        
        self.logger.info(f"CSV reports generated successfully")
        return output_files
    
    def generate_html_report(self, reconciler, output_path=None):
        """
        Generate a single HTML report with all reconciliation results.
        
        Args:
            reconciler (BankReconciler): Reconciler with reconciliation results.
            output_path (str, optional): Path for saving the report.
                If None, a timestamped filename will be used.
            
        Returns:
            str: Path to the generated report.
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_dir, f"reconciliation_report_{timestamp}.html")
        
        self.logger.info(f"Generating HTML report at {output_path}")
        
        # Create HTML content with sections for each component
        html_content = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>Bank Reconciliation Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #2c3e50; }",
            "h2 { color: #3498db; margin-top: 30px; }",
            "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; font-weight: bold; }",
            "tr:nth-child(even) { background-color: #f9f9f9; }",
            ".summary-value { font-weight: bold; color: #2c3e50; }",
            ".match-exact { background-color: #d4edda; }",  # Green
            ".match-partial { background-color: #fff3cd; }",  # Yellow
            ".match-date { background-color: #d1ecf1; }",  # Blue
            ".match-amount { background-color: #f8d7da; }",  # Red
            ".good-score { color: green; }",
            ".medium-score { color: orange; }",
            ".low-score { color: red; }",
            "footer { margin-top: 50px; font-size: 12px; color: #7f8c8d; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Bank Reconciliation Report</h1>",
            f"<p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        ]
        
        # Add summary section
        html_content.extend(self._generate_html_summary(reconciler))
        
        # Add matched transactions section
        if reconciler.matched_transactions is not None and not reconciler.matched_transactions.empty:
            html_content.extend(self._generate_html_matched_section(reconciler.matched_transactions))
        
        # Add unmatched bank transactions section
        if reconciler.unmatched_bank_transactions is not None and not reconciler.unmatched_bank_transactions.empty:
            html_content.extend(self._generate_html_unmatched_bank_section(reconciler.unmatched_bank_transactions))
        
        # Add unmatched internal transactions section
        if reconciler.unmatched_internal_transactions is not None and not reconciler.unmatched_internal_transactions.empty:
            html_content.extend(self._generate_html_unmatched_internal_section(reconciler.unmatched_internal_transactions))
        
        # Add partial matches section
        if reconciler.partial_matches is not None and not reconciler.partial_matches.empty:
            html_content.extend(self._generate_html_partial_matches_section(reconciler.partial_matches))
        
        # Add match suggestions section
        if reconciler.match_suggestions:
            html_content.extend(self._generate_html_suggestions_section(reconciler.match_suggestions))
        
        # Add footer and close tags
        html_content.extend([
            "<footer>",
            "Generated by Indian Bank Reconciliation System",
            "</footer>",
            "</body>",
            "</html>"
        ])
        
        # Write HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_content))
        
        self.logger.info(f"HTML report generated successfully")
        return output_path
    
    def generate_json_report(self, reconciler, output_path=None):
        """
        Generate a JSON report with all reconciliation results.
        
        Args:
            reconciler (BankReconciler): Reconciler with reconciliation results.
            output_path (str, optional): Path for saving the report.
                If None, a timestamped filename will be used.
            
        Returns:
            str: Path to the generated report.
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_dir, f"reconciliation_report_{timestamp}.json")
        
        self.logger.info(f"Generating JSON report at {output_path}")
        
        # Get comprehensive summary with all transactions
        summary = reconciler.get_reconciliation_summary(include_transactions=True)
        
        # Convert special types to native Python types
        def convert_datetimes(obj):
            if isinstance(obj, (pd.Timestamp, datetime)):
                return obj.isoformat()
            elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
                return int(obj)
            elif isinstance(obj, (np.float64, np.float32, np.float16)):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, pd.Series):
                return obj.to_list()
            elif isinstance(obj, pd.DataFrame):
                return obj.to_dict(orient='records')
            return obj
        
        # Write JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, default=convert_datetimes, indent=2)
        
        self.logger.info(f"JSON report generated successfully")
        return output_path
    
    def _create_summary_dataframe(self, reconciler):
        """Create a DataFrame with reconciliation summary information."""
        summary = reconciler.get_reconciliation_summary()['statistics']
        
        # Create summary rows
        summary_rows = [
            {'Category': 'Total Bank Transactions', 'Value': summary['total_bank_transactions']},
            {'Category': 'Matched Transactions', 'Value': summary['matched_count']},
            {'Category': 'Unmatched Bank Transactions', 'Value': summary['unmatched_bank_count']},
            {'Category': 'Unmatched Internal Records', 'Value': summary['unmatched_internal_count']},
            {'Category': 'Partial Matches', 'Value': summary['partial_matches_count']},
            {'Category': 'Match Rate (%)', 'Value': f"{(summary['matched_count'] / summary['total_bank_transactions']) * 100:.2f}%" if summary['total_bank_transactions'] > 0 else "0.00%"},
            {'Category': 'Matched Amount Total (₹)', 'Value': f"₹{summary['matched_amount_total']:,.2f}"},
            {'Category': 'Unmatched Bank Amount Total (₹)', 'Value': f"₹{summary['unmatched_bank_amount_total']:,.2f}"},
            {'Category': 'Unmatched Internal Amount Total (₹)', 'Value': f"₹{summary['unmatched_internal_amount_total']:,.2f}"},
            {'Category': 'Partial Matches Amount Total (₹)', 'Value': f"₹{summary['partial_matches_amount_total']:,.2f}"}
        ]
        
        # Add match type statistics if available
        if 'match_types' in summary and summary['match_types']:
            for match_type, stats in summary['match_types'].items():
                summary_rows.append({
                    'Category': f"{match_type} Matches", 
                    'Value': f"{stats['count']} ({stats['percentage']:.2f}%)"
                })
        
        return pd.DataFrame(summary_rows)
    
    def _prepare_matched_transactions(self, df):
        """Prepare matched transactions for reporting."""
        # Create a copy to avoid modifying the original
        result_df = df.copy()
        
        # Format date columns
        date_cols = [col for col in result_df.columns if 'date' in col.lower()]
        for col in date_cols:
            if pd.api.types.is_datetime64_any_dtype(result_df[col]):
                result_df[col] = result_df[col].dt.strftime('%Y-%m-%d')
        
        # Format amount columns to have Rupee symbol
        amount_cols = [col for col in result_df.columns if 'amount' in col.lower()]
        for col in amount_cols:
            result_df[col] = result_df[col].apply(lambda x: f"₹{x:,.2f}" if pd.notnull(x) else "")
        
        # Format score as percentage
        if 'match_score' in result_df.columns:
            result_df['match_score'] = result_df['match_score'].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "")
        
        # Reorder columns for better readability
        preferred_order = [
            'bank_transaction_id', 'internal_transaction_id', 'match_type', 'match_score',
            'bank_date', 'internal_date', 'date_difference',
            'bank_amount', 'internal_amount', 'amount_difference',
            'bank_description', 'internal_description'
        ]
        
        # Only include columns that exist in the dataframe
        ordered_cols = [col for col in preferred_order if col in result_df.columns]
        
        # Add any remaining columns at the end
        remaining_cols = [col for col in result_df.columns if col not in ordered_cols]
        final_cols = ordered_cols + remaining_cols
        
        return result_df[final_cols]
    
    def _prepare_unmatched_bank_transactions(self, df):
        """Prepare unmatched bank transactions for reporting."""
        # Create a copy
        result_df = df.copy()
        
        # Format date columns
        if 'date' in result_df.columns and pd.api.types.is_datetime64_any_dtype(result_df['date']):
            result_df['date'] = result_df['date'].dt.strftime('%Y-%m-%d')
        
        if 'value_date' in result_df.columns and pd.api.types.is_datetime64_any_dtype(result_df['value_date']):
            result_df['value_date'] = result_df['value_date'].dt.strftime('%Y-%m-%d')
        
        # Format amount columns to have Rupee symbol
        for col in ['debit', 'credit', 'balance', 'signed_amount']:
            if col in result_df.columns:
                result_df[col] = result_df[col].apply(lambda x: f"₹{x:,.2f}" if pd.notnull(x) else "")
        
        # Preferred column order
        preferred_order = [
            'transaction_id', 'date', 'value_date', 'ref_no', 'narration',
            'debit', 'credit', 'signed_amount', 'balance',
            'payment_method', 'reference_id', 'ifsc_code', 'has_gst', 'has_tds'
        ]
        
        # Only include columns that exist in the dataframe
        ordered_cols = [col for col in preferred_order if col in result_df.columns]
        
        # Add any remaining columns at the end
        remaining_cols = [col for col in result_df.columns if col not in ordered_cols]
        final_cols = ordered_cols + remaining_cols
        
        return result_df[final_cols]
    
    def _prepare_unmatched_internal_transactions(self, df):
        """Prepare unmatched internal transactions for reporting."""
        # Create a copy
        result_df = df.copy()
        
        # Format date columns
        if 'date' in result_df.columns and pd.api.types.is_datetime64_any_dtype(result_df['date']):
            result_df['date'] = result_df['date'].dt.strftime('%Y-%m-%d')
        
        # Format amount column to have Rupee symbol
        if 'amount' in result_df.columns:
            result_df['amount'] = result_df['amount'].apply(lambda x: f"₹{x:,.2f}" if pd.notnull(x) else "")
        
        # Preferred column order
        preferred_order = [
            'transaction_id', 'date', 'reference', 'description', 'amount'
        ]
        
        # Only include columns that exist in the dataframe
        ordered_cols = [col for col in preferred_order if col in result_df.columns]
        
        # Add any remaining columns at the end
        remaining_cols = [col for col in result_df.columns if col not in ordered_cols]
        final_cols = ordered_cols + remaining_cols
        
        return result_df[final_cols]
    
    def _prepare_match_suggestions(self, suggestions_dict):
        """Convert match suggestions dictionary to a dataframe for reporting."""
        rows = []
        
        for bank_tx_id, matches in suggestions_dict.items():
            for match in matches:
                # Format dates as strings if they're datetime objects
                bank_date = match['bank_date']
                internal_date = match['internal_date']
                
                if isinstance(bank_date, (datetime, pd.Timestamp)):
                    bank_date = bank_date.strftime('%Y-%m-%d')
                
                if isinstance(internal_date, (datetime, pd.Timestamp)):
                    internal_date = internal_date.strftime('%Y-%m-%d')
                
                # Format amounts with Rupee symbol
                bank_amount = f"₹{match['bank_amount']:,.2f}" if pd.notnull(match['bank_amount']) else ""
                internal_amount = f"₹{match['internal_amount']:,.2f}" if pd.notnull(match['internal_amount']) else ""
                
                # Format match score as percentage
                match_score = f"{match['match_score']*100:.2f}%" if pd.notnull(match['match_score']) else ""
                
                rows.append({
                    'bank_transaction_id': bank_tx_id,
                    'internal_transaction_id': match['internal_transaction_id'],
                    'match_score': match_score,
                    'bank_date': bank_date,
                    'internal_date': internal_date,
                    'bank_amount': bank_amount,
                    'internal_amount': internal_amount,
                    'bank_description': match['bank_description'],
                    'internal_description': match['internal_description']
                })
        
        if not rows:
            return pd.DataFrame(columns=[
                'bank_transaction_id', 'internal_transaction_id', 'match_score',
                'bank_date', 'internal_date', 'bank_amount', 'internal_amount',
                'bank_description', 'internal_description'
            ])
        
        return pd.DataFrame(rows)
    
    def _generate_html_summary(self, reconciler):
        """Generate HTML summary section."""
        summary = reconciler.get_reconciliation_summary()['statistics']
        match_rate = (summary['matched_count'] / summary['total_bank_transactions']) * 100 if summary['total_bank_transactions'] > 0 else 0
        
        html = [
            "<h2>Reconciliation Summary</h2>",
            "<table>",
            "<tr><th>Category</th><th>Value</th></tr>",
            f"<tr><td>Total Bank Transactions</td><td class='summary-value'>{summary['total_bank_transactions']}</td></tr>",
            f"<tr><td>Matched Transactions</td><td class='summary-value'>{summary['matched_count']}</td></tr>",
            f"<tr><td>Unmatched Bank Transactions</td><td class='summary-value'>{summary['unmatched_bank_count']}</td></tr>",
            f"<tr><td>Unmatched Internal Records</td><td class='summary-value'>{summary['unmatched_internal_count']}</td></tr>",
            f"<tr><td>Partial Matches</td><td class='summary-value'>{summary['partial_matches_count']}</td></tr>",
            f"<tr><td>Match Rate</td><td class='summary-value'>{match_rate:.2f}%</td></tr>",
            f"<tr><td>Matched Amount Total</td><td class='summary-value'>₹{summary['matched_amount_total']:,.2f}</td></tr>",
            f"<tr><td>Unmatched Bank Amount Total</td><td class='summary-value'>₹{summary['unmatched_bank_amount_total']:,.2f}</td></tr>",
            f"<tr><td>Unmatched Internal Amount Total</td><td class='summary-value'>₹{summary['unmatched_internal_amount_total']:,.2f}</td></tr>",
            f"<tr><td>Partial Matches Amount Total</td><td class='summary-value'>₹{summary['partial_matches_amount_total']:,.2f}</td></tr>"
        ]
        
        # Add match type statistics if available
        if 'match_types' in summary and summary['match_types']:
            for match_type, stats in summary['match_types'].items():
                html.append(f"<tr><td>{match_type} Matches</td><td class='summary-value'>{stats['count']} ({stats['percentage']:.2f}%)</td></tr>")
        
        html.append("</table>")
        return html
    
    def _generate_html_matched_section(self, df):
        """Generate HTML for matched transactions section."""
        df_html = self._prepare_matched_transactions(df).to_html(index=False, classes='matched-table')
        
        # Add custom CSS classes based on match_type
        df_html = df_html.replace('<tr>', '<tr class="match-row">')
        
        # Add specific classes for different match types
        match_type_classes = {
            'EXACT': 'match-exact',
            'AMOUNT_MISMATCH': 'match-amount',
            'DATE_MISMATCH': 'match-date',
            'PARTIAL': 'match-partial'
        }
        
        for match_type, css_class in match_type_classes.items():
            df_html = df_html.replace(f">{match_type}<", f" class='{css_class}'>{match_type}<")
        
        return [
            "<h2>Matched Transactions</h2>",
            df_html
        ]
    
    def _generate_html_unmatched_bank_section(self, df):
        """Generate HTML for unmatched bank transactions section."""
        df_html = self._prepare_unmatched_bank_transactions(df).to_html(index=False)
        return [
            "<h2>Unmatched Bank Transactions</h2>",
            df_html
        ]
    
    def _generate_html_unmatched_internal_section(self, df):
        """Generate HTML for unmatched internal transactions section."""
        df_html = self._prepare_unmatched_internal_transactions(df).to_html(index=False)
        return [
            "<h2>Unmatched Internal Records</h2>",
            df_html
        ]
    
    def _generate_html_partial_matches_section(self, df):
        """Generate HTML for partial matches section."""
        df_html = self._prepare_matched_transactions(df).to_html(index=False)
        return [
            "<h2>Partial Matches</h2>",
            df_html
        ]
    
    def _generate_html_suggestions_section(self, suggestions_dict):
        """Generate HTML for match suggestions section."""
        df = self._prepare_match_suggestions(suggestions_dict)
        df_html = df.to_html(index=False)
        
        # Add colored score classes
        for score in range(0, 101, 5):
            score_str = f"{score:.2f}%"
            css_class = "good-score" if score >= 80 else "medium-score" if score >= 60 else "low-score"
            df_html = df_html.replace(f">{score_str}<", f" class='{css_class}'>{score_str}<")
        
        return [
            "<h2>Match Suggestions</h2>",
            df_html
        ]