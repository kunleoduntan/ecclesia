# Contact Us Web Integration — Setup Guide
## Ecclesia App / Value Impacts Consulting

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  ERPNext / Ecclesia                      │
│                                                          │
│  Web Form Settings (DocType — one record per company)    │
│  ┌─────────────┬──────────────┬──────────────────────┐  │
│  │ vic-main    │ client-a     │ client-b-portal       │  │
│  │ VIC Website │ Client A Co. │ Client B Ltd          │  │
│  └─────────────┴──────────────┴──────────────────────┘  │
│          │                                               │
│   get_form_config?key=xxx   (guest GET)                  │
│   receive_contact_form      (guest POST)                 │
│          │                                               │
│  Contact Us DocType  ←── linked_company per form_key    │
└─────────────────────────────────────────────────────────┘
         ↑                          ↑
   website A                  website B
  WF_KEY="vic-main"       WF_KEY="client-a"
```

### What each website HTML embeds (the ONLY two lines that change)
```js
const WF_HOST = "https://erp.yourcompany.com";
const WF_KEY  = "vic-main";

const WF_HOST = "https://erpnext-159343-0.cutsttey.net";
const WF_KEY  = "vic-main";  // must match the form_key you created in Web Form Settings
```

Everything else — branding, fields, options, success messages, assignment
strategy — is managed in ERPNext and served dynamically.

---

## File Structure

```
ecclesia/
├── api/
│   └── contact_intake.py              ← All API endpoints + AI engine
├── doctype/
│   ├── web_form_settings/
│   │   ├── web_form_settings.json     ← DocType definition
│   │   └── web_form_settings.js      ← Client JS (buttons, slug formatter)
│   └── contact_us/
│       ├── contact_us.json            ← DocType definition
│       └── contact_us.js             ← Client JS (reassign, convert)
website/
└── contact.html                       ← Config-driven embeddable form
```

---

## API Endpoints

| Method | URL | Auth | Purpose |
|--------|-----|------|---------|
| GET | `...get_form_config?key={key}` | Guest | Load branding + field config |
| POST | `...receive_contact_form` | Guest | Submit form, create doc, assign |
| POST | `...reassign_lead` | User | Re-run AI assignment from UI |
| POST | `...test_form_submission` | User | Fire synthetic test from UI |

---

## Setup Steps

### 1. Deploy API + DocType files
```bash
cp contact_intake.py      /apps/ecclesia/ecclesia/api/
cp -r web_form_settings/  /apps/ecclesia/ecclesia/doctype/
cp -r contact_us/         /apps/ecclesia/ecclesia/doctype/

bench --site your-site.com migrate && bench restart
```

### 2. Add fields to Contact Us DocType
- `web_form_key`     (Data, read-only)
- `linked_company`   (Link → Company, read-only)
- `industry`         (Select)
- `estimated_budget` (Select)
- `assigned_to`      (Link → User)
- `assigned_to_name` (Data, read-only)
- `ai_reasoning`     (Small Text, read-only)
- `submission_date`  (Datetime, read-only)

### 3. Set AI API key in site_config.json
```json
{ "anthropic_api_key": "sk-ant-xxxxxxxx" }
```

### 4. Create a Web Form Settings record
ERPNext → Ecclesia → Web Form Settings → New

| Field               | Example                          |
|---------------------|----------------------------------|
| Form Key            | `vic-main`                       |
| Form Label          | `Value Impacts — Main Website`   |
| Company             | `Value Impacts Consulting`       |
| Allowed CORS Origin | `https://valueimpacts.com.ng`    |
| Assignment Strategy | `AI + Load Balancing`            |
| Brand Accent Colour | `#c8972a`                        |

### 5. Embed on website
Set two variables in `contact.html`:
```js
const WF_HOST = "https://erp.yourcompany.com";
const WF_KEY  = "vic-main";
```

### 6. Configure CORS
```json
{ "allow_cors": "https://valueimpacts.com.ng" }
```

---

## Adding a Second Company

1. New **Web Form Settings** record with a new `form_key`
2. Link to second company, set second CORS origin
3. Drop HTML on second website with new `WF_KEY`

No code changes. No redeployment.

---

## Assignment Strategies

| Strategy            | Behaviour                                                   |
|---------------------|-------------------------------------------------------------|
| AI + Load Balancing | AI matches industry/message, weighted by open lead count    |
| Load Balancing Only | Assigns to salesperson with fewest open leads               |
| Round Robin         | Rotates sequentially through salespeople                    |
| Fixed Salesperson   | Always assigns to one specific user                         |

---

## Testing

Use **Tools → Send Test Submission** inside any Web Form Settings record,
or via curl:
```bash
curl -X POST "https://erp.site.com/api/method/ecclesia.api.contact_intake.receive_contact_form" \
  -H "Content-Type: application/json" \
  -H "Origin: https://valueimpacts.com.ng" \
  -d '{
    "form_key": "vic-main",
    "full_name": "Emeka Obi",
    "email": "emeka@techco.ng",
    "subject": "ERPNext for our 300-staff firm",
    "message": "We need full ERP implementation including payroll and inventory.",
    "industry": "Manufacturing",
    "estimated_budget": "₦10M – ₦50M"
  }'
```
