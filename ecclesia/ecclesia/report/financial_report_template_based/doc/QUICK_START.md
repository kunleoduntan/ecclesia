# 🚀 Quick Start Guide - 10 Minutes to Your First Report

Get your flexible financial reporting system up and running in just 10 minutes!

---

## ⏱️ Time Breakdown
- **2 min** - Install DocTypes
- **2 min** - Run Migration
- **2 min** - Explore Templates
- **2 min** - Run First Report
- **2 min** - Export to Excel

**Total: 10 minutes** ⚡

---

## Step 1: Install DocTypes (2 minutes)

### A. Copy DocType Files

```bash
# Navigate to your app
cd ~/frappe-bench/apps/ecclesia

# Create doctype directories
mkdir -p ecclesia/ecclesia/doctype/financial_report_template
mkdir -p ecclesia/ecclesia/doctype/financial_report_line

# Copy JSON files (assuming files are in /tmp)
cp /tmp/financial_report_template.json ecclesia/ecclesia/doctype/financial_report_template/
cp /tmp/financial_report_line.json ecclesia/ecclesia/doctype/financial_report_line/
```

### B. Migrate and Restart

```bash
cd ~/frappe-bench
bench migrate
bench restart
```

### ✅ Checkpoint
Open ERPNext → Search for "Financial Report Template" → List should appear (empty for now)

---

## Step 2: Run Migration Script (2 minutes)

### A. Copy Migration Script

```bash
cd ~/frappe-bench/apps/ecclesia
mkdir -p ecclesia/ecclesia/report/financial_report_dynamic

# Copy all Python files
cp /tmp/financial_report_dynamic.py ecclesia/ecclesia/report/financial_report_dynamic/
cp /tmp/excel_export.py ecclesia/ecclesia/report/financial_report_dynamic/
cp /tmp/migration_script.py ecclesia/ecclesia/report/financial_report_dynamic/
cp /tmp/financial_report_template_based.json ecclesia/ecclesia/report/financial_report_dynamic/
```

### B. Run Migration

```bash
bench console
```

In the console:
```python
from ecclesia.ecclesia.report.financial_report_dynamic.migration_script import run_migration
run_migration()
```

### C. Install Excel Dependencies

```bash
bench pip install openpyxl
```

### ✅ Checkpoint
You should see:
```
✓ Template 'Standard P&L Template' created successfully with 18 lines
✓ Template 'Standard Balance Sheet' created successfully with 12 lines

MIGRATION COMPLETED SUCCESSFULLY!
```

---

## Step 3: Explore Templates (2 minutes)

### A. Open Template List

1. Go to **ERPNext**
2. Search for **"Financial Report Template"**
3. Click to open list

You should see:
- ✅ Standard P&L Template
- ✅ Standard Balance Sheet

### B. Open Standard P&L Template

Click on **"Standard P&L Template"**

**What to notice:**
- Template name and type
- Excel formatting settings (colors, decimal places)
- Report lines table with:
  - Line numbers (10, 20, 30...)
  - Line labels (Revenue, Cost of Sales, Gross Profit...)
  - Line types (Account Aggregate, Calculated)
  - Formulas (REV - COS for Gross Profit)

### C. Examine a Few Lines

**Line 10 - Revenue:**
- Type: Account Aggregate
- Mapping: Financial Reporting Group
- Group: "Brokerage income"

**Line 30 - Gross Profit:**
- Type: Calculated
- Formula: `REV - DCE`
- Styling: Bold, Total Row

**Line 70 - EBITDA:**
- Type: Calculated
- Formula: `GP - ADMIN - REPAIR - SELL - EMP`
- Styling: Bold, Subtotal Row

### ✅ Checkpoint
You understand:
- Templates define report formats
- Lines can aggregate accounts or calculate
- Formulas reference line codes

---

## Step 4: Run Your First Report (2 minutes)

### A. Create Report File

You need to register the report in ERPNext.

