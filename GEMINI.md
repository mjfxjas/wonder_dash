## Project Overview

WonderDash is a neon-styled terminal console for AWS CloudFront and core services. It's a Python application that uses `boto3` to interact with the AWS API and `rich` to create a rich, interactive terminal-based user interface.

The application has a central "hub" that acts as a main menu, providing access to various toolkits for services like CloudFront, S3, EC2, and Lambda. The main feature is a real-time CloudFront dashboard that displays live requests, data transfer, error rates, and other key metrics.

## Building and Running

1.  **Install dependencies:**
    The project uses a `pyproject.toml` file to manage dependencies. Install them using pip:
    ```bash
    pip install .
    ```

2.  **Run the application:**
    The main entry point is the `wonder-dash` command, which launches the hub menu.
    ```bash
    wonder-dash hub
    ```

    From the hub, you can navigate to the CloudFront dashboard or other toolkits.

## Development Conventions

*   **Editable mode:** For development, install the package in editable mode to reflect code changes immediately:
    ```bash
    pip install -e .
    ```
*   **Dependencies:** Project dependencies are managed in `pyproject.toml`.
*   **Code Style:** The code uses modern Python features like type hints and f-strings. It is well-structured and follows a modular approach.
*   **Configuration:** The application uses a configuration file (`~/.config/wonder-dash/config.json`) to store AWS profile information and other settings. The `wonder-dash setup` command provides a wizard to create this file. Environment variables can be used to override the configuration.
