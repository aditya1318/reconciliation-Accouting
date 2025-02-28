# Schema Mapping Framework: Architecture Documentation

## Overview

The Schema Mapping Framework is a flexible, configurable system for transforming heterogeneous financial data formats into standardized representations, enabling seamless reconciliation regardless of the source format. This document outlines the architecture, components, and data flow of the framework.

## Key Features

- **Format Agnostic**: Process any data format (CSV, Excel, XML, JSON) with a unified API
- **Configurable Transformations**: Use YAML configuration to define schema mappings without code changes
- **Validation Engine**: Ensure data integrity through schema-defined validation rules
- **Audit Trail**: Maintain comprehensive logs of all transformations for compliance
- **Auto-Detection**: Automatically identify source formats based on schema rules
- **Extensible**: Easily add custom transformations and parsers

## Architecture Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│                 │     │                  │     │                    │
│  Source Data    │────▶│  Schema Mapper   │────▶│  Transformed Data  │
│ (Heterogeneous) │     │                  │     │  (Standardized)    │
│                 │     │                  │     │                    │
└─────────────────┘     └──────────────────┘     └────────────────────┘
                                │
                                │
                      ┌─────────┴─────────┐
                      │                   │
                      ▼                   ▼
         ┌─────────────────────┐ ┌────────────────────┐
         │                     │ │                    │
         │ Schema Definitions  │ │   Audit Logging    │
         │  (YAML Config)      │ │                    │
         │                     │ │                    │
         └─────────────────────┘ └────────────────────┘
```

## Core Components

### 1. SchemaRegistry

The `SchemaRegistry` acts as a central repository of all schema definitions. It:

- **Loads schema definitions** from configuration files
- **Caches schemas** for efficient access
- **Auto-detects formats** based on schema detection rules
- **Manages transformer scripts** for custom transformations

```python
from bank_recon.schema_mapper import SchemaRegistry

# Initialize with custom config directory
registry = SchemaRegistry(config_dir="path/to/configs")

# Get schema by ID
hdfc_schema = registry.get_bank_schema("hdfc")

# List available schemas
all_bank_schemas = registry.list_bank_schemas()

# Auto-detect schema based on data
detected_schema_id = registry.detect_schema(dataframe, schema_type="bank")
```

### 2. SchemaLoader

The `SchemaLoader` is responsible for reading and parsing input data from various formats:

- **Support for multiple formats**: CSV, Excel, JSON, XML
- **Format-specific options**: Custom delimiters, header rows, etc.
- **Initial data cleanup**: Column standardization, data type conversion

```python
from bank_recon.schema_mapper import SchemaLoader

# Initialize loader
loader = SchemaLoader()

# Load data according to schema configuration
data_df, metadata = loader.load_data("statement.csv", hdfc_schema)
```

### 3. DataTransformer

The `DataTransformer` applies schema-defined transformations to convert data formats:

- **Field mapping**: Maps source fields to standardized target fields
- **Data type conversion**: Dates, numbers, strings with proper formatting
- **Derived fields**: Generate new fields based on existing ones
- **Custom transformations**: Apply complex transformations defined in scripts

```python
from bank_recon.schema_mapper import DataTransformer

# Initialize transformer
transformer = DataTransformer()

# Apply transformations according to schema
transformed_df = transformer.transform(data_df, hdfc_schema)
```

### 4. DataValidator

The `DataValidator` ensures data integrity through schema-defined validation rules:

- **Validation rule types**: Not null, unique, regex matching, min/max values, etc.
- **Custom validation expressions**: Complex validation logic using expressions
- **Validation reporting**: Detailed reports of validation failures

```python
from bank_recon.schema_mapper import DataValidator

# Initialize validator
validator = DataValidator()

# Validate data against schema rules
is_valid, validation_errors = validator.validate(transformed_df, hdfc_schema)
```

### 5. AuditLogger

The `AuditLogger` maintains a comprehensive audit trail for compliance and debugging:

- **Transformation logging**: Record all data transformations
- **Validation results**: Log validation successes and failures
- **Data snapshots**: Capture data states at different processing stages
- **Error tracking**: Detailed error logging with context

```python
from bank_recon.schema_mapper import AuditLogger

