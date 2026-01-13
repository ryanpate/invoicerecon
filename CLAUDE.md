# InvoiceRecon - Law Firm Invoice Reconciliation SaaS

## Project Overview

**Mission:** Build an AI-powered invoice reconciliation platform for small law firms (2-10 lawyers) that automates the painful monthly process of matching invoices against time tracking software, expense reports, and client retainers.

**Target Market:** 450,000+ law firms in the US alone. Targeting small firms drowning in manual reconciliation work.

**Value Proposition:** Replace 20-30 hours of junior associate work ($8,000/month cost) with automated AI reconciliation for $500/month.

---

## Business Economics

| Metric | Value |
|--------|-------|
| Build Cost | ~$5,000 |
| Monthly Price | $500/firm |
| API Cost per Customer | ~$20/month |
| Gross Margin | 96% |
| Break-even | 11 customers |
| Target MRR | $5,000+ |
| Market Size (0.1% capture) | 450 firms = $225K ARR |

---

## Tech Stack

### Backend
- **Framework:** Django 5.x (Python 3.12+)
- **Database:** PostgreSQL (Railway managed)
- **Task Queue:** Celery + Redis (for async PDF processing)
- **API:** Django REST Framework
- **AI/ML:** Anthropic Claude API (document parsing, data extraction)

### Frontend
- **Framework:** Django Templates + HTMX (for interactivity)
- **CSS:** Tailwind CSS 3.x
- **Components:** Alpine.js for lightweight reactivity
- **Charts:** Chart.js for reconciliation dashboards

### Infrastructure
- **Hosting:** Railway
- **Repository:** https://github.com/ryanpate/invoicerecon
- **CDN:** Railway (static files) or Cloudflare
- **File Storage:** AWS S3 or Railway Volumes (for invoice PDFs)
- **Email:** SendGrid or Resend

### Integrations
- **Clio** (legal practice management - largest market share)
- **MyCase** (popular with small firms)
- **Stripe** (billing and subscriptions)
- **QuickBooks** (optional - expense data)

---

## Core Features (MVP)

### Phase 1: Invoice Processing Engine
1. **PDF Upload & Parsing**
   - Drag-and-drop invoice upload
   - Multi-page PDF support
   - Claude API for intelligent data extraction
   - Extract: Client name, matter number, date, line items, amounts, hours

2. **Data Extraction Pipeline**
   - Structured JSON output from invoices
   - Confidence scoring for extracted fields
   - Human review queue for low-confidence extractions

### Phase 2: Integration Layer
1. **Clio Integration**
   - OAuth2 authentication
   - Pull time entries, matters, clients
   - Sync billing rates and expense categories

2. **MyCase Integration**
   - Similar OAuth2 flow
   - Time entry and matter synchronization

### Phase 3: Reconciliation Engine
1. **Matching Algorithm**
   - Match invoice line items to time entries
   - Fuzzy matching for client/matter names
   - Date range validation
   - Rate verification

2. **Discrepancy Detection**
   - Missing time entries
   - Rate mismatches
   - Unbilled expenses
   - Overbilling detection
   - Retainer balance issues

3. **Reporting**
   - Per-client reconciliation reports
   - Monthly summary dashboards
   - Export to PDF/Excel
   - Email notifications for discrepancies

### Phase 4: User Experience
1. **Dashboard**
   - Overview of pending reconciliations
   - Quick stats: invoices processed, discrepancies found, time saved
   - Recent activity feed

2. **Reconciliation Workflow**
   - Step-by-step guided process
   - One-click approve/flag items
   - Bulk actions for efficiency

---

## Pricing Tiers

### Starter - $299/month
- Up to 50 invoices/month
- 1 practice management integration
- Email support
- Basic reporting

### Professional - $499/month (Target tier)
- Up to 200 invoices/month
- Unlimited integrations
- Priority support
- Advanced analytics
- Custom report templates

### Enterprise - $999/month
- Unlimited invoices
- Dedicated account manager
- Custom integrations
- API access
- White-label options

---

## Project Structure

