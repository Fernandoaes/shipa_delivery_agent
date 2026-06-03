# SHIPA Ops Dashboard (frontend)

Next.js + Tailwind + Leaflet dashboard for Shipa ops: orders, customers, and a per-order delivery map.

## Run
```bash
cp .env.example .env.local   # set API_BASE_URL + DASHBOARD_API_KEY
npm install
npm run dev                  # http://localhost:3000
```

Requires the FastAPI backend running and seeded (see repo root README). Data is fetched
server-side; the API key never reaches the browser.
