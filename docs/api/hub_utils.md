# Module: `hub_utils`

Shared helpers used by both the hub and dashboard renderers.

## Responsibilities
- Provide consistent Rich layouts (loading screens, simple tables).
- Handle clipboard safe fallbacks (where supported).
- Offer formatting utilities that keep typography consistent across modules.

## Key Functions
- `build_loading_layout(title, accent_color)`: Returns a Rich `Layout` with spinner + placeholder body.
- `simple_table(headers, header_style)`: Shortcut for creating a Table with default padding and style.
- `format_metric(value)`: Example helper for formatting numbers (if present in the module).

## Usage Notes
- Import helpers from `hub_utils` instead of re-creating Rich layouts. This keeps the UI cohesive.
- All helpers should remain dependency-light so they can be imported from both CLI and dashboard contexts.