# Initialize audit logger
audit_logger = AuditLogger(audit_dir="path/to/audit/logs")

# Start a new audit record
audit_logger.start_audit("bank_statement_processing", source_info={"file_path": "statement.csv"})

# Record transformations, validations, etc.
audit_logger.record_transformation(transform_details)

# Complete the audit and save to file
audit_path = audit_logger.complete_audit("success", result_info=process_info)
```

### 6. SchemaMapper

The `SchemaMapper` is the main orchestrator that coordinates all the components:

- **Unified API**: Simple interface for processing any data source
- **Component coordination**: Manages the flow between components
- **Error handling**: Graceful error handling and recovery
- **Result packaging**: Standardized result format with metadata

```python
from bank_recon.schema_mapper import SchemaMapper

# Initialize the schema mapper
mapper = SchemaMapper()

# Process a bank statement
bank_df, process_info = mapper.process_bank_statement("statement.csv", schema_id="hdfc")

# Process internal records
internal_df, process_info = mapper.process_internal_records("records.csv", schema_id="tally_erp")
```

## Schema Configuration Format

Schema configurations are defined in YAML files with the following structure:

```yaml
# Basic information
name: "HDFC Bank"
id: "hdfc"
version: "1.0.0"
description: "Schema configuration for HDFC Bank statements"

# Source format details
source:
  supported_formats: ["csv", "excel"]
  encoding: "utf-8"
  excel_options:
    header_row: 9
    skip_footer: 3
  detection_rules:
    column_patterns: ["Date", "Narration", "Withdrawal Amt"]

# Field mappings
field_mappings:
  date:
    source: "Date"
    type: "date"
    required: true
    format: "%d/%m/%Y"
  narration:
    source: "Narration"
    type: "string"
    transform: "clean_description"
  # ... more fields

# Derived fields
derived_fields:
  payment_method:
    transform: "extract_payment_method"
    source: "narration"
    type: "string"
  # ... more derived fields

# Validation rules
validation_rules:
  - rule: "not_null"
    field: "date"
    error_message: "Transaction date cannot be null"
  # ... more rules

# Audit configuration
audit:
  enabled: true
  track_fields: ["date", "narration", "debit", "credit"]
  track_transformations: true
```

## Integration with Existing System

The Schema Mapping Framework integrates seamlessly with the existing reconciliation system:

1. **Updated Parser**: The `BankStatementParser` class now uses `SchemaMapper` internally
2. **Enhanced Reconciler**: The `BankReconciler` class can process any data source through schemas
3. **Backward Compatibility**: Legacy code still works with updated components
4. **Gradual Migration**: System can be migrated to use schemas incrementally

### Example Integration Workflow

```python
from bank_recon.reconciler_updated import BankReconciler

# Initialize reconciler (which uses SchemaMapper internally)
reconciler = BankReconciler(
    date_tolerance_days=2,
    amount_tolerance_percentage=0.01,
    description_match_threshold=70
)