**Option 1: Via UI (Recommended)**
1. Go to **Report** list
2. Click **New**
3. Fill in:
   - Report Name: "Financial Report - Template Based"
   - Ref DocType: "GL Entry"
   - Report Type: "Script Report"
   - Module: "Ecclesia"
   - Is Standard: Yes
4. In Roles table, add:
   - System Manager
   - Accounts Manager
   - Accounts User
5. Save

**Option 2: Copy JSON**
```bash
mkdir -p ~/frappe-bench/apps/ecclesia/ecclesia/ecclesia/report/financial_report_template_based
cp /tmp/financial_report_template_based.json ~/frappe-bench/apps/ecclesia/ecclesia/ecclesia/report/financial_report_template_based/

bench migrate
```

### B. Run the Report

1. Go to **Reports** → Search "Financial Report - Template Based"
2. Fill in filters:
   - **Template**: Standard P&L Template
   - **Company**: [Your Company]
   - **Year**: 2026 (or current year)
   - **Frequency**: Monthly
   - **Show Budget**: No (for now)
3. Click **Run** or **Refresh**

### C. View Results

You should see:
- Account Name column
- Monthly columns (Jan, Feb, Mar...)
- Last Year columns (if you have prior year data)
- Variance % columns
- YTD totals

**Example Output:**
```
Account Name              | Jan      | Jan LY   | Var%  | ... | YTD      |
--------------------------|----------|----------|-------|-----|----------|
Brokerage Income          | 500,000  | 450,000  | 11.1% | ... | 500,000  |
Direct Commission Exp     | 200,000  | 180,000  | 11.1% | ... | 200,000  |
Gross Profit              | 300,000  | 270,000  | 11.1% | ... | 300,000  |
...
```

### ✅ Checkpoint
You can see your financial data in the new template format!

---

## Step 5: Export to Excel (2 minutes)

### A. Export Report

1. With report displayed, click **Menu** (three dots)
2. Click **Export**
3. Select **Excel**

**OR**

Use the export function directly:
```python
# In bench console
from ecclesia.ecclesia.report.financial_report_dynamic.excel_export import get_excel_file

filters = {
    'template': 'Standard P&L Template',
    'company': 'Your Company',
    'year': 2026,
    'frequency': 'Monthly'
}

# This would be called by ERPNext export
```

### B. Open Excel File

Download and open the Excel file.

**What you'll see:**
- 📊 **Report Header**
  - Company name
  - Period and year
  - Generation timestamp

- 🎨 **Formatted Headers**
  - Blue background
  - Bold text
  - Borders

- 📈 **Data Rows**
  - Total rows: Gray background, bold
  - Subtotal rows: Light gray background
  - Calculated rows: Bold text
  - Proper alignment
  - Thousands separators
  - Negative values in red

- 🔒 **Frozen Panes**
  - Header row frozen
  - Scroll data while headers stay visible

### C. Admire the Formatting!

**Professional features:**
✅ Color-coded headers  
✅ Total rows highlighted  
✅ Borders and alignment  
✅ Currency formatting  
✅ Percentage columns  
✅ Auto-sized columns  
✅ Frozen headers  

### ✅ Checkpoint
You have a beautiful, professional Excel export!

---

## 🎉 Congratulations!

You've successfully:
1. ✅ Installed the Financial Report Template system
2. ✅ Created sample templates
3. ✅ Understood how templates work
4. ✅ Run your first report
5. ✅ Generated a beautiful Excel export

**Time taken:** ~10 minutes ⏱️

---

## 🎯 What's Next?

### Next 10 Minutes: Test with Budget

1. **Create a Budget Plan**
   - Go to Budget Plan list
   - Create new budget
   - Add monthly amounts for some accounts

2. **Run Report with Budget**
   - Same report
   - Check "Show Budget"
   - Select your Budget Plan
   - See budget variance columns!

### Next Hour: Create Custom Template

