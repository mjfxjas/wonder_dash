# Module: `dashboard`

The live dashboard aggregates AWS service data and presents it in a Rich layout.

## Responsibilities
- Fetch CloudFront request data and related service metrics via boto3.
- Render sections (identity, compute, storage, networking) using panels and tables.
- Handle refresh cadence so the UI stays responsive without hammering APIs.
- Provide entry point `run_dashboard(config)` that the CLI calls.

## Important Functions
- `run_dashboard(config)`: Validates config, builds boto3 session, kicks off the refresh loop.
- `_build_layout()`: Defines the Rich layout placeholders.
- `_update_identity_panel`, `_update_compute_panel`, `_update_storage_panel`: Populate sections with data from the cached model.
- `_fetch_data(session, config)`: Gathers AWS resources and returns structured dictionaries.

## Data Model
- Identity: STS caller identity, current region, account alias.
- Compute: EC2 instance summary, Lambda concurrency metrics.
- Storage: S3 bucket stats, DynamoDB table counts.
- Network/Delivery: CloudFront distributions, alias mapping.

## Error Handling
- Wraps boto3 exceptions and surfaces friendly messages in the layout.
- Respects `config.cache_ttl_seconds` so data is reused until TTL expires.
