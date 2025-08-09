# Task: Implement Authentication Middleware for v4 Endpoints

## Description

Create authentication middleware for the v4 endpoints that verifies JWT tokens obtained from the v3 authentication endpoint. This middleware will ensure that only authenticated users can access the v4 endpoints.

## Requirements

1. Implement middleware that verifies JWT tokens
2. Extract project information from the token
3. Handle error cases (missing token, invalid token, expired token)
4. Ensure compatibility with the existing v3 authentication endpoint

## Implementation Details

- Create a new file at `agentops/api/middleware/auth.py`
- Implement a FastAPI dependency that verifies JWT tokens
- Extract project information from the token
- Handle error cases (missing token, invalid token, expired token)
- Ensure compatibility with the existing v3 authentication endpoint

## Integration with v4 Endpoints

- All v4 endpoints should use this middleware to verify authentication
- The middleware should extract project information from the token and make it available to the endpoint handlers

## Error Handling

- Return appropriate HTTP status codes for authentication errors:
  - 401 Unauthorized: Missing or invalid token
  - 403 Forbidden: Token does not have permission to access the requested resource

## Testing

- Create unit tests for the middleware
- Test with valid and invalid tokens
- Test with expired tokens
- Test with tokens that do not have permission to access the requested resource

## Dependencies

- Use the existing JWT verification function from `agentops/api/routes/v3.py`

## Estimated Time

2-3 hours
