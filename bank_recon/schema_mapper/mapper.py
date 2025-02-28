"""
Schema Mapper main module for reconciliation system.

This module provides a unified interface for the schema mapping framework,
coordinating the registration, loading, transformation, validation, and auditing
of heterogeneous financial data sources.
"""

import os
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

from .registry import SchemaRegistry
from .loader import SchemaLoader
from .transformer import DataTransformer
from .validator import DataValidator
from .audit import AuditLogger


class SchemaMapper:
    """
    Main class for schema mapping operations.
    
    Provides a unified interface for registering schemas, loading data,
    applying transformations, validating data, and maintaining audit trails.
    """
    
    def __init__(self, 
                config_dir: Optional[str] = None,
                audit_enabled: bool = True,
                audit_dir: Optional[str] = None,
                logger: Optional[logging.Logger] = None):
        """
        Initialize the schema mapper.
        
        Args:
            config_dir: Directory containing schema configuration files.
                If None, uses default config directory.
            audit_enabled: Whether to enable audit logging.
            audit_dir: Directory for storing audit logs.
                If None, uses default audit directory.
            logger: Logger for recording operations.
        """
        self.logger = logger or logging.getLogger('schema_mapper')
        
        # Initialize components
        self.registry = SchemaRegistry(config_dir=config_dir, logger=self.logger)
        self.loader = SchemaLoader(logger=self.logger)
        self.transformer = DataTransformer(logger=self.logger)
        self.validator = DataValidator(logger=self.logger)
        self.audit = AuditLogger(
            audit_dir=audit_dir,
            enabled=audit_enabled,
            logger=self.logger
        )
        
        self.logger.info("Schema mapper initialized")
    
    def process_bank_statement(self, 
                              file_path: str, 
                              schema_id: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Process a bank statement file according to the specified schema.
        
        Args:
            file_path: Path to the bank statement file.
            schema_id: ID of the bank schema to use.
                If None, will attempt to auto-detect.
                
        Returns:
            Tuple of (transformed_data, process_info)
            
        Raises:
            ValueError: If schema cannot be found or file processing fails.
        """
        # Start audit
        self.audit.start_audit(
            process_name="bank_statement_processing",
            source_info={"file_path": file_path, "schema_id": schema_id}
        )
        
        try:
            # Get schema
            if schema_id:
                schema = self.registry.get_bank_schema(schema_id)
                if not schema:
                    raise ValueError(f"Bank schema not found: {schema_id}")
            else:
                # TODO: Implement auto-detection
                # For now, we'll load the data and try to detect the schema
                temp_df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                detected_schema_id = self.registry.detect_schema(temp_df, schema_type='bank')
                if not detected_schema_id:
                    raise ValueError("Could not auto-detect bank schema")
                
                schema_id = detected_schema_id
                schema = self.registry.get_bank_schema(schema_id)
            
            # Record schema application
            self.audit.record_schema_application({
                "id": schema_id,
                "name": schema.get('name', schema_id),
                "version": schema.get('version', '1.0.0'),
                "type": "bank"
            })
            
            # Load data according to schema
            data, metadata = self.loader.load_data(file_path, schema)
            
            # Record data snapshot
            self.audit.record_data_snapshot(
                stage="loaded",
                data_sample=data.head(5),
                row_count=len(data),
                column_names=list(data.columns)
            )
            
            # Transform data according to schema
            transformed_data = self.transformer.transform(
                data, 
                schema,
                transform_scripts=self._get_transformation_scripts(schema)
            )
            
            # Record transformation history
            self.audit.bulk_record_transformations(self.transformer.transformation_history)
            
            # Record transformed data snapshot
            self.audit.record_data_snapshot(
                stage="transformed",
                data_sample=transformed_data.head(5),
                row_count=len(transformed_data),
                column_names=list(transformed_data.columns)
            )
            
            # Validate data according to schema
            is_valid, validation_errors = self.validator.validate(transformed_data, schema)
            
            # Record validation results
            self.audit.record_validation(self.validator.validation_results)
            
            # Complete audit
            process_info = {
                "schema_id": schema_id,
                "file_path": file_path,
                "rows_processed": len(data),
                "rows_transformed": len(transformed_data),
                "is_valid": is_valid,
                "validation_errors": len(validation_errors),
                "metadata": metadata
            }
            
            self.audit.complete_audit(
                status="success" if is_valid else "warning",
                result_info=process_info
            )
            
            return transformed_data, process_info
            
        except Exception as e:
            self.logger.error(f"Error processing bank statement: {e}")
            
            # Record error and complete audit
            self.audit.record_error(
                error_message=str(e),
                error_details={"exception_type": type(e).__name__}
            )
            
            self.audit.complete_audit(
                status="error",
                result_info={"error": str(e)}
            )
            
            raise ValueError(f"Failed to process bank statement: {e}")
    
    def process_internal_records(self, 
                               file_path: str, 
                               schema_id: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Process an internal records file according to the specified schema.
        
        Args:
            file_path: Path to the internal records file.
            schema_id: ID of the internal schema to use.
                If None, will attempt to auto-detect.
                
        Returns:
            Tuple of (transformed_data, process_info)
            
        Raises:
            ValueError: If schema cannot be found or file processing fails.
        """
        # Start audit
        self.audit.start_audit(
            process_name="internal_records_processing",
            source_info={"file_path": file_path, "schema_id": schema_id}
        )
        
        try:
            # Get schema
            if schema_id:
                schema = self.registry.get_internal_schema(schema_id)
                if not schema:
                    raise ValueError(f"Internal schema not found: {schema_id}")
            else:
                # TODO: Implement auto-detection
                # For now, we'll load the data and try to detect the schema
                temp_df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
                detected_schema_id = self.registry.detect_schema(temp_df, schema_type='internal')
                if not detected_schema_id:
                    raise ValueError("Could not auto-detect internal schema")
                
                schema_id = detected_schema_id
                schema = self.registry.get_internal_schema(schema_id)
            
            # Record schema application
            self.audit.record_schema_application({
                "id": schema_id,
                "name": schema.get('name', schema_id),
                "version": schema.get('version', '1.0.0'),
                "type": "internal"
            })
            
            # Load data according to schema
            data, metadata = self.loader.load_data(file_path, schema)
            
            # Record data snapshot
            self.audit.record_data_snapshot(
                stage="loaded",
                data_sample=data.head(5),
                row_count=len(data),
                column_names=list(data.columns)
            )
            
            # Transform data according to schema
            transformed_data = self.transformer.transform(
                data, 
                schema,
                transform_scripts=self._get_transformation_scripts(schema)
            )
            
            # Record transformation history
            self.audit.bulk_record_transformations(self.transformer.transformation_history)
            
            # Record transformed data snapshot
            self.audit.record_data_snapshot(
                stage="transformed",
                data_sample=transformed_data.head(5),
                row_count=len(transformed_data),
                column_names=list(transformed_data.columns)
            )
            
            # Validate data according to schema
            is_valid, validation_errors = self.validator.validate(transformed_data, schema)
            
            # Record validation results
            self.audit.record_validation(self.validator.validation_results)
            
            # Complete audit
            process_info = {
                "schema_id": schema_id,
                "file_path": file_path,
                "rows_processed": len(data),
                "rows_transformed": len(transformed_data),
                "is_valid": is_valid,
                "validation_errors": len(validation_errors),
                "metadata": metadata
            }
            
            self.audit.complete_audit(
                status="success" if is_valid else "warning",
                result_info=process_info
            )
            
            return transformed_data, process_info
            
        except Exception as e:
            self.logger.error(f"Error processing internal records: {e}")
            
            # Record error and complete audit
            self.audit.record_error(
                error_message=str(e),
                error_details={"exception_type": type(e).__name__}
            )
            
            self.audit.complete_audit(
                status="error",
                result_info={"error": str(e)}
            )
            
            raise ValueError(f"Failed to process internal records: {e}")
    
    def list_available_schemas(self) -> Dict[str, List[Dict[str, str]]]:
        """
        List all available schemas.
        
        Returns:
            Dictionary of schema types to lists of schema information.
        """
        return {
            "bank": self.registry.list_bank_schemas(),
            "internal": self.registry.list_internal_schemas()
        }
    
    def refresh_schemas(self) -> None:
        """Refresh schema registry from disk."""
        self.registry.refresh()
        self.logger.info("Schema registry refreshed")
    
    def get_audit_summary(self) -> Dict[str, Any]:
        """Get summary of the most recent audit."""
        return self.audit.get_audit_summary()
    
    def _get_transformation_scripts(self, schema: dict) -> Dict[str, str]:
        """Get custom transformation scripts for a schema."""
        transformations = schema.get('transformations', {})
        scripts = {}
        
        for name, details in transformations.items():
            if 'script' in details:
                scripts[name] = details['script']
        
        return scripts