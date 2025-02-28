#!/usr/bin/env python
"""
Simple Boundary Schema Test Script

This script tests YAML parsing of boundary test schemas without requiring direct imports
from the bank_recon package. It attempts to load each schema and checks for basic structure.
"""

import os
import sys
import yaml
import json
from pathlib import Path
from datetime import datetime

def print_separator(title=None):
    """Print a section separator with an optional title."""
    width = 80
    if title:
        padding = (width - len(title) - 2) // 2
        print("\n" + "=" * padding + f" {title} " + "=" * padding)
    else:
        print("\n" + "=" * width)

def check_schema_structure(schema_data):
    """Perform basic schema structure validation."""
    errors = []
    
    # Check required top-level fields
    required_fields = ['name', 'id', 'version', 'source', 'field_mappings']
    for field in required_fields:
        if field not in schema_data:
            errors.append(f"Missing required field: {field}")
    
    # Check source section
    if 'source' in schema_data:
        source = schema_data['source']
        if not isinstance(source, dict):
            errors.append("'source' must be a dictionary")
        elif 'supported_formats' not in source:
            errors.append("'source' must contain 'supported_formats'")
    
    # Check field_mappings section
    if 'field_mappings' in schema_data:
        field_mappings = schema_data['field_mappings']
        if not isinstance(field_mappings, dict):
            errors.append("'field_mappings' must be a dictionary")
        else:
            for field_name, field_config in field_mappings.items():
                if not isinstance(field_config, dict):
                    errors.append(f"Field config for '{field_name}' must be a dictionary")
                else:
                    if 'type' not in field_config:
                        errors.append(f"Field '{field_name}' is missing required 'type'")
                    
                    valid_types = ['date', 'decimal', 'string', 'boolean', 'integer']
                    if 'type' in field_config and field_config['type'] not in valid_types:
                        errors.append(f"Field '{field_name}' has invalid type: {field_config['type']}")
    
    # Check derived_fields section if present
    if 'derived_fields' in schema_data:
        derived_fields = schema_data['derived_fields']
        if not isinstance(derived_fields, dict):
            errors.append("'derived_fields' must be a dictionary")
        else:
            for field_name, field_config in derived_fields.items():
                if not isinstance(field_config, dict):
                    errors.append(f"Derived field config for '{field_name}' must be a dictionary")
                else:
                    if 'transform' not in field_config:
                        errors.append(f"Derived field '{field_name}' is missing required 'transform'")
                    if 'type' not in field_config:
                        errors.append(f"Derived field '{field_name}' is missing required 'type'")
    
    # Check validation_rules section if present
    if 'validation_rules' in schema_data:
        validation_rules = schema_data['validation_rules']
        if not isinstance(validation_rules, list):
            errors.append("'validation_rules' must be a list")
        else:
            for i, rule in enumerate(validation_rules):
                if not isinstance(rule, dict):
                    errors.append(f"Validation rule #{i+1} must be a dictionary")
                elif 'rule' not in rule:
                    errors.append(f"Validation rule #{i+1} is missing required 'rule' field")
    
    return errors

def test_schema_file(file_path):
    """Test loading and basic validation of a schema file."""
    print_separator(f"Testing {os.path.basename(file_path)}")
    
    try:
        # Try to load the schema file
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                schema_data = yaml.safe_load(f)
                print(f"✓ YAML syntax is valid")
                
                # Print basic schema info
                print(f"Schema name: {schema_data.get('name', 'Unknown')}")
                print(f"Schema ID: {schema_data.get('id', 'Unknown')}")
                print(f"Version: {schema_data.get('version', 'Unknown')}")
                
                # Check schema structure
                errors = check_schema_structure(schema_data)
                if errors:
                    print(f"✗ Schema structure has {len(errors)} issues:")
                    for error in errors:
                        print(f"  - {error}")
                else:
                    print(f"✓ Basic schema structure is valid")
                
                # Count sections and fields
                print("\nSchema Statistics:")
                print(f"Field mappings: {len(schema_data.get('field_mappings', {}))}")
                print(f"Derived fields: {len(schema_data.get('derived_fields', {}))}")
                print(f"Validation rules: {len(schema_data.get('validation_rules', []))}")
                print(f"Preprocessing steps: {len(schema_data.get('preprocessing', []))}")
                print(f"Functions: {len(schema_data.get('functions', []))}")
                
                # Print detailed structure overview
                print("\nStructure Overview:")
                top_level_keys = list(schema_data.keys())
                print(f"Top-level sections: {', '.join(top_level_keys)}")
            
            except yaml.YAMLError as e:
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
    project_root = os.path.dirname(os.path.abspath(__file__))
    boundary_dir = os.path.join(project_root, 'examples', 'boundary_tests')
    if not os.path.exists(boundary_dir):
        os.makedirs(boundary_dir, exist_ok=True)
        print(f"Created boundary tests directory: {boundary_dir}")
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