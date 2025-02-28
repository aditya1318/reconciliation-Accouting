"""
Audit Logger module for tracking schema transformations.

This module provides a comprehensive audit trail for data transformations,
ensuring compliance and traceability of the reconciliation process.
"""

import os
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


class AuditLogger:
    """
    Logger for maintaining audit trails of schema transformations.
    
    Records detailed logs of all transformations, validations, and data changes
    for compliance and debugging purposes.
    """
    
    def __init__(self, 
                audit_dir: Optional[str] = None, 
                enabled: bool = True,
                logger: Optional[logging.Logger] = None):
        """
        Initialize the audit logger.
        
        Args:
            audit_dir: Directory for storing audit logs.
                If None, uses default directory.
            enabled: Whether audit logging is enabled.
            logger: Logger for recording audit operations.
        """
        self.logger = logger or logging.getLogger('audit_logger')
        self.enabled = enabled
        
        if audit_dir is None:
            # Default audit path relative to this file
            current_dir = Path(__file__).parent.parent.parent
            self.audit_dir = current_dir / 'logs' / 'audit'
        else:
            self.audit_dir = Path(audit_dir)
        
        # Create audit directory if it doesn't exist
        if enabled and not self.audit_dir.exists():
            os.makedirs(self.audit_dir, exist_ok=True)
            self.logger.info(f"Created audit directory: {self.audit_dir}")
        
        # Initialize audit record
        self.current_audit = self._create_empty_audit()
    
    def start_audit(self, process_name: str, source_info: Dict[str, Any]) -> None:
        """
        Start a new audit record.
        
        Args:
            process_name: Name of the process being audited
            source_info: Information about the source data
        """
        if not self.enabled:
            return
        
        # Create a new audit record
        self.current_audit = self._create_empty_audit()
        self.current_audit['process_name'] = process_name
        self.current_audit['start_time'] = datetime.now().isoformat()
        self.current_audit['source_info'] = source_info
        
        self.logger.info(f"Started audit for process: {process_name}")
    
    def record_schema_application(self, schema_info: Dict[str, Any]) -> None:
        """
        Record information about the schema being applied.
        
        Args:
            schema_info: Information about the schema
        """
        if not self.enabled:
            return
        
        self.current_audit['schema_info'] = schema_info
        self.logger.info(f"Recorded schema application: {schema_info.get('id', 'unknown')}")
    
    def record_transformation(self, transform_details: Dict[str, Any]) -> None:
        """
        Record a data transformation.
        
        Args:
            transform_details: Details of the transformation
        """
        if not self.enabled:
            return
        
        # Add timestamp if not already present
        if 'timestamp' not in transform_details:
            transform_details['timestamp'] = datetime.now().isoformat()
        
        self.current_audit['transformations'].append(transform_details)
        self.logger.debug(f"Recorded transformation: {transform_details.get('field', 'unknown')}")
    
    def record_validation(self, validation_results: List[Dict[str, Any]]) -> None:
        """
        Record validation results.
        
        Args:
            validation_results: Results of data validation
        """
        if not self.enabled:
            return
        
        self.current_audit['validations'].extend(validation_results)
        
        # Count failures
        failures = sum(1 for result in validation_results if not result.get('passed', True))
        self.logger.info(f"Recorded {len(validation_results)} validations with {failures} failures")
    
    def record_data_snapshot(self, stage: str, data_sample: Any, 
                           row_count: int, column_names: List[str]) -> None:
        """
        Record a snapshot of the data at a specific stage.
        
        Args:
            stage: Processing stage name
            data_sample: Sample of the data (typically first few rows)
            row_count: Total number of rows in the data
            column_names: Names of columns in the data
        """
        if not self.enabled:
            return
        
        # Convert data sample to serializable format if needed
        if isinstance(data_sample, pd.DataFrame):
            sample_dict = data_sample.head(5).to_dict(orient='records')
        elif isinstance(data_sample, pd.Series):
            sample_dict = data_sample.head(5).to_dict()
        else:
            sample_dict = data_sample
        
        snapshot = {
            'stage': stage,
            'timestamp': datetime.now().isoformat(),
            'row_count': row_count,
            'column_names': column_names,
            'data_sample': sample_dict
        }
        
        self.current_audit['data_snapshots'].append(snapshot)
        self.logger.debug(f"Recorded data snapshot for stage: {stage}")
    
    def record_error(self, error_message: str, error_details: Dict[str, Any]) -> None:
        """
        Record an error that occurred during processing.
        
        Args:
            error_message: Error message
            error_details: Additional error details
        """
        if not self.enabled:
            return
        
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'message': error_message,
            'details': error_details
        }
        
        self.current_audit['errors'].append(error_record)
        self.logger.warning(f"Recorded error: {error_message}")
    
    def complete_audit(self, status: str, result_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Complete the current audit and save it to file.
        
        Args:
            status: Final status of the process ('success', 'error', etc.)
            result_info: Information about the result
            
        Returns:
            Path to the saved audit file
        """
        if not self.enabled:
            return ""
        
        # Update audit record
        self.current_audit['end_time'] = datetime.now().isoformat()
        self.current_audit['status'] = status
        
        if result_info:
            self.current_audit['result_info'] = result_info
        
        # Calculate duration
        try:
            start_time = datetime.fromisoformat(self.current_audit['start_time'])
            end_time = datetime.fromisoformat(self.current_audit['end_time'])
            duration_seconds = (end_time - start_time).total_seconds()
            self.current_audit['duration_seconds'] = duration_seconds
        except (ValueError, KeyError):
            self.current_audit['duration_seconds'] = None
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        process_name = self.current_audit.get('process_name', 'unknown')
        filename = f"{process_name}_{timestamp}_{status}.json"
        file_path = self.audit_dir / filename
        
        # Save audit record to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_audit, f, indent=2, default=str)
            
            self.logger.info(f"Saved audit to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save audit file: {e}")
            return ""
    
    def bulk_record_transformations(self, transformations: List[Dict[str, Any]]) -> None:
        """
        Record multiple transformations at once.
        
        Args:
            transformations: List of transformation details
        """
        if not self.enabled:
            return
        
        for transform in transformations:
            self.record_transformation(transform)
    
    def _create_empty_audit(self) -> Dict[str, Any]:
        """Create an empty audit record structure."""
        return {
            'process_name': '',
            'start_time': None,
            'end_time': None,
            'duration_seconds': None,
            'status': 'in_progress',
            'source_info': {},
            'schema_info': {},
            'transformations': [],
            'validations': [],
            'data_snapshots': [],
            'errors': [],
            'result_info': {}
        }
    
    def get_audit_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current audit.
        
        Returns:
            Audit summary dictionary
        """
        if not self.enabled:
            return {}
        
        # Create a summary with key information
        summary = {
            'process_name': self.current_audit.get('process_name', ''),
            'start_time': self.current_audit.get('start_time'),
            'status': self.current_audit.get('status', 'in_progress'),
            'transformation_count': len(self.current_audit.get('transformations', [])),
            'validation_count': len(self.current_audit.get('validations', [])),
            'error_count': len(self.current_audit.get('errors', [])),
            'schema_id': self.current_audit.get('schema_info', {}).get('id', 'unknown')
        }
        
        # Count validation failures
        validation_failures = sum(
            1 for v in self.current_audit.get('validations', []) 
            if not v.get('passed', True)
        )
        summary['validation_failures'] = validation_failures
        
        return summary