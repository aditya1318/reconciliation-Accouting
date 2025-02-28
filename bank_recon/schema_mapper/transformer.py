"""
Data Transformer module for mapping between schemas.

This module applies schema-defined transformations to convert data 
from source formats to the standardized internal format required for reconciliation.
"""

import os
import pandas as pd
import numpy as np
import re
import logging
import importlib.util
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import tempfile


class DataTransformer:
    """
    Transformer for applying schema mappings to data.
    
    Maps source data to standardized formats according to schema-defined
    rules, executes transformations, and generates derived fields.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the data transformer.
        
        Args:
            logger: Logger for recording transformation operations.
        """
        self.logger = logger or logging.getLogger('data_transformer')
        self.transformation_history = []
        
        # Built-in transformations
        self.builtin_transforms = {
            'clean_amount': self._clean_amount,
            'clean_description': self._clean_description,
            'date_transform': self._date_transform,
            'extract_payment_method': self._extract_payment_method,
            'extract_reference_id': self._extract_reference_id,
            'extract_ifsc_code': self._extract_ifsc_code,
            'check_for_gst': self._check_for_gst,
            'check_for_tds': self._check_for_tds,
            'extract_gst_amount': self._extract_gst_amount,
            'extract_tds_amount': self._extract_tds_amount
        }
        
        # Cache for compiled custom transformers
        self._custom_transform_cache = {}
    
    def transform(self, data: pd.DataFrame, schema: dict, 
                 transform_scripts: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """
        Transform data according to the schema configuration.
        
        Args:
            data: Source data to transform
            schema: Schema configuration defining the transformations
            transform_scripts: Optional dictionary of custom transform scripts
            
        Returns:
            Transformed DataFrame in standardized format
        """
        self.logger.info(f"Starting transformation with schema: {schema.get('id', 'unknown')}")
        self.transformation_history = []
        
        # Track original columns for audit
        original_columns = list(data.columns)
        
        # Apply field mappings
        result_df = self._apply_field_mappings(data, schema)
        
        # Apply derived fields
        result_df = self._apply_derived_fields(result_df, schema, transform_scripts)
        
        # Apply computed fields
        result_df = self._apply_computed_fields(result_df, schema)
        
        # Log transformation summary
        self.logger.info(f"Transformation complete. Original columns: {len(original_columns)}, "
                        f"Result columns: {len(result_df.columns)}")
        
        return result_df
    
    def _apply_field_mappings(self, data: pd.DataFrame, schema: dict) -> pd.DataFrame:
        """Apply field mappings from source to target schema."""
        field_mappings = schema.get('field_mappings', {})
        if not field_mappings:
            self.logger.warning("No field mappings found in schema")
            return data.copy()
        
        # Create empty result DataFrame with standardized column names
        result_df = pd.DataFrame()
        
        # Process each field mapping
        for target_field, mapping in field_mappings.items():
            source_field = mapping.get('source')
            if not source_field or source_field not in data.columns:
                # Skip if source field is not found
                if mapping.get('required', False):
                    self.logger.warning(f"Required field '{source_field}' not found in source data")
                continue
            
            # Copy the data
            result_df[target_field] = data[source_field].copy()
            
            # Apply type conversion if specified
            field_type = mapping.get('type')
            if field_type:
                result_df[target_field] = self._convert_type(
                    result_df[target_field], 
                    field_type, 
                    mapping.get('format'),
                    target_field
                )
            
            # Apply transformation if specified
            transform = mapping.get('transform')
            if transform:
                original_values = result_df[target_field].copy()
                result_df[target_field] = self._apply_transformation(
                    result_df, target_field, transform, None
                )
                
                # Record transformation for audit
                self._record_transformation(
                    field=target_field,
                    transform=transform,
                    samples_before=original_values.head(3).tolist(),
                    samples_after=result_df[target_field].head(3).tolist()
                )
        
        return result_df
    
    def _apply_derived_fields(self, data: pd.DataFrame, schema: dict, 
                             transform_scripts: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """Apply derived fields based on transformations."""
        derived_fields = schema.get('derived_fields', {})
        if not derived_fields:
            return data
        
        result_df = data.copy()
        
        # Process each derived field
        for target_field, config in derived_fields.items():
            transform = config.get('transform')
            source_fields = config.get('source')
            
            if not transform:
                self.logger.warning(f"No transform specified for derived field: {target_field}")
                continue
            
            # Initialize field with default value if specified
            if 'default' in config:
                result_df[target_field] = config['default']
            
            # Apply transformation
            original_values = result_df[target_field].copy() if target_field in result_df else pd.Series([None] * len(result_df))
            result_df[target_field] = self._apply_transformation(
                result_df, target_field, transform, transform_scripts, source_fields
            )
            
            # Apply type conversion if specified
            field_type = config.get('type')
            if field_type:
                result_df[target_field] = self._convert_type(
                    result_df[target_field], 
                    field_type,
                    None,
                    target_field
                )
            
            # Record transformation for audit
            if transform:
                self._record_transformation(
                    field=target_field,
                    transform=transform,
                    samples_before=original_values.head(3).tolist(),
                    samples_after=result_df[target_field].head(3).tolist()
                )
        
        return result_df
    
    def _apply_computed_fields(self, data: pd.DataFrame, schema: dict) -> pd.DataFrame:
        """Apply computed fields based on expressions."""
        computed_fields = schema.get('computed_fields', {})
        if not computed_fields:
            return data
        
        result_df = data.copy()
        
        # Process each computed field
        for target_field, config in computed_fields.items():
            expression = config.get('expression')
            
            if not expression:
                self.logger.warning(f"No expression specified for computed field: {target_field}")
                continue
            
            # Apply the expression
            original_values = result_df[target_field].copy() if target_field in result_df else pd.Series([None] * len(result_df))
            
            try:
                # Replace field references with dataframe column references
                expr = self._prepare_expression(expression, result_df.columns)
                
                # Evaluate the expression
                result = eval(expr, {'df': result_df, 'np': np, 'pd': pd,
                                    'get_fiscal_quarter': self._get_fiscal_quarter})
                
                # Assign the result
                result_df[target_field] = result
                
                # Apply type conversion if specified
                field_type = config.get('type')
                if field_type:
                    result_df[target_field] = self._convert_type(
                        result_df[target_field], 
                        field_type,
                        None,
                        target_field
                    )
                
                # Record transformation for audit
                self._record_transformation(
                    field=target_field,
                    transform=f"expression: {expression}",
                    samples_before=original_values.head(3).tolist(),
                    samples_after=result_df[target_field].head(3).tolist()
                )
                
            except Exception as e:
                self.logger.error(f"Error evaluating expression for {target_field}: {e}")
                # Leave the field as is or set to None
                result_df[target_field] = None
        
        return result_df
    
    def _apply_transformation(self, data: pd.DataFrame, target_field: str, 
                             transform_name: str, transform_scripts: Optional[Dict[str, str]], 
                             source_fields: Optional[Union[str, List[str]]] = None) -> pd.Series:
        """Apply a specific transformation to the data."""
        # Handle builtin transformations
        if transform_name in self.builtin_transforms:
            transform_func = self.builtin_transforms[transform_name]
            
            # Simple case: transform single column
            if source_fields is None:
                if target_field in data.columns:
                    # Transform existing column
                    return data.apply(lambda row: transform_func(row[target_field]), axis=1)
                else:
                    self.logger.warning(f"Target field {target_field} not found for transformation")
                    return pd.Series([None] * len(data))
            
            # Handle multiple source fields
            elif isinstance(source_fields, list):
                # Check if all source fields exist
                if not all(field in data.columns for field in source_fields):
                    missing = [f for f in source_fields if f not in data.columns]
                    self.logger.warning(f"Source fields missing for {transform_name}: {missing}")
                    return pd.Series([None] * len(data))
                
                # Apply transformation with multiple fields
                return data.apply(
                    lambda row: transform_func(*[row[field] for field in source_fields]), 
                    axis=1
                )
            
            # Handle single source field
            elif isinstance(source_fields, str):
                if source_fields not in data.columns:
                    self.logger.warning(f"Source field {source_fields} not found for transformation")
                    return pd.Series([None] * len(data))
                
                # Apply transformation with single source field
                return data.apply(lambda row: transform_func(row[source_fields]), axis=1)
        
        # Handle custom transformations from schema
        elif transform_scripts and transform_name in transform_scripts:
            # Compile the transformer if not already in cache
            if transform_name not in self._custom_transform_cache:
                script = transform_scripts[transform_name]
                transformer = self._compile_custom_transformer(script)
                self._custom_transform_cache[transform_name] = transformer
            else:
                transformer = self._custom_transform_cache[transform_name]
            
            # Similar logic as above but with the custom transformer
            if source_fields is None:
                if target_field in data.columns:
                    return data.apply(lambda row: transformer(row[target_field], row), axis=1)
                else:
                    return pd.Series([None] * len(data))
            elif isinstance(source_fields, list):
                if not all(field in data.columns for field in source_fields):
                    missing = [f for f in source_fields if f not in data.columns]
                    self.logger.warning(f"Source fields missing for {transform_name}: {missing}")
                    return pd.Series([None] * len(data))
                return data.apply(
                    lambda row: transformer(*[row[field] for field in source_fields], row), 
                    axis=1
                )
            elif isinstance(source_fields, str):
                if source_fields not in data.columns:
                    self.logger.warning(f"Source field {source_fields} not found for transformation")
                    return pd.Series([None] * len(data))
                return data.apply(lambda row: transformer(row[source_fields], row), axis=1)
        
        else:
            self.logger.warning(f"Unknown transformation: {transform_name}")
            if target_field in data.columns:
                return data[target_field]
            else:
                return pd.Series([None] * len(data))
    
    def _compile_custom_transformer(self, script: str) -> Callable:
        """Compile a custom transformer from script."""
        # Create a temporary module
        try:
            # Write script to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp:
                temp_path = temp.name
                temp.write(script.encode('utf-8'))
            
            # Load the module
            spec = importlib.util.spec_from_file_location("custom_transform", temp_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get the transform function
            if hasattr(module, 'transform'):
                return module.transform
            else:
                self.logger.error("Custom transform script missing 'transform' function")
                return lambda *args, **kwargs: None
                
        except Exception as e:
            self.logger.error(f"Error compiling custom transformer: {e}")
            return lambda *args, **kwargs: None
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _convert_type(self, series: pd.Series, type_name: str, 
                     format_str: Optional[str], field_name: str) -> pd.Series:
        """Convert series to the specified type."""
        try:
            if type_name == 'date':
                if format_str:
                    return pd.to_datetime(series, format=format_str, errors='coerce')
                else:
                    return pd.to_datetime(series, errors='coerce')
            
            elif type_name == 'datetime':
                if format_str:
                    return pd.to_datetime(series, format=format_str, errors='coerce')
                else:
                    return pd.to_datetime(series, errors='coerce')
            
            elif type_name == 'decimal' or type_name == 'float':
                return pd.to_numeric(series, errors='coerce')
            
            elif type_name == 'integer' or type_name == 'int':
                return pd.to_numeric(series, errors='coerce').astype('Int64')
            
            elif type_name == 'string' or type_name == 'str':
                return series.astype(str)
            
            elif type_name == 'boolean' or type_name == 'bool':
                # Handle various boolean representations
                return series.map(lambda x: str(x).lower() in ('true', 't', 'yes', 'y', '1'))
            
            else:
                self.logger.warning(f"Unknown type '{type_name}' for field '{field_name}'")
                return series
                
        except Exception as e:
            self.logger.error(f"Error converting field '{field_name}' to '{type_name}': {e}")
            return series
    
    def _prepare_expression(self, expression: str, columns: pd.Index) -> str:
        """Prepare an expression for evaluation by replacing field references."""
        # Replace field references with dataframe column references
        for col in columns:
            # Replace full word matches on column names with df[] references
            expression = re.sub(r'\b' + col + r'\b', f'df["{col}"]', expression)
        
        return expression
    
    def _record_transformation(self, field: str, transform: str, 
                             samples_before: List, samples_after: List) -> None:
        """Record a transformation for audit purposes."""
        self.transformation_history.append({
            'timestamp': datetime.now().isoformat(),
            'field': field,
            'transform': transform,
            'samples_before': samples_before,
            'samples_after': samples_after
        })
    
    # Built-in transformations
    def _clean_amount(self, value: Any) -> float:
        """Clean amount values by removing currency symbols, commas, etc."""
        if pd.isna(value):
            return None
        
        if not isinstance(value, str):
            return float(value)
        
        # Remove currency symbols, commas, and convert to float
        value = str(value)
        value = value.replace('₹', '').replace('Rs.', '').replace('INR', '')
        value = value.replace(',', '').replace(' ', '')
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _clean_description(self, value: Any) -> str:
        """Normalize description text."""
        if pd.isna(value):
            return ""
        
        value = str(value)
        
        # Convert to uppercase
        value = value.upper()
        
        # Replace multiple spaces with a single space
        value = re.sub(r'\s+', ' ', value).strip()
        
        # Remove common prefixes
        prefixes = ["TRANSACTION DETAILS:", "NARRATION:", "DESCRIPTION:", "PARTICULARS:"]
        for prefix in prefixes:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()
        
        return value
    
    def _date_transform(self, value: Any, format_str: Optional[str] = None) -> datetime:
        """Transform date values to standard format."""
        if pd.isna(value):
            return None
        
        try:
            if format_str:
                return pd.to_datetime(value, format=format_str)
            else:
                return pd.to_datetime(value)
        except (ValueError, TypeError):
            return None
    
    def _extract_payment_method(self, desc: str) -> str:
        """Extract payment method from description."""
        if pd.isna(desc):
            return ""
        
        desc = str(desc)
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
    
    def _extract_reference_id(self, desc: str) -> str:
        """Extract reference ID from description."""
        if pd.isna(desc):
            return ""
        
        desc = str(desc)
        # UPI reference pattern
        upi_match = re.search(r'UPI[/:\s][A-Z]*(\d{9,})', desc)
        if upi_match:
            return upi_match.group(1)
        
        # IMPS reference pattern
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
    
    def _extract_ifsc_code(self, desc: str) -> str:
        """Extract IFSC code from description."""
        if pd.isna(desc):
            return ""
        
        desc = str(desc)
        ifsc_match = re.search(r'[A-Z]{4}0[A-Z0-9]{6}', desc)
        if ifsc_match:
            return ifsc_match.group(0)
        
        return ""
    
    def _check_for_gst(self, desc: str) -> bool:
        """Check if description mentions GST."""
        if pd.isna(desc):
            return False
        
        desc = str(desc)
        gst_patterns = [r'GST', r'CGST', r'SGST', r'IGST', r'GSTIN']
        for pattern in gst_patterns:
            if re.search(pattern, desc):
                return True
        
        return False
    
    def _check_for_tds(self, desc: str) -> bool:
        """Check if description mentions TDS."""
        if pd.isna(desc):
            return False
        
        desc = str(desc)
        return bool(re.search(r'TDS', desc))
    
    def _extract_gst_amount(self, desc: str, amount: float) -> float:
        """Extract GST amount from description and amount."""
        if pd.isna(desc) or pd.isna(amount):
            return 0.0
        
        desc = str(desc)
        amount = float(amount)
        
        # Look for explicit GST amount
        gst_amount_match = re.search(r'GST[:\s]*([\d,.]+)', desc)
        if gst_amount_match:
            try:
                return float(gst_amount_match.group(1).replace(',', ''))
            except (ValueError, TypeError):
                pass
        
        # Assume standard GST rate of 18% if GST is mentioned
        if self._check_for_gst(desc):
            return round(amount * 0.18 / 1.18, 2)  # GST component of total
        
        return 0.0
    
    def _extract_tds_amount(self, desc: str, amount: float) -> float:
        """Extract TDS amount from description and amount."""
        if pd.isna(desc) or pd.isna(amount):
            return 0.0
        
        desc = str(desc)
        amount = float(amount)
        
        # Look for explicit TDS amount
        tds_amount_match = re.search(r'TDS[:\s]*([\d,.]+)', desc)
        if tds_amount_match:
            try:
                return float(tds_amount_match.group(1).replace(',', ''))
            except (ValueError, TypeError):
                pass
        
        # Assume standard TDS rate of 10% if TDS is mentioned
        if self._check_for_tds(desc):
            return round(amount * 0.1, 2)
        
        return 0.0
    
    def _get_fiscal_quarter(self, date_series: pd.Series) -> pd.Series:
        """
        Helper function to get the fiscal quarter from a date.
        Assumes Indian fiscal year (April-March).
        """
        if isinstance(date_series, pd.Series):
            return date_series.apply(self._get_single_fiscal_quarter)
        else:
            return self._get_single_fiscal_quarter(date_series)
    
    def _get_single_fiscal_quarter(self, date_val: Any) -> str:
        """Get fiscal quarter for a single date value."""
        if pd.isna(date_val):
            return ""
        
        try:
            date = pd.to_datetime(date_val)
            month = date.month
            year = date.year
            
            # Indian fiscal year starts in April
            if month < 4:  # Jan-Mar
                fiscal_year = f"{year-1}-{year}"
                quarter = 4
            elif month < 7:  # Apr-Jun
                fiscal_year = f"{year}-{year+1}"
                quarter = 1
            elif month < 10:  # Jul-Sep
                fiscal_year = f"{year}-{year+1}"
                quarter = 2
            else:  # Oct-Dec
                fiscal_year = f"{year}-{year+1}"
                quarter = 3
            
            return f"Q{quarter} {fiscal_year}"
            
        except (ValueError, TypeError):
            return ""