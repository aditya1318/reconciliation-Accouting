# Schema Mapping Configuration

This directory contains YAML configuration files that define schema mappings for various data sources used in the reconciliation system. Each file provides a mapping between external data formats and our standardized internal format.

## Directory Structure

- `bank_schemas/` - Bank statement schema definitions
- `internal_schemas/` - Internal record schema definitions
- `transformers/` - Custom data transformation scripts

## Configuration Format

Schema mapping files use a consistent YAML format to define:

1. Source information (format, schema details)
2. Field mappings between source and target schemas
3. Transformation rules for data conversion
4. Validation rules for ensuring data integrity

See the example files for detailed structure and format.