"""
Schema Loader module for reading and parsing input data.

This module handles loading data from various formats based on schema configuration
and performs initial parsing according to schema-defined rules.
"""

import os
import pandas as pd
import yaml
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple


class SchemaLoader:
    """
    Loader for reading and parsing data according to schema configuration.
    
    Handles CSV, Excel, JSON, XML and other formats, with configurable
    parsing options specific to each schema.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the schema loader.
        
        Args:
            logger: Logger for recording loader operations.
        """
        self.logger = logger or logging.getLogger('schema_loader')
    
    def load_data(self, file_path: str, schema: dict) -> Tuple[pd.DataFrame, dict]:
        """
        Load data from a file according to schema configuration.
        
        Args:
            file_path: Path to the data file.
            schema: Schema configuration for parsing the data.
            
        Returns:
            Tuple of (dataframe, metadata)
            
        Raises:
            ValueError: If file format is unsupported or parsing fails.
        """
        file_ext = Path(file_path).suffix.lower()
        source_config = schema.get('source', {})
        supported_formats = source_config.get('supported_formats', [])
        
        # Determine format from file extension
        if file_ext == '.csv' and 'csv' in supported_formats:
            return self._load_csv(file_path, source_config.get('csv_options', {}))
        elif file_ext in ['.xls', '.xlsx'] and 'excel' in supported_formats:
            return self._load_excel(file_path, source_config.get('excel_options', {}))
        elif file_ext == '.json' and 'json' in supported_formats:
            return self._load_json(file_path, source_config.get('json_options', {}))
        elif file_ext in ['.xml', '.html'] and 'xml' in supported_formats:
            return self._load_xml(file_path, source_config.get('xml_options', {}))
        else:
            raise ValueError(f"Unsupported file format for schema: {file_ext}")
    
    def _load_csv(self, file_path: str, options: dict) -> Tuple[pd.DataFrame, dict]:
        """Load data from CSV file."""
        self.logger.info(f"Loading CSV file: {file_path}")
        
        # Extract options with defaults
        encoding = options.get('encoding', 'utf-8')
        delimiter = options.get('delimiter', ',')
        header_row = options.get('header_row', 0)
        skip_footer = options.get('skip_footer', 0)
        
        # Read the CSV file
        try:
            if skip_footer > 0:
                # Count total rows to calculate skipfooter for pandas
                with open(file_path, 'r', encoding=encoding) as f:
                    total_rows = sum(1 for _ in f)
                
                # Read with skipfooter
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    delimiter=delimiter,
                    header=header_row,
                    skipfooter=skip_footer,
                    engine='python'  # Required for skipfooter
                )
            else:
                # Standard read without skipfooter
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    delimiter=delimiter,
                    header=header_row
                )
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Create metadata
            metadata = {
                'source_type': 'csv',
                'rows_loaded': len(df),
                'columns': list(df.columns),
                'file_path': file_path
            }
            
            return df, metadata
            
        except Exception as e:
            self.logger.error(f"Error loading CSV file: {e}")
            raise ValueError(f"Failed to load CSV file: {e}")
    
    def _load_excel(self, file_path: str, options: dict) -> Tuple[pd.DataFrame, dict]:
        """Load data from Excel file."""
        self.logger.info(f"Loading Excel file: {file_path}")
        
        # Extract options with defaults
        sheet_name = options.get('sheet_name', 0)
        header_row = options.get('header_row', 0)
        skip_footer = options.get('skip_footer', 0)
        
        try:
            # Check if we need to handle skip_footer
            if skip_footer > 0:
                # First, load to get total rows
                temp_df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=None
                )
                
                # Calculate the number of rows to read
                nrows = len(temp_df) - skip_footer - header_row
                
                # Now read with nrows
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=header_row,
                    nrows=nrows
                )
            else:
                # Standard read without skip_footer
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=header_row
                )
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Create metadata
            metadata = {
                'source_type': 'excel',
                'rows_loaded': len(df),
                'columns': list(df.columns),
                'file_path': file_path,
                'sheet_name': sheet_name
            }
            
            return df, metadata
            
        except Exception as e:
            self.logger.error(f"Error loading Excel file: {e}")
            raise ValueError(f"Failed to load Excel file: {e}")
    
    def _load_json(self, file_path: str, options: dict) -> Tuple[pd.DataFrame, dict]:
        """Load data from JSON file."""
        self.logger.info(f"Loading JSON file: {file_path}")
        
        # Extract options with defaults
        encoding = options.get('encoding', 'utf-8')
        records_path = options.get('records_path', None)
        
        try:
            # Read the JSON file
            with open(file_path, 'r', encoding=encoding) as f:
                data = json.load(f)
            
            # Extract records based on path
            if records_path:
                for key in records_path.split('/'):
                    if key and (isinstance(data, dict) and key in data):
                        data = data[key]
                    elif key and isinstance(data, list) and key.isdigit():
                        data = data[int(key)]
                    else:
                        self.logger.warning(f"Path component '{key}' not found in JSON")
            
            # Convert to DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                raise ValueError("Expected JSON array or object")
            
            # Create metadata
            metadata = {
                'source_type': 'json',
                'rows_loaded': len(df),
                'columns': list(df.columns),
                'file_path': file_path
            }
            
            return df, metadata
            
        except Exception as e:
            self.logger.error(f"Error loading JSON file: {e}")
            raise ValueError(f"Failed to load JSON file: {e}")
    
    def _load_xml(self, file_path: str, options: dict) -> Tuple[pd.DataFrame, dict]:
        """Load data from XML file."""
        self.logger.info(f"Loading XML file: {file_path}")
        
        # Extract options with defaults
        root_element = options.get('root_element', None)
        record_element = options.get('record_element', None)
        
        try:
            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Navigate to root element if specified
            if root_element:
                for path in root_element.split('/'):
                    if not path:
                        continue
                    found = False
                    for child in root:
                        if child.tag == path or child.tag.endswith(f"}}{path}"):  # Handle namespaces
                            root = child
                            found = True
                            break
                    if not found:
                        self.logger.warning(f"XML path element '{path}' not found")
            
            # Find record elements
            records = []
            
            if record_element:
                # Find all elements matching the record element path
                elements = root.findall(f".//{record_element}")
                for element in elements:
                    record = {}
                    # Extract all child element values
                    for child in element:
                        tag = child.tag
                        if '}' in tag:  # Handle namespaces
                            tag = tag.split('}', 1)[1]
                        record[tag] = child.text
                    records.append(record)
            else:
                # If no record element specified, use direct children of root
                for element in root:
                    tag = element.tag
                    if '}' in tag:  # Handle namespaces
                        tag = tag.split('}', 1)[1]
                    records.append({tag: element.text})
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Create metadata
            metadata = {
                'source_type': 'xml',
                'rows_loaded': len(df),
                'columns': list(df.columns),
                'file_path': file_path
            }
            
            return df, metadata
            
        except Exception as e:
            self.logger.error(f"Error loading XML file: {e}")
            raise ValueError(f"Failed to load XML file: {e}")