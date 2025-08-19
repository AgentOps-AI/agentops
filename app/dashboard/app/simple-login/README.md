# Simple Login (Development/Testing Only)

## Purpose 🎯

This page (`/simple-login`) provides a UI variation for initiating the standard federated login flows (e.g., Google, GitHub) and testing API calls post-authentication. It is intended **exclusively for local development and automated testing (e.g., Cypress E2E tests)**.

It allows developers and tests to quickly authenticate using the normal OAuth providers without navigating through the full main application sign-in UI (`/signin`).

**⚠️ NOTE: While this page uses the standard secure OAuth flows, it represents a developer-focused entry point. It should ideally be disabled or inaccessible in production builds to avoid potential confusion or unintended access.**

## Mechanism ⚙️

The simple login page works by:

1.  Presenting buttons for OAuth providers (e.g., Google, GitHub).
2.  When a provider button is clicked, it calls the backend `/auth/oauth` endpoint, instructing it to initiate the standard OAuth flow for that provider, setting `/simple-login` as the redirect target after successful authentication with the provider.
3.  The backend responds with the provider's authentication URL, and the frontend redirects the user to that external URL.
4.  After the user authenticates with the provider (e.g., Google), the provider redirects back to `/simple-login`.
5.  The standard authentication handling (Supabase client-side listeners or backend callback processing) takes over to establish the user session and set the `session_id` cookie, just as it would for the main `/signin` flow.
6.  Once authenticated, the page provides buttons to test various authenticated API endpoints.

## Usage 🧑‍💻

-   **Local Development:** Navigate directly to `/simple-login` in your browser when running the development server locally. Click the desired OAuth provider button to sign in.

## Security Considerations 🔒

-   **Standard OAuth Security:** The authentication flow itself relies on the security of the configured OAuth providers (Google, GitHub) and the backend's handling of the OAuth callback and session creation, which is the same as the main sign-in flow.
-   **Production Exposure:** The primary consideration is preventing this developer-focused route from being accessible or discoverable in production. Ensure build processes, environment variables, or feature flags restrict access to this page in production deployments. 