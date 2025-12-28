#!/usr/bin/env python3
"""Test script to display WonderDash ASCII art."""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from wonder_dash.ascii_art import get_wonder_dash_logo, get_compact_logo, get_welcome_message
    from rich.console import Console
    
    console = Console()
    
    print("Testing WonderDash ASCII Art...")
    print("=" * 50)
    
    # Test full logo
    print("\n1. Full WonderDash Logo:")
    logo = get_wonder_dash_logo()
    console.print(logo)
    
    print("\n" + "=" * 50)
    
    # Test compact logo
    print("\n2. Compact Logo:")
    compact = get_compact_logo()
    console.print(compact)
    
    print("\n" + "=" * 50)
    
    # Test welcome message
    print("\n3. Welcome Message:")
    welcome = get_welcome_message()
    console.print(welcome, justify="center")
    
    print("\n" + "=" * 50)
    print("ASCII Art test completed successfully!")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the repository root directory.")
except Exception as e:
    print(f"Error: {e}")