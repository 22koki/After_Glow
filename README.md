# Afterglow ✦

An intimate, constellation-inspired web experience for keeping memories, photo stories, audio and time capsules. The repo includes a lightweight frontend and a Django REST API.

## Quick start

### API

    cd backend
    python -m venv .venv
    # On Windows:
    .venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver

For local development, environment defaults are provided. Before production use, set a strong DJANGO_SECRET_KEY, DJANGO_DEBUG=0, allowed hosts and CORS origins, use HTTPS and move from SQLite to a managed database.

### Frontend

From the repository root:

    python -m http.server 5173

Open http://localhost:5173. The frontend uses http://127.0.0.1:8000/api in local development. For production, configure your reverse proxy so /api routes reach Django and uploads remain private. The frontend is intentionally dependency-free.

## Features

- An interactive, responsive constellation landing page and fictional demo
- Email/password registration and sign in
- Private universes with occasion and atmosphere choices
- Revocable guest invitation links
- Photo, note and audio memory uploads
- Owner approval for guest contributions
- Time capsules with server-enforced future unlock dates
- Private authenticated or invite-authorized attachment serving
- Initial Django API tests

## Security and deployment notes

**Important:** This is an MVP, not a production-ready privacy service. The API uses bearer tokens kept in sessionStorage and shareable invite tokens. Treat invite links as secrets. Production work needs authentication hardening, rate limiting at the edge, encrypted storage, backup and deletion policies, malware scanning, content moderation, privacy/legal review and real end-to-end browser tests. Invitations grant access to all approved memories in their universe. Files are never intended to be served through a public /media path.

The owner must save the invite link: only a hash of the invite token is retained server-side. Rotating the link revokes the old guest link. Do not commit real user data or credentials.

## Commercial roadmap

1. Recording audio directly in browser and richer star interactions
2. Secure media storage, quotas, consent controls and export/delete
3. Owner-selectable custom themes and event branding
4. Paid event universes, subscription tiers and transaction receipts
5. Production deployment, security review and accessibility testing
