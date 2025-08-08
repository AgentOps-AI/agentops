FROM supabase/postgres:15.1.0.103

# Set environment variables
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres
ENV POSTGRES_DB=test_db

# Expose port
EXPOSE 5432

# Add healthcheck
HEALTHCHECK --interval=5s --timeout=5s --retries=5 \
    CMD ["pg_isready", "-U", "postgres", "-p", "5432"]