```
invoicerecon/
├── CLAUDE.md                 # This file - project documentation
├── README.md                 # Public readme
├── requirements.txt          # Python dependencies
├── Dockerfile               # Railway deployment
├── railway.json             # Railway config
├── manage.py                # Django management
├── .env.example             # Environment template
│
├── config/                  # Django project settings
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── development.py  # Dev settings
│   │   └── production.py   # Production settings
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── accounts/           # User authentication & firms
│   │   ├── models.py       # User, Firm, Subscription
│   │   ├── views.py
│   │   └── ...
│   │
│   ├── invoices/           # Invoice processing
│   │   ├── models.py       # Invoice, LineItem, Extraction
│   │   ├── services/
│   │   │   ├── parser.py   # Claude API integration
│   │   │   └── extractor.py
│   │   └── ...
│   │
│   ├── integrations/       # Clio, MyCase connections
│   │   ├── models.py       # Integration, TimeEntry, Matter
│   │   ├── services/
│   │   │   ├── clio.py
│   │   │   └── mycase.py
│   │   └── ...
│   │
│   ├── reconciliation/     # Core matching engine
│   │   ├── models.py       # Reconciliation, Discrepancy
│   │   ├── services/
│   │   │   ├── matcher.py
│   │   │   └── reporter.py
│   │   └── ...
│   │
│   ├── billing/            # Stripe subscription handling
│   │   ├── models.py
│   │   ├── webhooks.py
│   │   └── ...
│   │
│   └── dashboard/          # Main UI views
│       ├── views.py
│       └── ...
│
├── templates/
│   ├── base.html
│   ├── components/         # Reusable UI components
│   ├── accounts/
│   ├── dashboard/
│   ├── invoices/
│   ├── reconciliation/
│   └── marketing/          # Landing pages
│       ├── home.html
│       ├── pricing.html
│       └── features.html
│
├── static/
│   ├── css/
│   │   └── tailwind.css
│   ├── js/
│   └── images/
│
└── tests/
    ├── test_invoice_parsing.py
    ├── test_reconciliation.py
    └── ...
```

---

## Database Schema (Key Models)

### accounts.Firm
```python
class Firm(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription_tier = models.CharField(choices=TIERS)
    stripe_customer_id = models.CharField()
    monthly_invoice_limit = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
```

### invoices.Invoice
```python
class Invoice(models.Model):
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE)
    file = models.FileField(upload_to='invoices/')
    client_name = models.CharField(max_length=255)
    matter_number = models.CharField(max_length=100)
    invoice_date = models.DateField()
    total_amount = models.DecimalField()
    extraction_confidence = models.FloatField()
    status = models.CharField(choices=STATUS_CHOICES)
    raw_extraction = models.JSONField()  # Claude API response
    created_at = models.DateTimeField(auto_now_add=True)
```

### reconciliation.Discrepancy
```python
class Discrepancy(models.Model):
    reconciliation = models.ForeignKey(Reconciliation, on_delete=models.CASCADE)
    type = models.CharField(choices=DISCREPANCY_TYPES)
    # MISSING_TIME, RATE_MISMATCH, UNBILLED_EXPENSE, etc.
    invoice_line = models.ForeignKey(InvoiceLineItem)
    time_entry = models.ForeignKey(TimeEntry, null=True)
    expected_value = models.DecimalField()
    actual_value = models.DecimalField()
    difference = models.DecimalField()
    status = models.CharField(choices=['pending', 'resolved', 'ignored'])
    resolution_note = models.TextField(blank=True)
```

---

## API Endpoints

### Authentication
- `POST /api/auth/register/` - New firm signup
- `POST /api/auth/login/` - Login
- `POST /api/auth/logout/` - Logout
- `GET /api/auth/me/` - Current user

### Invoices
- `POST /api/invoices/upload/` - Upload invoice PDF
- `GET /api/invoices/` - List invoices
- `GET /api/invoices/{id}/` - Invoice detail
- `PATCH /api/invoices/{id}/` - Update extracted data

### Integrations
- `GET /api/integrations/clio/connect/` - OAuth flow start
- `GET /api/integrations/clio/callback/` - OAuth callback
- `POST /api/integrations/clio/sync/` - Trigger sync

### Reconciliation
- `POST /api/reconciliations/` - Start new reconciliation
- `GET /api/reconciliations/` - List reconciliations
- `GET /api/reconciliations/{id}/` - Reconciliation detail with discrepancies
- `PATCH /api/discrepancies/{id}/resolve/` - Mark discrepancy resolved

---

## Claude API Integration

### Invoice Parsing Prompt Template
```python
INVOICE_EXTRACTION_PROMPT = """
Analyze this legal invoice image/PDF and extract the following information in JSON format:

{
  "client_name": "Full client name",
  "matter_number": "Matter/case number",
  "invoice_number": "Invoice number",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "billing_attorney": "Attorney name",
  "line_items": [
    {
      "date": "YYYY-MM-DD",
      "description": "Work description",
      "timekeeper": "Name",
      "hours": 0.0,
      "rate": 0.00,
      "amount": 0.00,
      "type": "time|expense|flat_fee"
    }
  ],
  "subtotal": 0.00,
  "taxes": 0.00,
  "total": 0.00,
  "retainer_applied": 0.00,
  "amount_due": 0.00
}

Be precise with numbers. If a field is unclear, use null and note it in a separate "extraction_notes" field.
"""
```

---

## SEO Strategy

### Target Keywords
- "law firm invoice reconciliation software"
- "legal billing automation"
- "attorney time tracking reconciliation"
- "clio invoice matching"
- "mycase billing automation"
- "law firm billing discrepancy detection"
- "legal practice billing software"

### Content Strategy
1. **Landing Pages**
   - Homepage with clear value prop
   - Integration-specific pages (Clio, MyCase)
   - Use-case pages (small firm, solo practitioner)

