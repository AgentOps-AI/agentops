# AgentOps Authentication System

## Architecture Overview

The AgentOps authentication system combines Supabase for identity management with a Redis-backed session store. Authentication flows begin when users authenticate through Supabase, which returns JWT tokens containing user information. Our system then creates its own session, stores the mapping in Redis, and issues an HTTP-only cookie containing a signed session identifier. This approach provides the security benefits of server-side sessions while leveraging Supabase's robust identity platform.

## Session Management

The `Session` class provides a clean interface to the Redis backend. Each session is identified by a UUID and contains a reference to the authenticated user. The interface is deliberately minimal:

Server-side session storage was chosen over client-side JWT tokens because it allows for immediate session invalidation and extension, neither of which is possible with self-contained JWTs. The Redis backend provides fast access with automatic TTL management.

## Authentication Flow

The authentication flow consists of two distinct steps, designed to securely handle Supabase tokens:

1. The `auth_callback` view receives the hash fragment from Supabase (containing access and refresh tokens) and renders a page with strict Content-Security-Policy that extracts these tokens.

2. The client-side JavaScript forwards these tokens to `auth_session`, which validates the Supabase JWT, creates a new session, and sets a secure HTTP-only cookie containing our signed session ID.

This approach prevents tokens from appearing in server logs or browser history, reducing the risk of token leakage.

## Request Authentication

All API endpoints require authentication by default through the `AuthenticatedRoute` class. Only routes explicitly marked with the `@public_route` decorator are accessible without authentication. This "secure by default" pattern prevents accidentally exposing sensitive endpoints.

The middleware extracts the session cookie, validates it, retrieves the session from Redis, and provides it to the route handler via `request.state.session`. When enabled, session expiration is automatically extended on each authenticated request.

## Security Considerations

The security model specifically avoids client-side JWTs because they cannot be invalidated, their expiration cannot be extended, and they present risks if stored in localStorage. Instead, HTTP-only cookies with the Secure and SameSite=strict flags prevent JavaScript access and CSRF attacks.

Content Security Policy with nonces is implemented on authentication pages to prevent XSS attacks, and all cookies are scoped to specific domains to limit exposure. The session store architecture allows for immediate invalidation of all sessions if needed.

## Cookie Management

The authentication system uses a minimalist cookie approach to maintain user sessions securely. Understanding how these cookies work is important for developers integrating with the AgentOps API.

### How Session Cookies Work

When a user authenticates:

1. A server-side session is created and stored in Redis
2. A session identifier (UUID) is generated
3. This identifier is JWT-encoded with our internal secret
4. The encoded token is stored in an HTTP-only cookie

For subsequent requests:

1. The cookie is automatically sent with each request to the API
2. The middleware extracts and validates the cookie
3. The session ID is decoded and used to retrieve the full session from Redis
4. If authentication is successful, the session object is made available to the endpoint handler

### Cookie Properties

Our session cookies are configured with several important security properties:

- **HTTP-only**: Cannot be accessed by JavaScript, protecting against XSS attacks
- **Secure**: Only sent over HTTPS in production environments
- **SameSite=strict**: Only sent for same-site requests, preventing CSRF attacks
- **Domain-scoped**: Limited to the API domain
- **Expiration**: Automatically expires after the configured session lifetime

### Client Integration Considerations

When developing a client application that interacts with AgentOps:

- There's no need to manually extract or send tokens - browsers handle cookies automatically
- Authentication state persists across page reloads as long as the session is valid
- Logging out requires an explicit call to the logout endpoint, which clears the cookie
- Cross-domain requests require credentials: `credentials: 'include'` (fetch) or `withCredentials: true` (axios)
- Mobile apps and non-browser clients need to handle cookies appropriately for their platform

### Cross-Origin and SameSite Cookies

The API server includes CORS configuration that allows requests from the main application domain (`APP_DOMAIN`). This works with SameSite=strict cookies through the following mechanism:

- The CORS `allow_origins` list includes the main application URL (`APP_URL`)
- The `allow_credentials` flag is set to `True`, permitting cookies to be included in cross-origin requests
- Clients must explicitly include credentials in their requests
- The browser will then include cookies with cross-origin requests to trusted domains

## Implementing Authentication in an Application

The `AuthenticatedRoute` class enforces authentication for all endpoints by default, while the `@public_route` decorator allows specific endpoints to be accessible without authentication.

```python
from fastapi import FastAPI, APIRouter, Request
from uuid import UUID
from agentops.auth.middleware import AuthenticatedRoute
from agentops.auth.views import public_route
from agentops.auth.session import Session

app = FastAPI()

# Create a router with the AuthenticatedRoute class
router = APIRouter(route_class=AuthenticatedRoute)

# Protected endpoint (requires authentication)
@router.get("/protected-endpoint")
async def protected_endpoint(request: Request):
    session: Session = request.state.session
    user_id: UUID = session.user_id
    return {"message": f"Hello, user {str(user_id)}!"}

# Public endpoint (no authentication required)
@router.get("/public-endpoint")
@public_route
async def public_endpoint():
    return {"message": "This endpoint is accessible without authentication"}

# Include the router in your application
app.include_router(router)
```

With this implementation:

1. All routes on the router require authentication by default
2. The middleware extracts and validates the session cookie from requests
3. For authenticated endpoints, `request.state.session` is populated with the user's session
4. Session expiration is automatically extended when enabled
5. Routes with the `@public_route` decorator are accessible without authentication
