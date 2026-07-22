/**
 * CRA dev server proxy configuration.
 *
 * Proxies /api requests to the Django backend so the frontend
 * and API are on the same origin. This avoids cross-origin cookie
 * issues (SameSite, CORS credentials) during development.
 *
 * Inside Docker: target is http://django:8000
 * Outside Docker: target is http://localhost:8000
 * Override via API_PROXY_TARGET env var.
 *
 * Connection pooling is configured to prevent Chromium's per-origin
 * 6-connection limit from being exhausted by stale HMR WebSocket
 * connections during E2E test runs. See: EP01/EP02/PS01/PMS03.
 */
const { createProxyMiddleware } = require('http-proxy-middleware');
const http = require('http');

// Inside Docker the backend is at http://django:8000 (Docker service name).
// Set API_PROXY_TARGET env var to override (e.g., http://localhost:8000 for local dev).
const TARGET = process.env.API_PROXY_TARGET || 'http://django:8000';

// HTTP agent with connection pooling — each proxied request reuses
// existing sockets instead of opening a new TCP connection.
const proxyAgent = new http.Agent({
  keepAlive: true,
  maxSockets: 20,
  maxFreeSockets: 10,
  timeout: 30000,
  keepAliveMsecs: 30000,
});

module.exports = function (app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: TARGET,
      changeOrigin: true,
      agent: proxyAgent,
      proxyTimeout: 30000,
      timeout: 30000,
    }),
  );
};
