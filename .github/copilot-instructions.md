# Wonder Dash - GitHub Copilot Instructions

## Project Overview

WonderDash is a neon-styled terminal console application for AWS CloudFront and core services monitoring. It provides live, animated dashboards using the Rich library, designed for AWS CLI users who want terminal-based management tools.

## Tech Stack

### Core Framework
- **Python 3.9+**: Primary programming language
- **Rich 13.x**: Terminal UI library for live dashboards and animations
- **Boto3**: AWS SDK for Python
- **Click**: Command-line interface framework

### Key Libraries
- **Textual**: Terminal application framework (if used)
- **Pandas**: Data manipulation for analytics
- **PyYAML**: Configuration file handling
- **python-dotenv**: Environment variable management

### Packaging
- **pyproject.toml**: Modern Python packaging
- **src/ layout**: Source code organization

## Code Patterns & Conventions

### Rich Console Usage
```python
from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console()

# Create animated table
table = Table(title="CloudFront Dashboard")
table.add_column("Metric", style="cyan")
table.add_column("Value", style="green")

with Live(table, refresh_per_second=4):
    # Update table data in loop
    table.add_row("Requests", str(request_count))
```

### AWS Boto3 Integration
```python
import boto3

# Initialize AWS clients
cloudfront = boto3.client('cloudfront')
s3 = boto3.client('s3')
ec2 = boto3.client('ec2')

# CloudFront distribution info
response = cloudfront.get_distribution(Id=distribution_id)
distribution = response['Distribution']
```

### Click Commands
```python
import click

@click.group()
def cli():
    """WonderDash - AWS Terminal Dashboard"""
    pass

@cli.command()
@click.option('--distribution-id', envvar='CF_DISTRIBUTION_ID')
def dashboard(distribution_id):
    """Launch CloudFront dashboard"""
    if not distribution_id:
        click.echo("Error: CF_DISTRIBUTION_ID required")
        return
    # Launch dashboard logic
```

### Configuration Management
```python
import os
from pathlib import Path

CONFIG_FILE = Path.home() / '.wonderdash' / 'config.yaml'

def load_config():
    """Load configuration with environment variable overrides"""
    config = {
        'aws_profile': os.getenv('AWS_PROFILE', 'default'),
        'cf_distribution_id': os.getenv('CF_DISTRIBUTION_ID'),
        'update_interval': int(os.getenv('CF_PERIOD_SECONDS', '30'))
    }
    return config
```

## Development Workflow

### Setup
```bash
# Clone and setup
git clone <repo>
cd wonder_dash_repo

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .
```

### Running
```bash
# Launch hub menu
wonder-dash hub

# Direct module execution
python -m wonder_dash.hub

# Specific commands
wonder-dash dashboard --distribution-id YOUR_ID
```

### Testing
```bash
# Run tests
python -m pytest

# Manual testing with mock AWS
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
```

## Common Tasks

### Adding New AWS Services
1. Add boto3 client initialization
2. Create data collection functions
3. Design Rich display components
4. Add to hub menu navigation
5. Update configuration options

### Creating New Dashboards
1. Define data collection logic
2. Create Rich layout (tables, panels, progress bars)
3. Implement live updating with threading
4. Add keyboard controls for interaction
5. Test with real AWS data

### Theming and Styling
1. Define color palettes in theme constants
2. Apply styles to Rich components
3. Test visibility in different terminal themes
4. Add theme toggle functionality

## Important Notes

- **Terminal UI**: Designed for terminal use - test in various terminal emulators
- **AWS Permissions**: Requires appropriate IAM permissions for all AWS services used
- **Live Updates**: Uses threading for real-time data updates - handle thread safety
- **Configuration**: Supports both config files and environment variables
- **Error Handling**: Graceful degradation when AWS services are unavailable
- **Performance**: Optimize API calls and update frequencies for responsiveness

## Code Style

- Follow PEP 8 conventions
- Use type hints for function parameters
- Include docstrings for all functions
- Use Rich styling consistently
- Handle AWS exceptions appropriately
- Keep functions focused and testable
- Use pathlib for file operations