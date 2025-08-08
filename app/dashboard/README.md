> **Note:** This project uses shared development configurations (linting, formatting) defined in the repository root. Please see the [root README.md](../../README.md#development-setup) for initial setup instructions and tooling details (ESLint, Prettier).

This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Getting Started 🚀

This project uses [Bun](https://bun.sh/) as the runtime and package manager. Make sure you have it installed!

First, ensure you have the necessary environment variables set up. Copy the example file:

```bash
cp .env.example .env.local
```

Then, **edit `.env.local`** and fill in the required values.

#### Required Environment Variables

The following variables are **required** for the dashboard to function:

**Supabase Configuration:**
```bash
NEXT_PUBLIC_SUPABASE_URL="https://your-project-id.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-supabase-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"
```

**API Configuration:**
```bash
NEXT_PUBLIC_API_URL="http://localhost:8000"  # Backend API URL
NEXT_PUBLIC_APP_URL="http://localhost:3000"  # Frontend URL
```

#### Optional Environment Variables

**Stripe (for billing features):**
```bash
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_test_your_stripe_publishable_key"
```

**Analytics & Monitoring:**
```bash
NEXT_PUBLIC_POSTHOG_KEY="your-posthog-key"
NEXT_PUBLIC_SENTRY_DSN="your-sentry-dsn"
```

**Feature Flags:**
```bash
NEXT_PUBLIC_ENVIRONMENT_TYPE="development"
NEXT_PUBLIC_PLAYGROUND="true"
```

See the `.env.example` file for the complete list of available configuration options.

Next, install the frontend dependencies:

```bash
bun install
```

### Backend API Setup (Crucial!) ❗

The dashboard frontend relies **exclusively** on the backend API server (located in the `api/` directory) for all data fetching and actions after user authentication.

**You MUST run the backend API locally** before starting the frontend development server to test features correctly.

Follow the setup instructions in the [`api/README.md`](../api/README.md) to run the backend either natively (Python) or using Docker. Ensure the API is running and accessible at the URL specified in your `NEXT_PUBLIC_API_URL` environment variable (typically `http://localhost:8000`).

## Billing & Subscription Features 💳

The dashboard includes comprehensive billing and subscription management features powered by Stripe integration. This section covers the frontend billing components and their functionality.

### Billing Architecture (Frontend)

The billing system in the dashboard follows this flow:
1. **User Authentication** via Supabase provides JWT tokens
2. **Billing Pages** (`/settings/organization`) display organization subscription status
3. **Stripe Elements** handle secure payment processing
4. **Real-time Updates** via polling and webhook-triggered data refetch
5. **Backend API** manages all Stripe operations and subscription state

### Key Billing Components

#### Billing Settings Page (`app/(with-layout)/settings/organization/`)
- **Main Page** (`page.tsx`): Orchestrates billing operations and state management
- **OrganizationsList** (`components/OrganizationsList.tsx`): Displays subscription status and management options
- **EmbeddedCheckoutForm** (`components/EmbeddedCheckoutForm.tsx`): Stripe Elements integration for payments

#### Billing Features

### Backend Integration

**For complete billing setup including Stripe configuration, webhook handling, and API endpoints, see:**
➡️ **[`../api/README.md#billing--subscription-management`](../api/README.md#billing--subscription-management)**

### Environment Variables (Frontend)

```bash
# Required for billing features
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API URL
```

### Testing Billing Features

For local development:
1. **Backend Setup**: Follow [`../api/README.md`](../api/README.md) for complete Stripe configuration (the docker version is best for billing see the -s option on just api-build/run)
2. **Test Mode**: Use Stripe test keys and test card numbers (e.g., `4242424242424242`)
3. **Webhook Testing**: Use `stripe listen` to forward webhooks to local backend
4. **Frontend Testing**: Access `/settings/organization` to test the complete flow

### Billing Component Architecture

```
app/(with-layout)/settings/organization/
├── page.tsx                           # Main billing page & state management
├── components/
│   ├── OrganizationsList.tsx         # Subscription status & management UI
│   └── EmbeddedCheckoutForm.tsx      # Stripe Elements payment form
└── hooks/
    ├── useStripeConfig.ts            # Stripe configuration fetching
    └── useStripePricing.ts           # Pricing information
```

### Key Hooks & Utilities

- **`useOrgs()`**: Fetches organization data including subscription status
- **`useStripeConfig()`**: Retrieves Stripe publishable keys and configuration
- **`useStripePricing()`**: Gets current pricing information
- **`fetchAuthenticatedApi()`**: Makes authenticated requests to billing endpoints

### Billing Error Handling

The frontend includes comprehensive error handling:
- **Network Errors**: Retry mechanisms and user-friendly messages
- **Payment Failures**: Clear error display and recovery options
- **State Synchronization**: Polling to ensure UI reflects actual subscription state
- **Permission Errors**: Appropriate messaging for non-admin users

### Running the Frontend Dev Server

Once the backend API is running and frontend dependencies are installed (`bun install`), start the frontend development server:

```bash
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the magic happen ✨.

The page auto-updates as you edit files. Hot reloading is pretty sweet, eh?

This project uses [`next/font`](https://nextjs.org/docs/basic-features/font-optimization) to automatically optimize and load Inter, a custom Google Font.

## Development Workflow 🛠️

Working on the dashboard? Here are some helpful commands:

- **Run Dev Server:** `bun run dev` (You already know this one!)
- **Build for Production:** `bun run build` (Checks for build errors)
- **Linting:** `bun run lint` (Keep the code style consistent, please! 🙏)
- **Type Checking:** `bunx tsc --noEmit`
  - This command is your best friend for finding _all_ TypeScript errors at once, unlike `bun run build` which might stop at the first error.
  - **Important:** Make sure you run this command from _within_ the `dashboard` directory so it can find the `tsconfig.json`.

## Project Structure 🗺️

Navigating the codebase? Here's a quick lay of the land:

- **`app/`**: The heart of the Next.js App Router. Contains layouts, pages, route handlers (APIs), and loading/error components.
  - `(with-layout)/`: Routes in here share the main application layout (header, sidebar, etc.).
  - Other folders often correspond directly to URL paths.
- **`components/`**: Reusable UI components used across the application. Organized by feature or UI pattern.
  - `ui/`: Generally contains lower-level, shadcn-ui based components (Button, Card, etc.).
- **`lib/`**: Utility functions, type definitions (`types_db.ts`), constants, and external service integrations (like Supabase client setup in `lib/supabase/`).
- **`hooks/`**: Custom React hooks, especially for data fetching (like `useMetrics`, `useTraces`). They often rely on the context providers.
- **`public/`**: Static assets served directly (images, fonts).
- **`tests/`**: Unit and integration tests (using Jest, potentially).
- **`styles/`**: Global styles (though most styling is done via Tailwind CSS within components).

_(This is a brief overview, feel free to explore!)_

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js/) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/deployment) for more details.

## Frontend Data Fetching & Auth Architecture 🏗️ (Revised)

This section outlines the revised architecture for handling authentication, API communication, and state management in the dashboard frontend.

**Core Principles:**

1.  **Authentication via Supabase:** User sign-up, sign-in, and session management are handled using the `@supabase/ssr` library on the client and server-side middleware. After successful authentication, a JWT is obtained from the Supabase session.
2.  **Backend API as Single Source of Truth:** All data requests (user details, projects, orgs, traces, metrics, etc.) after login are directed exclusively to the backend API server (running at `NEXT_PUBLIC_API_URL`). The frontend **does not** make direct calls to the Supabase database (except for specific auth actions like sign-in, sign-out, password reset, MFA management).
3.  **JWT for API Authorization:** Every request to the backend API includes the Supabase JWT in the `Authorization: Bearer <token>` header.
4.  **Centralized API Client:** A dedicated function, `fetchAuthenticatedApi` (in `lib/api-client.ts`), handles all communication with the backend API. It automatically retrieves the current JWT from the Supabase session (`supabase.auth.getSession()`) and attaches the `Authorization` header.
5.  **React Query for Server State:** `@tanstack/react-query` is used to manage server state, including data fetching (`useQuery`), caching, background updates, and mutations (`useMutation`).
6.  **Custom Hooks for Data Fetching:** Data fetching logic is primarily encapsulated in custom hooks (located in `hooks/queries/`, e.g., `useUser`, `useProjects`, `useOrgs`, and directly in `hooks/` for `useTraces`, `useMetrics`). These hooks utilize `useQuery` or `useMutation` from React Query.
7.  **API Helper Functions:** For many common operations (User, Org, Project CRUD), hooks call dedicated API helper functions (e.g., `fetchUserAPI`, `createOrgAPI`, `updateProjectAPI`) defined in `lib/api/`. These helper functions then use `fetchAuthenticatedApi` internally to perform the actual request.
8.  **Direct API Client Usage in Hooks:** For more complex queries like fetching traces (`useTraces`) or metrics (`useMetrics`), the hooks often call `fetchAuthenticatedApi` directly, constructing the necessary endpoint and query parameters based on context (e.g., selected project ID, date range, filters).
9.  **Shared Client State:** Shared cross-component state, such as the currently selected project and date range, is managed using React Context via dedicated providers (e.g., `ProjectProvider` defined within `app/(with-layout)/projects-manager.tsx`, `DashboardStateProvider` in `app/(with-layout)/dashboard-state-provider.tsx`).

**Simplified Flow (Example: Fetching User Data):**

1.  User authenticates using Supabase UI/client functions.
2.  Frontend gets Supabase session and JWT.
3.  Component needs user profile data.
4.  Component calls relevant hook (e.g., `useUser()`).
5.  `useUser` hook calls `useQuery` with a query function that calls the API helper (`fetchUserAPI`).
6.  `fetchUserAPI` calls `fetchAuthenticatedApi('/opsboard/users/me')` with `method: 'GET'`.
7.  `fetchAuthenticatedApi` retrieves the JWT from `supabase.auth.getSession()`.
8.  `fetchAuthenticatedApi` makes the `fetch` call to `http://localhost:8000/opsboard/users/me` with the `Authorization: Bearer <token>` header.
9.  Backend API (`api/`) validates the JWT using `Depends(get_current_user)`.
10. Backend fetches user data from the database.
11. Backend returns data (JSON).
12. `fetchAuthenticatedApi` parses the JSON response.
13. `fetchUserAPI` returns the data to the `useQuery` hook.
14. React Query manages the state, component re-renders with the fetched user data.

**Key Changes from Previous Architecture:**

*   Removed direct Supabase database calls from frontend components (except for auth-specific actions).
*   Removed the `OperationalTokenProvider` and the concept of a separate operational token.
*   All authenticated data API calls use the Supabase JWT and go through `fetchAuthenticatedApi`, either directly or via helper functions in `lib/api/`.

## Cypress E2E Testing 🧪

For details on setting up and running End-to-End tests with Cypress, please refer to the dedicated README:

➡️ [`cypress/README.md`](./cypress/README.md)
