# Databases

There are two primary databases in our system

1. Postgres - hosted by Supabase
2. Clickhouse

## Backups
Point-in-time backups should always be enabled, with a minimum 30 day backup period

## Migrations
1. Postgres - Migrations exist in the `supabase/migrations` directory
    - New migrations here will automatically be applied on merge to main

2. Clickhouse - Migrations don't exist in Clickhouse in the way that they do with Postgres. Because Clickhouse is only being used as an OTEL data store, the table schemas will never need to change. On occasion, data will need to be manipulated, and this is performed via individual queries.

All Clickhouse data manipulation should be documented in Atuin. In the `AgentOps Clickhouse` workspace create a new runbook with an appropriate name. Describe the intended changes and the steps taken to accomplish it. Treat this like a Jupyter Notebook for Clickhouse. Atuin has a Clickhouse Client that can be used to run the queries and store outputs.

Data manipulation work that is done in Atuin is accessible to the team and acts as recordkeeping of migrations made. This makes it easier to both have query reviews and debug later.

## Production Data Modification
**Any time** a modification query (update or delete) is to be performed on production data, another relevant engineer must review the query and be present.

In addition, if affecting data to a significant degree (changes a small thing on a lot of rows, or a big thing on important rows), the table or db should first be backed up

## Other database environments
In general, if a database isn't used for production, it's a dev db. This data has no protection. These databases are used for query dry-runs and storing unimportant data (e2e tests).

## Production Data Protection
Production data must be treated with the utmost care and security consciousness. As we handle potentially sensitive information from our customers' AI agent interactions, including but not limited to API keys, credentials, and business logic, we must maintain strict data handling practices.

### Local Storage of Production Data
- Production data **MUST NOT** be stored on development machines unless absolutely necessary for critical debugging or incident response.
- If production data must be stored locally:
  1. Document the reason for local storage, including:
     - Specific incident or debugging case
     - Data scope and type
     - Expected duration of storage
  2. Store this documentation in the ticket requiring local data
  3. Delete the data immediately after the investigation is complete
  4. Document the time of deletion of the data

### Data Protection Considerations
- Even if data appears non-sensitive, it may contain embedded sensitive information (API keys, credentials, business logic)
- Treat all production data as potentially sensitive
- Consider the chain of liability - our customers trust us with their data, and their customers trust them
- only access and store what is absolutely necessary
- When in doubt, consult with leadership before storing or handling production data locally

A data leak can significantly undermine the trust of our customers. Our value is in the data we maintain and our responsibility is to handle it appropriately.