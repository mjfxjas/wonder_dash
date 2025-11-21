# Module: `cli`

CLI entry point for WonderDash.

## Responsibilities
- Build the `argparse` parser and dispatch subcommands.
- Ensure optional dependencies (boto3) are loaded before running commands that need them.
- Provide the default `hub` experience when no subcommand is passed.

## Commands
- `setup`: Calls `wizard.run_setup()` to guide the user through config creation.
- `dashboard`: Launches the live dashboard (`dashboard.run_dashboard`).
- `hub`: Opens the menu-driven hub (`hub.launch_hub`).
- `show-config`: Prints the resolved config to stdout.
- `list-distributions`: Lists CloudFront distributions using boto3 with the configured profile.

## Functions
- `build_parser()`: Returns the configured `argparse.ArgumentParser`.
- `main(argv=None)`: Parses arguments, dispatches to the selected function, returns exit code.
- Internal helpers like `_require_boto3()` handle dependency checks.
