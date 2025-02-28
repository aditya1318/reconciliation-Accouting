# Indian Bank Reconciliation System

A comprehensive reconciliation system specifically designed for Indian bank statements. This system processes standard fields including transaction date, value date, cheque/reference number, transaction description, debit amount, credit amount, and running balance.

## Key Features

- **India-specific Banking Support**: Handles multiple Indian bank formats (HDFC, SBI, ICICI, Axis, Yes Bank, etc.)
- **Intelligent Transaction Matching**: Uses sophisticated algorithms to match transactions with configurable tolerances
- **India-specific Transaction Identifiers**: Recognizes UPI, IMPS, NEFT, RTGS transactions and parses IFSC codes
- **GST and TDS Handling**: Identifies and accounts for GST/TDS components in transactions
- **Detailed Reporting**: Generates comprehensive reconciliation reports in multiple formats

## Installation

### Prerequisites

- Python 3.8 or higher

### From PyPI (Recommended)

```bash
pip install indian-bank-recon
```

### From Source

```bash
git clone https://github.com/username/indian-bank-recon.git
cd indian-bank-recon
pip install -e .
```

## Quick Start

### Command Line Interface

```bash
# Basic usage
bank-recon --bank-statement path/to/bank_statement.xlsx --internal-records path/to/internal_records.xlsx

# Specify bank format (optional)
bank-recon --bank-statement statement.xlsx --internal-records records.xlsx --bank hdfc

# Customize matching parameters
bank-recon --bank-statement statement.xlsx --internal-records records.xlsx \
           --date-tolerance 2 --amount-tolerance 0.05 --description-threshold 75

# Generate all report formats
bank-recon --bank-statement statement.xlsx --internal-records records.xlsx \
           --report-format all --output-dir ./reports
```

### Programmatic Usage

```python
from bank_recon.reconciler import BankReconciler
from bank_recon.report_generator import ReconciliationReportGenerator

# Initialize reconciler with custom parameters
reconciler = BankReconciler(
    date_tolerance_days=2,                # Allow up to 2 days difference
    amount_tolerance_percentage=0.05,     # Allow up to 5% difference in amounts
    description_match_threshold=75        # Fuzzy matching threshold for descriptions
)

# Perform reconciliation
summary = reconciler.reconcile(
    bank_statement_path='statement.xlsx',
    internal_records_path='records.xlsx',
    bank='hdfc'  # Specify bank format
)

# Print summary statistics
print(f"Match Rate: {summary['match_rate'] * 100:.2f}%")
print(f"Matched: {summary['matched_count']}/{summary['total_bank_transactions']}")

# Generate reports
report_generator = ReconciliationReportGenerator(output_dir='./reports')
excel_path = report_generator.generate_excel_report(reconciler)
html_path = report_generator.generate_html_report(reconciler)
```

## Supported Banks

The system comes with pre-configured formats for these Indian banks:

- HDFC Bank
- State Bank of India (SBI)
- ICICI Bank
- Axis Bank
- Yes Bank

Additional bank formats can be added via the configuration file.

## Transaction Matching Algorithm

The system uses a multi-criteria matching algorithm that considers:

1. **Amount Matching**: Exact matches or within a configurable tolerance percentage
2. **Date Matching**: Exact or within a configurable number of days
3. **Description Matching**: Fuzzy matching of transaction narrations
4. **Reference ID Matching**: Recognizes India-specific payment references (UPI, IMPS, NEFT IDs)

The algorithm also handles:

- GST-inclusive amount matching (automatically detects and adjusts for 18% GST)
- TDS adjustments in transaction amounts
- Indian payment method identification (UPI, IMPS, NEFT, RTGS, etc.)
- IFSC code extraction and matching

## Configuration

### Bank Format Configuration

The system uses YAML files to configure bank statement formats. The default configuration is at `config/bank_formats.yaml`. You can specify a custom configuration file with the `--config` option.

```yaml
hdfc:
  date_format: "%d/%m/%Y"
  columns:
    date: "Date"
    value_date: "Value Date"
    narration: "Narration"
    ref_no: "Chq/Ref Number"
    debit: "Withdrawal Amt"
    credit: "Deposit Amt"
    balance: "Closing Balance"
```

### Reconciliation Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `date_tolerance_days` | Maximum days difference for date matching | 3 |
| `amount_tolerance_percentage` | Maximum percentage difference for amount matching | 0.01 (1%) |
| `description_match_threshold` | Threshold for fuzzy description matching (0-100) | 80 |
| `match_criteria` | Weights for different matching criteria | {'amount': 0.5, 'date': 0.3, 'description': 0.2} |

## Report Formats

The system can generate reconciliation reports in multiple formats:

- **Excel (.xlsx)**: Multi-sheet workbook with detailed transaction matches
- **CSV (.csv)**: Separate files for each component (matched, unmatched, etc.)
- **HTML (.html)**: Interactive report with color-coded matching status
- **JSON (.json)**: Complete reconciliation data in JSON format

## Example Reports

### Summary Statistics

Each report includes summary statistics such as:

- Total transactions processed
- Number and percentage of matched transactions
- Unmatched bank and internal transactions
- Partial matches with matching scores
- Total amounts for each category

### Matched Transactions

Detailed information about matched transactions including:

- Bank and internal transaction IDs
- Match type (EXACT, AMOUNT_MISMATCH, DATE_MISMATCH, PARTIAL)
- Match score and confidence level
- Amount and date differences
- Transaction descriptions from both sources

### Unmatched Transactions

For unmatched transactions, the system provides:

- Lists of unmatched bank transactions
- Lists of unmatched internal records
- Match suggestions with confidence scores

## Running the Example

The repository includes an example script that demonstrates the reconciliation process:

```bash
python example.py
```

This creates sample bank and internal record files, performs reconciliation, and generates reports in all supported formats.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.