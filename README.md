# InvoiceRecon

AI-powered invoice reconciliation for small law firms. Automatically match invoices against Clio and MyCase time entries, detect discrepancies, and save 20+ hours per month.

## The Problem

Small law firms (2-10 lawyers) spend 20-30 hours every month manually reconciling invoices against time tracking software. That's $8,000+ in junior associate salary for boring data entry work.

## The Solution

InvoiceRecon uses Claude AI to:
- **Extract invoice data from PDFs** with 95%+ accuracy
- **Automatically match** invoice line items to time entries
- **Detect discrepancies** like missing time, rate mismatches, and unbilled expenses
- **Generate reports** for partners and clients

## Tech Stack

- **Backend:** Django 5.x, Python 3.12+
- **Database:** PostgreSQL
- **AI:** Anthropic Claude API
- **Integrations:** Clio, MyCase, Stripe
- **Frontend:** Django Templates, HTMX, Tailwind CSS, Alpine.js
- **Hosting:** Railway

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL (or SQLite for development)
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/ryanpate/invoicerecon.git
cd invoicerecon

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Environment Variables

See `.env.example` for all required environment variables:

- `SECRET_KEY` - Django secret key
- `ANTHROPIC_API_KEY` - Claude API key
- `STRIPE_*` - Stripe payment keys
- `CLIO_*` - Clio OAuth credentials
- `MYCASE_*` - MyCase OAuth credentials

## Deployment (Railway)

This project is configured for one-click Railway deployment:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

Required Railway services:
- PostgreSQL database
- Redis (for Celery)

## Project Structure

```
invoicerecon/
├── config/                 # Django settings
├── apps/
│   ├── accounts/          # User authentication & firms
│   ├── invoices/          # Invoice processing & AI extraction
│   ├── integrations/      # Clio, MyCase connections
│   ├── reconciliation/    # Matching engine
│   ├── billing/           # Stripe subscriptions
│   └── dashboard/         # Main UI
├── templates/             # HTML templates
└── static/               # CSS, JS, images
```

## Pricing

- **Starter** ($299/month): 50 invoices, 1 integration
- **Professional** ($499/month): 200 invoices, unlimited integrations
- **Enterprise** ($999/month): Unlimited everything

## License

Proprietary - All rights reserved.

## Contact

- Email: admin@invoicerecon.app
- GitHub: https://github.com/ryanpate/invoicerecon
