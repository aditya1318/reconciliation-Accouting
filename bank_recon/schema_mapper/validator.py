"""
Data Validator module for schema-based validation.

This module validates data against schema-defined validation rules,
ensuring data integrity and conformity to expected formats.
"""

import pandas as pd
import numpy as np
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta


class DataValidator:
    """
    Validator for ensuring data conforms to schema requirements.
    
    Applies schema-defined validation rules to data, records validation
    results, and flags potential issues.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the data validator.
        
        Args:
            logger: Logger for recording validation operations.
        """
        self.logger = logger or logging.getLogger('data_validator')
        self.validation_results = []
        
        # Register built-in validation rules
        self.validation_rules = {
            'not_null': self._validate_not_null,
            'unique': self._validate_unique,
            'min_value': self._validate_min_value,
            'max_value': self._validate_max_value,
            'regex': self._validate_regex,
            'length': self._validate_length,
            'in_set': self._validate_in_set,
            'date_range': self._validate_date_range,
            'custom': self._validate_custom
        }
    
    def validate(self, data: pd.DataFrame, schema: dict) -> Tuple[bool, List[dict]]:
        """
        Validate data against schema validation rules.
        
        Args:
            data: Data to validate
            schema: Schema with validation rules
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        self.validation_results = []
        validation_rules = schema.get('validation_rules', [])
        
        if not validation_rules:
            self.logger.info("No validation rules found in schema")
            return True, []
        
        self.logger.info(f"Validating data with {len(validation_rules)} rules")
        
        # Apply each validation rule
        for rule_config in validation_rules:
            rule_type = rule_config.get('rule')
            if not rule_type:
                self.logger.warning("Rule type not specified in validation rule")
                continue
            
            if rule_type not in self.validation_rules:
                self.logger.warning(f"Unknown validation rule type: {rule_type}")
                continue
            
            # Apply the validation rule
            self._apply_validation_rule(data, rule_config)
        
        # Check if all validations passed
        is_valid = all(result['passed'] for result in self.validation_results)
        validation_errors = [result for result in self.validation_results if not result['passed']]
        
        self.logger.info(f"Validation complete. Passed: {is_valid}, Errors: {len(validation_errors)}")
        
        return is_valid, validation_errors
    
    def _apply_validation_rule(self, data: pd.DataFrame, rule_config: dict) -> None:
        """Apply a single validation rule to the data."""
        rule_type = rule_config.get('rule')
        field = rule_config.get('field')
        error_message = rule_config.get('error_message', f"Validation failed for rule: {rule_type}")
        
        # Custom rule doesn't require a field, it uses an expression
        if rule_type == 'custom':
            expression = rule_config.get('expression')
            if not expression:
                self.logger.warning("Custom rule missing expression")
                return
            
            # Apply custom rule
            result = self.validation_rules[rule_type](data, None, expression)
            
            # Record validation result
            self.validation_results.append({
                'rule': rule_type,
                'field': None,
                'expression': expression,
                'passed': bool(result),
                'error_message': error_message if not result else None,
                'timestamp': datetime.now().isoformat()
            })
            return
        
        # All other rules require a field
        if not field:
            self.logger.warning(f"Field not specified for validation rule: {rule_type}")
            return
        
        if field not in data.columns:
            self.logger.warning(f"Field '{field}' not found in data for validation rule: {rule_type}")
            return
        
        # Apply the validation rule
        result = self.validation_rules[rule_type](data, field, rule_config)
        
        # Record validation result
        self.validation_results.append({
            'rule': rule_type,
            'field': field,
            'passed': bool(result),
            'error_message': error_message if not result else None,
            'timestamp': datetime.now().isoformat()
        })
    
    # Validation rule implementations
    def _validate_not_null(self, data: pd.DataFrame, field: str, config: dict) -> bool:
        """Validate that field values are not null."""
        null_count = data[field].isna().sum()
        return null_count == 0
    
    def _validate_unique(self, data: pd.DataFrame, field: str, config: dict) -> bool:
        """Validate that field values are unique."""
        # Drop NA values for uniqueness check
        non_null_values = data[field].dropna()
        return len(non_null_values) == len(non_null_values.unique())
    
    def _validate_min_value(self, data: pd.DataFrame, field: str, config: dict) -> bool:
        """Validate that field values are greater than or equal to a minimum value."""
        min_value = config.get('value')
        if min_value is None:
            self.logger.warning("No minimum value specified for min_value rule")
            return False
        
        # Convert to numeric for comparison
        try:
            numeric_values = pd.to_numeric(data[field], errors='coerce')
            return (numeric_values >= min_value).all() or numeric_values.isna().all()
        except:
            self.logger.warning(f"Failed to convert {field} to numeric for min_value validation")
            return False
    
    def _validate_max_value(self, data: pd.DataFrame, field: str, config: dict) -> bool:
        """Validate that field values are less than or equal to a maximum value."""
        max_value = config.get('value')
        if max_value is None:
            self.logger.warning("No maximum value specified for max_value rule")
            return False
        
        # Convert to numeric for comparison
        try:
            numeric_values = pd.to_numeric(data[field], errors='coerce')
            return (numeric_values <= max_value).all() or numeric_values.isna().all()
        except:
            self.logger.warning(f"Failed to convert {field} to numeric for max_value validation")
            return False
    
    def _validate_regex(self, data: pd.DataFrame, field: str, config: dict) -> bool:
        """Validate that field values match a regular expression pattern."""
        pattern = config.get('pattern')
        if not pattern:
            self.logger.warning("No pattern specified for regex rule")
            return False
        
        # Check if all non-null values match the pattern
        try:
            matches = data[field].fillna('').str.match(pattern)
            return matches.all()
        except:
            self.logger.warning(f"Failed to apply regex pattern to {field}")
            return False
    
    def _validate_length(self, data: pd.DataFrame, field: str, config: dict) -> bool:
        """Validate that field values have length within specified range."""
        min_length = config.get('min')
        max_length = config.get('max')
        
        # Convert values to string and get lengths
        lengths = data[field].fillna('').astype(str).str.len()
        
        # Check minimum length if specified
        if min_length is not None:
            if (lengths < min_length).any():
                return False
        
        # Check maximum length if specified
        if max_length is not None:
            if (lengths > max_length).any():
                return False
        
        return True
    
    def _validate_in_set(self, data: pd.DataFrame, field: str, config: dict) -> bool:
        """Validate that field values are in a specified set of values."""
        valid_values = config.get('values', [])
        if not valid_values:
            self.logger.warning("No values specified for in_set rule")
            return False
        
        # Check if all non-null values are in the set
        non_null_values = data[field].dropna()
        return non_null_values.isin(valid_values).all()
    
    def _validate_date_range(self, data: pd.DataFrame, field: str, config: dict) -> bool:
        """Validate that date field values are within a specified range."""
        min_date = config.get('min_date')
        max_date = config.get('max_date')
        
        # Convert to datetime for comparison
        try:
            date_values = pd.to_datetime(data[field], errors='coerce')
            
            # Check minimum date if specified
            if min_date is not None:
                # Handle special case "today" with optional offset
                if isinstance(min_date, str) and min_date.startswith('today'):
                    today = pd.Timestamp.today().normalize()
                    offset_match = re.search(r'today([+-]\d+)', min_date)
                    if offset_match:
                        days = int(offset_match.group(1))
                        min_date_value = today + timedelta(days=days)
                    else:
                        min_date_value = today
                else:
                    min_date_value = pd.to_datetime(min_date)
                
                if (date_values < min_date_value).any():
                    return False
            
            # Check maximum date if specified
            if max_date is not None:
                # Handle special case "today" with optional offset
                if isinstance(max_date, str) and max_date.startswith('today'):
                    today = pd.Timestamp.today().normalize()
                    offset_match = re.search(r'today([+-]\d+)', max_date)
                    if offset_match:
                        days = int(offset_match.group(1))
                        max_date_value = today + timedelta(days=days)
                    else:
                        max_date_value = today
                else:
                    max_date_value = pd.to_datetime(max_date)
                
                if (date_values > max_date_value).any():
                    return False
            
            return True
            
        except:
            self.logger.warning(f"Failed to convert {field} to dates for date_range validation")
            return False
    
    def _validate_custom(self, data: pd.DataFrame, field: str, expression: str) -> bool:
        """Validate using a custom expression."""
        if not expression:
            return False
        
        try:
            # Create a safe namespace with allowed functions
            namespace = {
                'df': data,
                'np': np,
                'pd': pd,
                'is_null': lambda x: pd.isna(x),
                'not_null': lambda x: ~pd.isna(x),
                'len': len,
                'min': min,
                'max': max,
                'sum': sum,
                'any': any,
                'all': all
            }
            
            # Evaluate the expression
            result = eval(expression, namespace)
            
            # Handle different result types
            if isinstance(result, pd.Series):
                return result.all()
            elif isinstance(result, np.ndarray):
                return result.all()
            else:
                return bool(result)
                
        except Exception as e:
            self.logger.error(f"Error evaluating custom validation expression: {e}")
            return False