1. **Clone Standard P&L**
   - Open template
   - Menu → Duplicate
   - Rename to "My Custom P&L"

2. **Modify Lines**
   - Add new expense categories
   - Change account mappings
   - Adjust formulas

3. **Test Your Template**
   - Run report with new template
   - Export to Excel
   - Share with team!

### Next Day: Master the System

1. **Read IMPLEMENTATION_GUIDE.md**
   - Detailed configuration guide
   - All 5 mapping methods
   - Formula syntax
   - Troubleshooting

2. **Create Templates for Different Needs**
   - Board Report (summary)
   - Management Report (detailed)
   - Tax Report (compliance)
   - Department Reports (by cost center)

3. **Train Your Team**
   - Show finance team how to use
   - Let them create own templates
   - Eliminate IT dependency!

---

## 📚 Quick Reference

### Common Tasks

| Task | Location |
|------|----------|
| View Templates | Search "Financial Report Template" |
| Create Template | New → Financial Report Template |
| Clone Template | Open template → Menu → Duplicate |
| Run Report | Reports → Financial Report - Template Based |
| Export Excel | Report → Menu → Export → Excel |

### Key Concepts

| Concept | Description |
|---------|-------------|
| Template | Complete report format definition |
| Line | Single row in report (account or calculation) |
| Line Code | Short code for formulas (REV, COS, GP) |
| Mapping Method | How to select accounts (5 types) |
| Formula | Calculation using line codes (REV - COS) |

### Mapping Methods

| Method | Example | When to Use |
|--------|---------|-------------|
| Account Range | 7000 to 7599 | Sequential numbering |
| Number Pattern | 7000-7599 or 7% | Pattern matching |
| Specific Accounts | Sales, Service | Cherry-pick accounts |
| Reporting Group | Brokerage income | Existing categorization |
| Root Type | Income | All of one type |

---

## 🐛 Quick Troubleshooting

### Report Not Found
**Problem:** Can't find report in list  
**Solution:** Run `bench migrate` and restart

### Template Empty
**Problem:** No templates in list  
**Solution:** Run migration script again

### No Data in Report
**Problem:** Report shows no values  
**Solution:** 
- Check company has GL entries
- Verify year has transactions
- Check account mappings match your chart of accounts

### Excel Export Fails
**Problem:** Export button doesn't work  
**Solution:** Install openpyxl: `bench pip install openpyxl`

---

## 💡 Pro Tips

### Tip 1: Start Simple
Begin with the migrated templates. Don't customize until you understand how they work.

### Tip 2: Clone, Don't Create
Always clone existing templates rather than creating from scratch. Much faster!

### Tip 3: Test Line by Line
When creating templates, add lines one at a time and test. Easier to debug.

### Tip 4: Use Meaningful Codes
Line codes should be obvious:
- `REV` for Revenue
- `COS` for Cost of Sales  
- `GP` for Gross Profit
- `EBITDA` for EBITDA

### Tip 5: Document Formulas
Add comments in template description explaining complex formulas.

---

## 📞 Need Help?

1. **Check documentation**
   - README.md - Overview
   - IMPLEMENTATION_GUIDE.md - Detailed guide
   - This file - Quick start

2. **Check ERPNext logs**
   ```bash
   tail -f ~/frappe-bench/logs/bench-start.log
   ```

3. **Test with simple template**
   - Use migrated templates first
   - Add complexity gradually

4. **Contact administrator**
   - Share template configuration
   - Share error messages
   - Provide sample data

---

## 🎊 You're Ready!

You now have:
- ✅ A working financial reporting system
- ✅ Sample templates to learn from
- ✅ Beautiful Excel exports
- ✅ Foundation to build on

**Go forth and create amazing reports!** 🚀

---

**Remember:** The system is designed to be **finance-team friendly**. You shouldn't need a developer for day-to-day use. Explore, experiment, and enjoy the flexibility!

**Happy Reporting!** 📊
