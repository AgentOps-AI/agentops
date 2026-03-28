# Local Development Setup Guide

This guide helps you set up the AgentOps Dashboard for local development and resolve common console errors.

## Quick Setup

### 1. Environment Configuration

The `.env.local` file has been created for you with local development defaults. You need to:

1. **Get your Supabase credentials** from your Supabase project dashboard:
   - Go to [Supabase Dashboard](https://supabase.com/dashboard)
   - Select your project → Settings → API
   - Copy the values and update `.env.local`:

```bash
# Replace these with your actual values:
NEXT_PUBLIC_SUPABASE_URL="https://your-project-id.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-supabase-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"
```

### 2. Backend API Setup

The dashboard requires the backend API to be running on `http://localhost:8000`.

Follow the setup instructions in [`../api/README.md`](../api/README.md) to start the backend server.

### 3. Install Dependencies & Start

```bash
# Install dependencies
bun install

# Start the development server
bun run dev
```

## Console Error Solutions

### ✅ PostHog Analytics Errors (FIXED)

**Errors you were seeing:**
- `401 Unauthorized` from `us.i.posthog.com`
- `404 Not Found` from `us-assets.i.posthog.com`
- MIME type errors from PostHog scripts

**Solution:**
- PostHog is now **disabled by default** in local development
- Set `NEXT_PUBLIC_POSTHOG_KEY=""` (empty) in `.env.local` to disable
- PostHog components now gracefully handle missing keys
- No more console errors from analytics in local development!

### ✅ Backend API Errors

**Errors you might see:**
- `401 Unauthorized` from `/opsboard/users/me`
- Network errors to `localhost:8000`

**Solution:**
- Make sure the backend API is running on `http://localhost:8000`
- Check that `NEXT_PUBLIC_API_URL="http://localhost:8000"` in `.env.local`
- Follow the API setup guide in `../api/README.md`

### ✅ Authentication Setup

**For full functionality:**
1. Set up your Supabase project with authentication enabled
2. Configure the Supabase credentials in `.env.local`
3. The backend API handles user session validation

## Optional Features for Local Development

### Enable PostHog (Optional)

If you want to test analytics locally:
1. Get a PostHog API key from [PostHog](https://posthog.com)
2. Set `NEXT_PUBLIC_POSTHOG_KEY="your-posthog-key"` in `.env.local`

### Enable Stripe Billing (Optional)

If you want to test billing features:
1. Get Stripe test keys from [Stripe Dashboard](https://dashboard.stripe.com)
2. Set `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_test_..."` in `.env.local`
3. Configure the backend with Stripe as well

## Troubleshooting

### Still seeing console errors?

1. **Clear browser cache** and reload
2. **Check browser dev tools** → Application → Local Storage → Clear all
3. **Restart the dev server**: `Ctrl+C` then `bun run dev`
4. **Verify environment variables**: Check that `.env.local` exists and has correct values

### Backend connection issues?

1. Verify backend is running: `curl http://localhost:8000/health` (or similar endpoint)
2. Check CORS settings in the backend configuration
3. Ensure `NEXT_PUBLIC_API_URL` matches your backend URL

### Authentication issues?

1. Verify Supabase credentials are correct
2. Check that your Supabase project has authentication enabled
3. Ensure the backend API can connect to your Supabase database

## Development Workflow

```bash
# Install dependencies
bun install

# Start development server with hot reload
bun run dev

# Run linting
bun run lint

# Build for production (to check for build errors)
bun run build

# Type checking
bunx tsc --noEmit
```

## Next Steps

1. ✅ Environment configured
2. ✅ Console errors resolved  
3. 🔄 Start backend API server
4. 🔄 Configure Supabase credentials
5. 🚀 Start developing!

---

**Need help?** Check the main [README.md](./README.md) or [API documentation](../api/README.md).