# Financial Report Template System - Implementation Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [DocType Structure](#doctype-structure)
4. [Configuration Guide](#configuration-guide)
5. [Usage Examples](#usage-examples)
6. [Excel Export](#excel-export)
7. [Budget Integration](#budget-integration)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This flexible financial reporting system allows you to:
- **Create multiple report formats** without coding
- **Configure account mappings** using 5 different methods
- **Define calculation formulas** in simple text format
- **Generate beautiful Excel exports** with professional formatting
- **Optionally compare against budgets** from your Budget Plan
- **Switch between formats instantly** for different audiences

### Key Benefits
✅ **No more hardcoding** - All configuration in database  
✅ **Finance team control** - No developer needed for changes  
✅ **Multiple formats** - Board reports, Management reports, IFRS, GAAP  
✅ **Budget integration** - Optional budget vs actual comparison  
✅ **Beautiful Excel** - Professional formatting, colors, borders  
✅ **Flexible accounts** - 5 mapping methods for maximum flexibility  

---

## 🚀 Installation

### Step 1: Install DocTypes

```bash
# Navigate to your ERPNext app directory
cd ~/frappe-bench/apps/ecclesia/ecclesia/ecclesia/doctype

# Create directories
mkdir financial_report_template
mkdir financial_report_line

# Copy DocType JSON files
cp /path/to/financial_report_template.json financial_report_template/
cp /path/to/financial_report_line.json financial_report_line/

# Restart bench
cd ~/frappe-bench
bench restart
```

### Step 2: Install Report Python File

```bash
# Navigate to reports directory
cd ~/frappe-bench/apps/ecclesia/ecclesia/ecclesia/report

# Create report directory
mkdir financial_report_dynamic

# Copy files
cp /path/to/financial_report_dynamic.py financial_report_dynamic/
cp /path/to/excel_export.py financial_report_dynamic/
```

### Step 3: Run Migration Script

```bash
# Run the migration to create initial templates
bench console
>>> from ecclesia.ecclesia.report.financial_report_dynamic.migration_script import run_migration
>>> run_migration()
```

### Step 4: Install Dependencies

```bash
# Install openpyxl for Excel export
bench pip install openpyxl
```

---

## 📊 DocType Structure

### Financial Report Template (Master DocType)

**Purpose:** Defines a complete report format with all its settings

**Key Fields:**
- `template_name` - Unique name (e.g., "Standard P&L", "IFRS Balance Sheet")
- `report_type` - Profit and Loss, Balance Sheet, Cash Flow, or Custom
- `is_default` - Mark as default for this report type
- `show_comparison` - Enable year-over-year comparison
- `enable_budget_comparison` - Allow budget vs actual comparison
- `excel_*` - Excel export formatting settings
- `report_lines` - Child table with all line items

### Financial Report Line (Child Table)

**Purpose:** Defines each line in the report

**Key Fields:**
- `line_number` - Sorting order (10, 20, 30...)
- `line_label` - Display name (e.g., "Revenue", "Gross Profit")
- `line_code` - Short code for formulas (e.g., "REV", "GP")
- `line_type` - Account Aggregate, Calculated, Header, or Blank Line
- `account_mapping_method` - How to select accounts
- `calculation_formula` - For calculated lines (e.g., "REV - COS")
- `indent_level` - Visual hierarchy (0, 1, 2...)
- `is_bold`, `is_total_row`, `is_subtotal_row` - Styling
- `sign_multiplier` - 1 or -1 to reverse sign

---

## ⚙️ Configuration Guide

### Creating a New Template

1. **Go to:** Financial Report Template list
2. **Click:** New
3. **Fill in basic details:**
   - Template Name: "My Custom P&L"
   - Report Type: "Profit and Loss"
   - Report Title: "Income Statement"
   - Enable checkboxes as needed

4. **Configure Excel settings:**
   - Header Color: #4472C4 (blue)
   - Total Row Color: #E7E6E6 (gray)
   - Decimal Places: 2
   - Thousands Separator: Yes

5. **Add Report Lines** (see below)

### Adding Report Lines

#### Example 1: Revenue Line (Account Aggregate)

```
Line Number: 10
Line Label: Revenue
Line Code: REV
Line Type: Account Aggregate
Account Mapping Method: Account Numbers Pattern
Account Number Pattern: 7000-7599
Sign Multiplier: 1
Is Bold: ✓
```

#### Example 2: Gross Profit (Calculated)

```
Line Number: 30
Line Label: Gross Profit
Line Code: GP
Line Type: Calculated
Calculation Formula: REV - COS
Is Bold: ✓
Is Total Row: ✓
```

#### Example 3: Section Header

```
Line Number: 100
Line Label: OPERATING EXPENSES
Line Type: Header
Is Bold: ✓
```

#### Example 4: Blank Line

```
Line Number: 35
Line Type: Blank Line
```

### Account Mapping Methods

#### 1️⃣ **Account Range**
Maps accounts between two accounts (by number).

**Example:**
- Account From: `7000 - Sales Revenue`
- Account To: `7599 - Other Revenue`

**Use When:** You have sequential account numbers

---

#### 2️⃣ **Account Numbers Pattern**
Uses patterns to match account numbers.

**Examples:**
- `7000-7599` - Range from 7000 to 7599
- `7%` - All accounts starting with 7
- `7[0-5]%` - Accounts 7000-7599 using SQL LIKE

**Use When:** You have consistent numbering schemes

---

#### 3️⃣ **Specific Accounts**
Lists exact accounts by name.

**Example:**
```
Sales - Retail, Sales - Wholesale, Service Income
```

**Use When:** You need to cherry-pick specific accounts

---

#### 4️⃣ **Financial Reporting Group**
Uses your existing custom field.

**Example:**
- Financial Reporting Group: `Brokerage income`

**Use When:** You've already categorized accounts

---

#### 5️⃣ **Root Type**
Selects all accounts of a root type.

**Options:**
- Income
- Expense
- Asset
- Liability
- Equity

**Use When:** You need all accounts of a type (e.g., Balance Sheet)

---

### Formula Syntax

Formulas use line codes and basic math operators:

**Operators:** `+`, `-`, `*`, `/`, `(`, `)`

**Examples:**
```
REV - COS                           → Gross Profit
GP - ADMIN - SELL - EMP             → EBITDA
EBITDA - DEPR - AMORT               → EBIT
EBIT - FIN + OTHER                  → PBT
(REV - COS) / REV * 100             → GP Margin %
```

**Rules:**
- Use UPPERCASE for line codes
- Spaces are optional
- Parentheses supported
- Only reference line codes that appear BEFORE this line

---

## 📝 Usage Examples

### Example 1: Standard P&L Template

**Template Setup:**
```
Template Name: Standard P&L
Report Type: Profit and Loss
Show Comparison: ✓
Enable Budget Comparison: ✓
```

**Lines:**
| # | Label | Type | Mapping/Formula |
|---|-------|------|-----------------|
| 10 | Revenue | Account Aggregate | Pattern: 7000-7599 |
| 20 | Cost of Sales | Account Aggregate | Pattern: 7600-7999 |
| 30 | **Gross Profit** | Calculated | REV - COS |
| 35 | _(blank)_ | Blank Line | |
| 40 | Admin Expenses | Account Aggregate | Group: Administrative |
| 50 | Selling Expenses | Account Aggregate | Group: Selling & Marketing |
| 60 | Employee Benefits | Account Aggregate | Group: Employee Benefits |
| 70 | **EBITDA** | Calculated | GP - ADMIN - SELL - EMP |
| 80 | Depreciation | Account Aggregate | Group: Depreciation |
| 90 | **EBIT** | Calculated | EBITDA - DEPR |

---

### Example 2: Management Report (Detailed)

Same as Standard P&L but with:
- More granular expense breakdown
- Departmental splits
- Budget variance columns
- Percentage of revenue columns

**Just clone the Standard P&L template and add more detail lines!**

---

### Example 3: Board Report (Summary)

Simplified version with only key metrics:
- Revenue
- Gross Profit
- EBITDA
- EBIT
- Profit Before Tax

**Just use fewer lines and hide detail!**

---

## 📊 Excel Export

### Features

✨ **Professional Formatting:**
- Company header with logo area
- Period and date information
- Frozen header row
- Colored headers and totals
- Borders and alignment
- Thousands separators
- Negative values in red

✨ **Dynamic Columns:**
- Monthly, Quarterly, or Half-Yearly periods
- Last Year comparison (optional)
- Budget comparison (optional)
- Variance percentages
- YTD totals
- % of Revenue column

✨ **Smart Styling:**
- Total rows: Bold + gray background
- Subtotal rows: Light gray background
- Calculated rows: Bold text
- Indented rows: Visual hierarchy
- Conditional formatting for variances

### Excel Column Structure

**Monthly Report with All Options:**
```
Account Name | Jan | Jan LY | Jan Var% | Jan Bud | Jan Bud Var% | ... | YTD | YTD LY | YTD Var% | YTD Bud | YTD Bud Var% | % Rev
```

**Quarterly Report (No Budget):**
```
Account Name | Q1 | Q1 LY | Q1 Var% | Q2 | Q2 LY | Q2 Var% | ... | YTD | YTD LY | YTD Var%
```

---

## 💰 Budget Integration

### Setup

1. **Enable in Template:**
   - Edit your template
   - Check "Enable Budget Comparison"
   - Save

2. **Create Budget Plan:**
   - Go to Budget Plan list
   - Create new budget with monthly breakdown
   - Link GL accounts in "Monthly Budget" child table
   - Fill in monthly amounts (Jan, Feb, Mar...)

3. **Run Report:**
   - Select template
   - Check "Show Budget"
   - Select Budget Plan
   - Generate report

### Budget Columns

When budget comparison is enabled, you get:
- **[Period] Bud** - Budget amount for period
- **[Period] Bud Var %** - Variance from budget
- **YTD Budget** - Year-to-date budget
- **YTD Bud Var %** - YTD variance from budget

**Formula:**
```
Budget Variance % = (Actual - Budget) / |Budget| × 100
```

---

## 🔧 Troubleshooting

### Issue: Template not showing in report

**Solution:**
- Check template is marked as "Active"
- Verify report type matches
- Refresh page

---

### Issue: Accounts not appearing

**Solution:**
- Check account mapping method is correct
- For patterns: verify SQL LIKE syntax
- For ranges: ensure accounts have numbers
- For groups: verify custom field is populated
- Check company filter matches

---

### Issue: Formula not calculating

**Solution:**
- Verify line codes are UPPERCASE
- Check referenced lines appear BEFORE this line
- Test formula manually: (100 - 50) should give 50
- Check for division by zero

---

### Issue: Excel export fails

**Solution:**
- Ensure openpyxl is installed: `bench pip install openpyxl`
- Check for very large datasets (>10,000 rows)
- Verify template colors are valid hex codes

---

### Issue: Budget comparison not working

**Solution:**
- Template must have "Enable Budget Comparison" checked
- Budget Plan must exist and be submitted
- GL Accounts must match between report and budget
- Budget Plan must have values in monthly_budget child table

---

## 🎓 Advanced Tips

### Tip 1: Multiple Templates for Different Audiences

Create variations:
- **Board Template** - High-level summary only
- **Management Template** - Detailed with all line items
- **IFRS Template** - Compliance format
- **Tax Template** - Tax authority format

All from the same GL data, just different views!

---

### Tip 2: Use Indent for Visual Hierarchy

```
Revenue (indent: 0, bold)
    Product Sales (indent: 1)
    Service Revenue (indent: 1)
Total Revenue (indent: 0, bold, total row)
```

---

### Tip 3: Smart Sign Multipliers

For Expenses that should display as positive:
- Set Sign Multiplier = 1
- System handles root type logic automatically

For reversed entries:
- Set Sign Multiplier = -1

---

### Tip 4: Reusable Line Codes

Use meaningful codes:
- `REV` for Revenue
- `COS` for Cost of Sales
- `GP` for Gross Profit
- `EBITDA` for EBITDA
- `EBIT` for EBIT
- `PBT` for Profit Before Tax

This makes formulas readable!

---

### Tip 5: Clone Templates

Instead of creating from scratch:
1. Open existing template
2. Click "Menu" → "Duplicate"
3. Rename
4. Modify lines as needed

Much faster! ⚡

---

## 📚 Quick Reference

### Common Patterns

| Task | Pattern |
|------|---------|
| All 7xxx accounts | `7%` |
| 7000-7599 range | `7000-7599` |
| Specific accounts | `Account A, Account B, Account C` |
| All Income | Root Type: Income |
| All Assets | Root Type: Asset |

### Common Formulas

| Metric | Formula |
|--------|---------|
| Gross Profit | `REV - COS` |
| EBITDA | `GP - OPEX` |
| EBIT | `EBITDA - DEPR` |
| Operating Profit | `EBIT - FIN` |
| PBT | `OP + OTHER` |
| Margin % | `GP / REV` |

---

## 🎉 Conclusion

You now have a **world-class financial reporting system** that:
- ✅ Eliminates hardcoded reports
- ✅ Empowers finance teams
- ✅ Supports multiple formats
- ✅ Integrates with budgets
- ✅ Exports beautiful Excel
- ✅ Scales effortlessly

**No more editing Python code to change a report!** 🚀

---

## 📞 Support

For questions or issues:
1. Check this guide first
2. Review template configuration
3. Test with simple template
4. Check ERPNext logs
5. Contact your administrator

**Happy Reporting!** 📊
