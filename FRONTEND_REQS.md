# Frontend System Requirements

This document describes the requirements to build, host, and use the Blackline frontend (Vite/React), and the environment it expects at runtime.

## End‑User Requirements

- Supported browsers (latest two stable versions recommended):
  - Chrome, Edge, Firefox, Safari
  - iOS/iPadOS Safari and Chrome (recent iOS versions)
- Device: desktop or modern laptop recommended for analysis UI. Mobile is usable for browsing results, not optimized for large uploads.
- Network: stable broadband connection. Large media uploads (100–500 MB+) benefit from wired or high‑quality Wi‑Fi.
- Upload limits: governed by your backend/proxy and storage bucket policies. For Nginx, set `client_max_body_size` accordingly. For S3, ensure sufficient presigned URL expiry and bucket limits.

## Developer Build Requirements

- Node.js 18.x (matches Netlify build and CI)
- npm 9+ (or `npm ci` compatible alternative like pnpm/yarn with local adjustments)
- Disk space: ~300–400 MB for `node_modules`

Install and build:
```
cd front-end
npm ci || npm install
npm run build
```

Dev server:
```
cd front-end
npm run dev
```

## Runtime Configuration

- `VITE_API_BASE` (required): The absolute origin of the backend API, e.g. `https://api.example.com`.
  - Used by API clients in the app (see `front-end/src/utils/assetsApi.ts`, `front-end/src/state/authStore.ts`).
  - In development, you can point to `http://localhost:8000`.

How to set:
- Netlify: Site settings → Build & Deploy → Environment → `VITE_API_BASE`
- GitHub Pages CI: set as Actions Variable/Secret consumed by `.github/workflows/deploy-pages.yml`
- Local build: prefix the build command, e.g. `VITE_API_BASE=https://api.example.com npm run build`

## Hosting Requirements (Static SPA)

- Any static hosting works (Netlify, GitHub Pages, Nginx, S3+CloudFront).
- Enable SPA fallback so client‑side routing resolves to `index.html`.
  - Netlify is pre‑configured: `netlify.toml` provides `/* → /index.html`.
  - GitHub Pages workflow copies `404.html` from `index.html` to aid SPA routing.
  - Nginx: `try_files $uri /index.html;` in the root location block.
- Optional API proxy to avoid CORS:
  - Netlify: uncomment `/api/*` proxy in `netlify.toml` and set `VITE_API_BASE` to your site origin.

## CORS and Backend Expectations

- If the frontend and backend are on different origins, the backend must allow the frontend origin via CORS.
- For production, restrict CORS allow_origins to your final site domain(s).

## Security Considerations

- Authentication: the prototype stores JWT tokens in `localStorage` for convenience (see `front-end/src/state/authStore.ts`).
  - For hardened deployments, prefer backend‑managed HttpOnly cookies or an auth proxy/SSO.
  - If continuing with tokens in web storage, consider: short expirations, CSRF protections, and origin‑scoped CORS.
- Ensure TLS (HTTPS) for both frontend and backend in production to protect credentials and uploads.

## Performance Notes

- The UI streams/handles preview assets and can initiate uploads; very large files are best uploaded via S3 presigned PUT to minimize API load.
- Build output is optimized via Vite; host with a CDN for best performance.

## File References

- Vite config: `front-end/vite.config.ts`
- Netlify config: `netlify.toml`
- GitHub Pages workflow: `.github/workflows/deploy-pages.yml`
- API base usage: `front-end/src/utils/assetsApi.ts`, `front-end/src/state/authStore.ts`