2. **Blog Content**
   - "How to Reduce Billing Errors at Your Law Firm"
   - "The True Cost of Manual Invoice Reconciliation"
   - "5 Signs Your Firm Needs Billing Automation"
   - Integration guides and tutorials

3. **Technical SEO**
   - Fast page loads (< 2s)
   - Mobile responsive
   - Schema markup for SaaS product
   - Sitemap and robots.txt

---

## Launch Checklist

### Pre-Launch (Week 1-4)
- [ ] Core Django project setup
- [ ] Database models and migrations
- [ ] User authentication (django-allauth)
- [ ] Basic invoice upload and Claude parsing
- [ ] Simple dashboard UI
- [ ] Stripe integration for subscriptions
- [ ] Railway deployment pipeline

### MVP Launch (Week 5-6)
- [ ] Clio integration (OAuth + data sync)
- [ ] Basic reconciliation matching
- [ ] Discrepancy detection and reporting
- [ ] Landing page with pricing
- [ ] Email signup for waitlist
- [ ] Terms of Service / Privacy Policy

### Beta Launch (Week 7-8)
- [ ] Invite 3 law firm partners from article
- [ ] Iterate based on feedback
- [ ] MyCase integration
- [ ] Enhanced reporting features
- [ ] Onboarding flow optimization

### Public Launch (Week 9-10)
- [ ] ProductHunt launch
- [ ] Legal tech forums/communities
- [ ] LinkedIn outreach to law firm administrators
- [ ] Google Ads for high-intent keywords
- [ ] Case study from beta users

---

## Go-To-Market Strategy

### Phase 1: Validation (First 10 Customers)
1. **Direct Outreach**
   - Email the 3 law firm partners mentioned
   - LinkedIn cold outreach to law firm administrators
   - Target: "Office Manager" or "Billing Coordinator" titles

2. **Legal Communities**
   - r/LawFirm subreddit
   - Clio user forums
   - Local bar association newsletters
   - Legal tech Facebook groups

### Phase 2: Content Marketing
1. **SEO Content**
   - Publish 2 blog posts/week
   - Target long-tail legal billing keywords
   - Create comparison content (vs manual process)

2. **Partnerships**
   - Clio marketplace listing
   - MyCase integration directory
   - Legal practice consultants as referral partners

### Phase 3: Paid Acquisition
1. **Google Ads**
   - Target: "law firm billing software", "legal invoice automation"
   - Estimated CPC: $15-30 (legal vertical is expensive)
   - Focus on high-intent, conversion-optimized landing pages

2. **LinkedIn Ads**
   - Target job titles: Office Manager, Billing Coordinator, Managing Partner
   - Firm size: 2-50 employees
   - Geography: Major US legal markets (NYC, LA, Chicago, Houston)

---

## Key Metrics to Track

### Business Metrics
- MRR (Monthly Recurring Revenue)
- Customer count by tier
- Churn rate (target < 5%/month)
- LTV:CAC ratio (target > 3:1)
- Time to first reconciliation

### Product Metrics
- Invoices processed per firm
- Discrepancies caught per month
- Time saved per firm (survey)
- Claude API costs per customer
- Error rate in extraction

### Marketing Metrics
- Website traffic
- Demo requests
- Trial-to-paid conversion
- CAC by channel

---

## Risk Mitigation

### Technical Risks
- **Claude API changes:** Abstract API calls behind service layer
- **PDF parsing failures:** Human review queue + confidence scoring
- **Integration API changes:** Monitor Clio/MyCase changelogs, webhook alerts

### Business Risks
- **Low conversion:** Offer 14-day free trial, no credit card required
- **High churn:** Focus on onboarding, show time-saved metrics
- **Competition:** Move fast, build integrations as moat

---

## Development Commands

```bash
# Local development
python manage.py runserver

# Run tests
python manage.py test

# Make migrations
python manage.py makemigrations

# Deploy to Railway
railway up

# Celery worker (for async processing)
celery -A config worker -l info
```

---

## Environment Variables

```
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=invoicerecon.railway.app

# Database (Railway provides this)
DATABASE_URL=postgres://...

# Claude API
ANTHROPIC_API_KEY=your-anthropic-key

# Stripe
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Integrations
CLIO_CLIENT_ID=...
CLIO_CLIENT_SECRET=...
MYCASE_CLIENT_ID=...
MYCASE_CLIENT_SECRET=...

# Storage
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=invoicerecon-uploads

# Email
SENDGRID_API_KEY=...
```

---

## Contact & Resources

- **GitHub:** https://github.com/ryanpate/invoicerecon
- **Clio API Docs:** https://developers.clio.com/
- **MyCase API Docs:** https://developers.mycase.com/
- **Anthropic Claude API:** https://docs.anthropic.com/
- **Stripe Billing:** https://stripe.com/docs/billing

---

*Built for passive income. Solving boring problems. Making law firms efficient.*