# Perform reconciliation with schema-based mapping
summary = reconciler.reconcile(
    bank_statement_path="statement.csv",
    internal_records_path="records.csv",
    bank="hdfc",
    internal_schema_id="tally_erp"
)
```

## Data Flow

The typical data flow through the system is:

1. **Schema Loading**: Schema definitions are loaded and cached by `SchemaRegistry`
2. **Data Loading**: Raw data is loaded by `SchemaLoader` according to schema options
3. **Transformation**: Data is transformed by `DataTransformer` using schema mappings
4. **Validation**: Transformed data is validated by `DataValidator` using schema rules
5. **Auditing**: All operations are logged by `AuditLogger` for compliance
6. **Result Return**: Standardized data is returned for reconciliation processing

## Benefits of the Architecture

- **Separation of Concerns**: Each component has a clear, focused responsibility
- **Extensibility**: New formats, transformations, and validations can be added easily
- **Configuration over Code**: Changes to data handling via configuration, not code
- **Audit Trail**: Comprehensive logging for compliance and debugging
- **Standardization**: Consistent interface for all data sources
- **Error Handling**: Robust error management throughout the pipeline

## Future Extensions

The architecture is designed to support future enhancements such as:

- **Machine Learning Integration**: Advanced pattern recognition for field extraction
- **API Integration**: Direct connections to financial systems via APIs
- **Real-time Processing**: Stream processing for continuous reconciliation
- **Interactive Schema Builder**: Visual tools for schema creation and testing
- **Schema Validation**: Validation of schema definitions themselves


## Schema to refer to:

# Basic Schema Information (Required)
name: "Schema Name"                # Human-readable name
id: "unique_id"                    # Unique identifier (used by SchemaRegistry.get_bank_schema/get_internal_schema)
version: "1.0.0"                   # Schema version
description: "Description"         # Optional description

# Source Format Configuration (Required by SchemaLoader)
source:
  # List of supported file formats (used by SchemaLoader.load_data)
  supported_formats:               # Array of string values
    - csv                          # Supported values: csv, excel, json, xml
    - excel
  
  # Format-specific options
  encoding: "utf-8"                # Text encoding for files
  
  excel_options:                   # Used when loading Excel files
    sheet_name: 0                  # Sheet index or name
    header_row: 9                  # Row containing headers
    skip_footer: 3                 # Rows to skip at end
  
  csv_options:                     # Used when loading CSV files
    delimiter: ","                 # Field delimiter
    header_row: 9                  # Row containing headers
    skip_footer: 3                 # Rows to skip at end
  
  json_options:                    # Used when loading JSON files
    records_path: "data/entries"   # Path to array of records
  
  xml_options:                     # Used when loading XML files
    root_element: "Statement"      # Root element
    record_element: "Transaction"  # Repeating record element
  
  # Auto-detection config (used by SchemaRegistry.detect_schema)
  detection_rules:
    column_patterns:               # Column names that indicate this format
      - "Date"
      - "Narration"

# Field Mappings (Required by DataTransformer._apply_field_mappings)
field_mappings:
  target_field_name:               # Name of the standardized field
    source: "Source Field Name"    # Name of field in source data
    type: "data_type"              # Type: date, datetime, decimal, integer, string, boolean
    required: true                 # Whether field is required
    format: "%d/%m/%Y"             # Format string for dates
    transform: "transform_name"    # Name of transformation to apply

# Derived Fields (Optional, used by DataTransformer._apply_derived_fields)
derived_fields:
  derived_field_name:              # Name of the field to create
    transform: "transform_name"    # Transformation to apply
    source: "source_field"         # Source field to transform
    type: "data_type"              # Type of the derived field
    default: "default_value"       # Default value (optional)
    expression: "..."              # Expression for calculation (optional)

# Computed Fields (Optional, used by DataTransformer._apply_computed_fields)
computed_fields:
  computed_field_name:             # Name of the field to compute
    expression: "..."              # Expression using df column references
    type: "data_type"              # Type of the computed field

# Validation Rules (Optional, used by DataValidator.validate)
validation_rules:
  - rule: "rule_type"              # Type of validation rule
    field: "field_name"            # Field to validate
    error_message: "Error message" # Error message on validation failure
    # Additional parameters specific to rule type:
    value: 0                       # For min_value, max_value rules
    pattern: "regex"               # For regex rule
    min: 5                         # For length rule minimum
    max: 100                       # For length rule maximum
    values: ["A", "B", "C"]        # For in_set rule
    min_date: "2020-01-01"         # For date_range rule
    max_date: "today+30"           # For date_range rule
    expression: "..."              # For custom rule

# Audit Configuration (Optional, used by AuditLogger)
audit:
  enabled: true                    # Enable/disable audit logging
  track_fields:                    # Fields to track in audit logs
    - field1
    - field2
  track_transformations: true      # Whether to track transformations

# Custom Transformations (Optional, used by SchemaMapper._get_transformation_scripts)
transformations:
  transform_name:
    script: "..."                  # Python script content