# Builder stage
FROM node:20-alpine as builder

# Declare ARG variables that will be used during build
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with cache mount
RUN npm install

# Copy project files
COPY . .

# Build the Next.js application with build-time env vars
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=$NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY

RUN --mount=type=cache,id=s/17c760dd-6886-4c45-a5c1-0b8a9b99a63d-/app/.next/cache,target=/app/.next/cache \
    npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy necessary files from builder
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/next.config.js ./next.config.js

# Expose port 3000
EXPOSE 3000

# Runtime environment variables
ENV NEXT_PUBLIC_SUPABASE_URL=""
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=""
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=""

# Start the application
CMD echo "Runtime SUPABASE_URL: $NEXT_PUBLIC_SUPABASE_URL" && \
    echo "Runtime SUPABASE_KEY: ${NEXT_PUBLIC_SUPABASE_ANON_KEY:0:8}..." && \
    npm run start
