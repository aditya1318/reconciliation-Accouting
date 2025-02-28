"""
Schema Registry module for managing and retrieving schema definitions.

This module provides a central registry for all schema configurations,
enabling discovery, loading, and management of schema mappings.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class SchemaRegistry:
    """
    Central registry for schema configurations.
    
    Manages loading, caching, and retrieving schema definitions from
    config files, allowing schema discovery and auto-detection.
    """
    
    def __init__(self, config_dir: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the schema registry.
        
        Args:
            config_dir: Directory containing schema configuration files.
                If None, uses default config directory.
            logger: Logger for recording registry operations.
        """
        self.logger = logger or logging.getLogger('schema_registry')
        
        if config_dir is None:
            # Default config path relative to this file
            current_dir = Path(__file__).parent.parent.parent
            self.config_dir = current_dir / 'config' / 'schema_mappings'
        else:
            self.config_dir = Path(config_dir)
        
        # Initialize caches
        self._bank_schemas: Dict[str, dict] = {}
        self._internal_schemas: Dict[str, dict] = {}
        self._transformer_scripts: Dict[str, dict] = {}
        
        # Load all schemas
        self.refresh()
    
    def refresh(self) -> None:
        """Reload all schema configurations from disk."""
        self.logger.info("Refreshing schema registry")
        self._load_bank_schemas()
        self._load_internal_schemas()
        self._load_transformer_scripts()
    
    def _load_bank_schemas(self) -> None:
        """Load all bank schemas from the configuration directory."""
        bank_schemas_dir = self.config_dir / 'bank_schemas'
        if not bank_schemas_dir.exists():
            self.logger.warning(f"Bank schemas directory not found: {bank_schemas_dir}")
            return
        
        self._bank_schemas = {}
        for file_path in bank_schemas_dir.glob('*.yaml'):
            try:
                with open(file_path, 'r') as f:
                    schema = yaml.safe_load(f)
                    schema_id = schema.get('id')
                    if not schema_id:
                        self.logger.warning(f"Schema file missing ID: {file_path}")
                        continue
                    self._bank_schemas[schema_id] = schema
                    self.logger.debug(f"Loaded bank schema: {schema_id} from {file_path}")
            except Exception as e:
                self.logger.error(f"Error loading schema from {file_path}: {e}")
        
        self.logger.info(f"Loaded {len(self._bank_schemas)} bank schemas")
    
    def _load_internal_schemas(self) -> None:
        """Load all internal record schemas from the configuration directory."""
        internal_schemas_dir = self.config_dir / 'internal_schemas'
        if not internal_schemas_dir.exists():
            self.logger.warning(f"Internal schemas directory not found: {internal_schemas_dir}")
            return
        
        self._internal_schemas = {}
        for file_path in internal_schemas_dir.glob('*.yaml'):
            try:
                with open(file_path, 'r') as f:
                    schema = yaml.safe_load(f)
                    schema_id = schema.get('id')
                    if not schema_id:
                        self.logger.warning(f"Schema file missing ID: {file_path}")
                        continue
                    self._internal_schemas[schema_id] = schema
                    self.logger.debug(f"Loaded internal schema: {schema_id} from {file_path}")
            except Exception as e:
                self.logger.error(f"Error loading schema from {file_path}: {e}")
        
        self.logger.info(f"Loaded {len(self._internal_schemas)} internal schemas")
    
    def _load_transformer_scripts(self) -> None:
        """Load all transformer scripts from the configuration directory."""
        transformers_dir = self.config_dir / 'transformers'
        if not transformers_dir.exists():
            self.logger.warning(f"Transformers directory not found: {transformers_dir}")
            return
        
        self._transformer_scripts = {}
        for file_path in transformers_dir.glob('*.py'):
            try:
                transformer_id = file_path.stem
                with open(file_path, 'r') as f:
                    script_content = f.read()
                    self._transformer_scripts[transformer_id] = {
                        'id': transformer_id,
                        'script': script_content,
                        'path': str(file_path)
                    }
                    self.logger.debug(f"Loaded transformer: {transformer_id} from {file_path}")
            except Exception as e:
                self.logger.error(f"Error loading transformer from {file_path}: {e}")
        
        self.logger.info(f"Loaded {len(self._transformer_scripts)} transformer scripts")
    
    def get_bank_schema(self, schema_id: str) -> Optional[dict]:
        """Get bank schema by ID."""
        return self._bank_schemas.get(schema_id)
    
    def get_internal_schema(self, schema_id: str) -> Optional[dict]:
        """Get internal schema by ID."""
        return self._internal_schemas.get(schema_id)
    
    def get_transformer_script(self, script_id: str) -> Optional[dict]:
        """Get transformer script by ID."""
        return self._transformer_scripts.get(script_id)
    
    def list_bank_schemas(self) -> List[dict]:
        """List all available bank schemas."""
        return [
            {'id': schema_id, 'name': schema.get('name', schema_id), 'version': schema.get('version', '1.0.0')}
            for schema_id, schema in self._bank_schemas.items()
        ]
    
    def list_internal_schemas(self) -> List[dict]:
        """List all available internal schemas."""
        return [
            {'id': schema_id, 'name': schema.get('name', schema_id), 'version': schema.get('version', '1.0.0')}
            for schema_id, schema in self._internal_schemas.items()
        ]
    
    def detect_schema(self, data: Union[Dict, Any], schema_type: str = 'bank') -> Optional[str]:
        """
        Detect schema based on data structure.
        
        Args:
            data: The data to analyze for schema detection
            schema_type: Type of schema to detect ('bank' or 'internal')
            
        Returns:
            Detected schema ID or None if no match found
        """
        schemas = self._bank_schemas if schema_type == 'bank' else self._internal_schemas
        
        for schema_id, schema in schemas.items():
            detection_rules = schema.get('source', {}).get('detection_rules', {})
            if not detection_rules:
                continue
            
            # Check column patterns
            column_patterns = detection_rules.get('column_patterns', [])
            if column_patterns:
                data_columns = self._extract_column_names(data)
                matches = sum(1 for pattern in column_patterns if any(pattern.lower() in col.lower() for col in data_columns))
                match_ratio = matches / len(column_patterns) if column_patterns else 0
                
                if match_ratio >= 0.7:  # At least 70% of patterns matched
                    self.logger.info(f"Detected schema {schema_id} with {match_ratio:.2f} confidence")
                    return schema_id
        
        return None
    
    def _extract_column_names(self, data: Any) -> List[str]:
        """Extract column names from different data structures."""
        if hasattr(data, 'columns'):
            # Pandas DataFrame
            return [str(col) for col in data.columns]
        elif isinstance(data, dict) and all(isinstance(k, str) for k in data.keys()):
            # Dictionary with string keys (like first row of a CSV)
            return list(data.keys())
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            # List of dictionaries
            return list(data[0].keys())
        else:
            # Unknown format
            return []