# AI-OuYi Web Frontend

Vue 3 + Vite + TypeScript frontend for the AI-OuYi Web management system.

Production-style local entrypoint:

```bash
npm run build
cd ../..
.venv/bin/python web/backend/run_api.py
```

Open `http://127.0.0.1:8123/`.

Optional frontend-only development server:

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

The Vite proxy sends `/api/*` requests to the fixed backend API port `http://127.0.0.1:8123`.
