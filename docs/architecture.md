# WonderDash Architecture

WonderDash assembles four cooperating layers that turn AWS telemetry into a responsive terminal dashboard.

## 1. UI Layer (Renderer)
Files: `dashboard.py`, `hub.py`

- Renders menus, tables, and progress indicators using Rich (and Textual support on the feature branch).
- Captures keyboard commands, updates layouts in place, and proxies export actions.
- Acts as the presentation shell for both the dashboard view and the hub command router.

## 2. Core Engine and Action Layer
Files: `hub_utils.py`, shared helpers in `cli.py`

- Detects AWS profiles and regions before handing control to renderers.
- Validates credentials, handles boto3 session creation, and normalizes errors.
- Coordinates cache TTL logic so dashboards do not flood the control plane.
- Loads dashboards on demand when the CLI or hub requests them.

## 3. Resource Discovery Layer
Files: `dashboard.py`, `hub_utils.py`

- Issues boto3 calls for CloudFront, S3, Lambda, EC2, STS, and DynamoDB (IAM planned).
- Shapes the service responses into structured dictionaries that renderers can stream to Rich tables.
- Keeps a cached in-memory model of identity, compute, and storage data to support quick refreshes.

## 4. Configuration and Extension Layer
Files: `config.py`, user overrides in `~/.wonderdash/config.json`

- Stores distribution IDs, refresh cadence, profile names, and UI preferences.
- Allows local overrides without touching the repository by writing to the config JSON file.
- Provides a single import (`WonderConfig`) that other modules consume.

## Diagrams
High-level diagrams live in `docs/assets/wonderdash_architecture_overview.png`. They illustrate:

1. User → WonderDash → AWS SDK flow
2. Layered architecture stack
3. The cached in-memory model
4. Interactive terminal mock-up

![WonderDash Architecture Overview](assets/wonderdash_architecture_overview.png)
