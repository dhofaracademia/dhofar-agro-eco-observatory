# Security review and hardening — 2026-10-03

Scope: tracked application code, deployment configuration, catalogue API, dependency
advisories, and a small number of read-only production requests. No load test,
credential attack, account takeover simulation, or assertion of complete security.

## Observed before the change

- Production HTML had HSTS, but no CSP, frame restriction, nosniff or permissions policy.
- `/api/satellite-scenes` was a fixed, read-only lookup (no user-controlled upstream URL),
  but every request performed a new provider request with no cache/coalescing.
- HTTPS alone was sufficient for catalogue image URLs. Saved gallery records were
  trusted without runtime validation. This allowed unintended image destinations;
  it is not evidence of server-side request forgery or an observed compromise.
- `/.env` and `/.git/config` returned the SPA HTML, **not secrets or repository data**.
- Existing React rendering and the map's DOM/textContent popup construction do not
  interpolate satellite metadata as executable HTML.
- npm audit reported zero known vulnerabilities. The local Python audit initially
  flagged the environment's pip installer, not an internet-facing Python service.
  After upgrading pip, the installed pipeline/audit environment reported no known
  vulnerabilities. GitHub’s Python 3.11 runner also exposed an outdated setuptools
  (79.0.1; advisory fix 83.0.0), so all Python jobs upgrade setuptools before
  installing dependencies. Pattern scanning tracked text found no private keys, GitHub
  token patterns, or AWS access-key IDs; this is not a full historical secret audit.

## Applied controls

- Enforced CSP: same-origin scripts/connections; restricted image/font/style origins;
  no objects, forms, base URL override, or embedding by other sites. Inline styles
  remain allowed for Leaflet/React styling, but inline scripts and eval do not.
- Added nosniff, DENY framing, referrer policy and disabled unused browser permissions.
  Both Vercel configurations share the policy. Platform HSTS is left intact.
- Excluded hidden paths from SPA fallback. Public data retains intentional open CORS.
- Restricted catalogue and saved-preview URLs to explicit trusted host lists,
  HTTPS, no credentials, no nonstandard port. Normalized and bounded saved records.
- Fixed upstream URL and bbox retained; redirects rejected; timeout retained; provider
  body limited to 1 MiB. Malformed records cannot crash field extraction.
- API rejects mutation methods, query variants and cross-site browser fetches.
  A 60-second public CDN cache and per-instance single-flight cache reduce repeated
  provider calls. Failures are not cached publicly; 15-second per-instance backoff
  limits retry storms. Error messages do not expose upstream internals.
- Pinned Actions to verified commit SHAs, disabled persisted checkout credentials in
  read-only quality/audit jobs, upgraded pip before installations, and added weekly
  dependency audits and Dependabot update checks.
- Regression tests cover URL allowlists, malformed/oversized responses, query/method
  rejection, concurrent lookup coalescing, expiry/backoff, enforced CSP on public
  routes, blocked inline script injection, and hostile saved gallery metadata.

## Remaining account-level work and limits

- Per-instance caching is **not** a distributed per-IP rate limiter and does not
  guarantee DDoS or cost protection. This change does not configure Vercel WAF rules.
  Suggested next step: inspect existing rules and stage a GET `/api/satellite-scenes`
  rate rule in logging mode, then tune from actual traffic before enforcement.
- GitHub/Vercel MFA, collaborator access, branch protection, secret-scanning settings,
  and production deployment permissions were not changed or certified by this review.
- No independent penetration test or historical credential investigation was performed.
- Dependency scanning detects published advisories, not unknown vulnerabilities.

References:
- https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/CSP
- https://vercel.com/docs/caching/cache-control-headers
- https://vercel.com/docs/vercel-firewall
