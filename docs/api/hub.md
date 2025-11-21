# Module: `hub`

The WonderDash hub is the menu router and export utility that users see when running `wonder-dash hub` or launching the CLI without arguments.

## Responsibilities
- Present menu-driven actions (identity probe, S3 summaries, CloudFront stats, exports, theme toggle).
- Render layouts, panels, and tables using Rich (`Console`, `Live`, `Panel`, `Table`).
- Manage cached export bundles so users can save or copy data.
- Handle clipboard and CSV export operations.
- Provide theme switching (light/dark) for different terminal palettes.

## Key Components
- `ExportBundle`: Dataclass storing export metadata (title, headers, rows).
- `_aws_session()`: Builds a boto3 session using the loaded config.
- `_who_am_i()`: Renders STS identity information with a loading animation.
- `_export_menu()`, `_export_to_csv()`, `_export_to_clipboard()`: Manage exports.
- `_toggle_dark_mode()`: Switches between palette dictionaries.
- `launch_hub()`: Entry point that builds the interactive menu, captures user input, and routes to handlers.

## Dependencies
- `config.load_config()` for profile and theme settings.
- Rich for terminal rendering.
- `hub_utils.build_loading_layout()` and `hub_utils.simple_table()` for consistent UI elements.
