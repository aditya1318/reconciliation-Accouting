#!/usr/bin/env python
"""
Boundary Schema Test Script

This script tests the behavior of the schema validation system when confronted with
various edge cases and invalid configurations. It attempts to load and validate
each schema, capturing any errors or issues that arise.
"""

import os
import sys
import logging
import yaml
import traceback
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add project root to path to import bank_recon modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from bank_recon.schema_mapper.validator import SchemaValidator
    from bank_recon.schema_mapper.loader import SchemaLoader
    from bank_recon.schema_mapper.registry import SchemaRegistry
    from bank_recon.schema_mapper.mapper import SchemaMapper
except ImportError:
    print("Error importing bank_recon modules. Make sure you're in the project root directory.")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('boundary_test')

# Create sample data for testing
def create_sample_data():
    """Create sample CSV data for testing schemas."""
    # Ensure the test data directory exists
    os.makedirs('examples/boundary_tests/data', exist_ok=True)
    
    # Create a sample CSV file with various data types and edge cases
    data = {
        'Date': ['2025-01-15', '2025-01-20', '2025-01-25', '2025-01-30', 'Invalid Date'],
        'Amount': ['1000.50', '-500.25', '0.00', 'Not a number', '1,000,000.00'],
        'Description': ['Normal transaction', 'With, comma', 'Extremely ' + 'long ' * 50 + 'description', '', None],
        'Category': ['Food', 'Transport', 'Entertainment', 'Other', None],
        'Status': ['Active', 'Pending', 'Canceled', 'Unknown', None],
        'Reference': ['REF123', '456', 'Alpha123', None, '']
    }
    
    df = pd.DataFrame(data)
    csv_path = 'examples/boundary_tests/data/sample_data.csv'
    df.to_csv(csv_path, index=False)
    
    return csv_path

def print_separator(title=None):
    """Print a section separator with an optional title."""
    width = 80
    if title:
        padding = (width - len(title) - 2) // 2
        print("\n" + "=" * padding + f" {title} " + "=" * padding)
    else:
        print("\n" + "=" * width)

def test_schema_file(file_path):
    """Test loading and validating a schema file."""
    print_separator(f"Testing {os.path.basename(file_path)}")
    
    try:
        # Try to load the schema file
        with open(file_path, 'r') as f:
            try:
                schema_data = yaml.safe_load(f)
                print(f"✓ YAML syntax is valid")
                
                # Print basic schema info
                print(f"Schema name: {schema_data.get('name', 'Unknown')}")
                print(f"Schema ID: {schema_data.get('id', 'Unknown')}")
                print(f"Version: {schema_data.get('version', 'Unknown')}")
                
                # Try to validate the schema
                validator = SchemaValidator()
                try:
                    validator.validate_schema(schema_data)
                    print(f"✓ Schema structure is valid")
                    
                    # Try to apply the schema to sample data
                    try:
                        # Create a test data file
                        csv_path = create_sample_data()
                        
                        # Create schema loader and mapper
                        loader = SchemaLoader()
                        schema_mapper = SchemaMapper(logger=logger)
                        
                        # Try to process the data with this schema
                        schema_id = schema_data.get('id', 'unknown')
                        schema_registry = SchemaRegistry()
                        schema_registry.register_schema(schema_id, schema_data, 'bank')
                        schema_mapper.schema_registry = schema_registry
                        
                        try:
                            result_df, process_info = schema_mapper.process_bank_statement(
                                csv_path, schema_id=schema_id
                            )
                            print(f"✓ Schema was successfully applied to data")
                            print(f"  Validation result: {'Valid' if process_info['is_valid'] else 'Invalid'}")
                            if not process_info['is_valid']:
                                print(f"  Validation errors: {process_info['validation_errors']}")
                            
                            # Print transformation info
                            print(f"  Original columns: {process_info.get('original_columns', 'Unknown')}")
                            print(f"  Result columns: {process_info.get('result_columns', 'Unknown')}")
                            
                            # Print first 2 rows of transformed data
                            if not result_df.empty:
                                print("\nSample transformed data (first 2 rows):")
                                pd.set_option('display.max_columns', None)
                                pd.set_option('display.width', 1000)
                                print(result_df.head(2).to_string())
                            
                        except Exception as e:
                            print(f"✗ Error applying schema to data: {str(e)}")
                            print(f"Traceback: {traceback.format_exc()}")
                    
                    except Exception as e:
                        print(f"✗ Error setting up test data: {str(e)}")
                
                except Exception as e:
                    print(f"✗ Schema structure is invalid: {str(e)}")
            
            except Exception as e:
                print(f"✗ YAML syntax is invalid: {str(e)}")
    
    except Exception as e:
        print(f"✗ Error reading file: {str(e)}")
    
    print_separator()

def test_all_boundary_schemas():
    """Test all boundary test schemas."""
    print("\nBOUNDARY SCHEMA TESTING")
    print("======================\n")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version: {sys.version}")
    
    # Get all YAML files in the boundary_tests directory
    boundary_dir = os.path.join(project_root, 'examples', 'boundary_tests')
    if not os.path.exists(boundary_dir):
        print(f"Boundary tests directory not found: {boundary_dir}")
        return
    
    schema_files = [f for f in os.listdir(boundary_dir) if f.endswith('.yaml')]
    
    if not schema_files:
        print("No schema files found in boundary_tests directory")
        return
    
    print(f"Found {len(schema_files)} schema files to test\n")
    
    for schema_file in schema_files:
        file_path = os.path.join(boundary_dir, schema_file)
        test_schema_file(file_path)
    
    print("\nBoundary testing completed")

if __name__ == '__main__':
    test_all_boundary_schemas()