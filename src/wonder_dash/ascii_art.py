"""ASCII art and visual elements for WonderDash."""

from rich.text import Text
from rich.console import Console

def get_wonder_dash_logo() -> Text:
    """Return the main WonderDash ASCII art logo."""
    logo = Text()
    
    # Main ASCII art
    ascii_art = """
██╗    ██╗ ██████╗ ███╗   ██╗██████╗ ███████╗██████╗ 
██║    ██║██╔═══██╗████╗  ██║██╔══██╗██╔════╝██╔══██╗
██║ █╗ ██║██║   ██║██╔██╗ ██║██║  ██║█████╗  ██████╔╝
██║███╗██║██║   ██║██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗
╚███╔███╔╝╚██████╔╝██║ ╚████║██████╔╝███████╗██║  ██║
 ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝
                                                      
██████╗  █████╗ ███████╗██╗  ██╗                     
██╔══██╗██╔══██╗██╔════╝██║  ██║                     
██║  ██║███████║███████╗███████║                     
██║  ██║██╔══██║╚════██║██╔══██║                     
██████╔╝██║  ██║███████║██║  ██║                     
╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝                     
"""
    
    # Add the ASCII art with neon styling
    logo.append(ascii_art, style="bright_cyan")
    
    # Add subtitle
    logo.append("\n    ⚡ Neon-styled terminal console for AWS CloudFront & core services ⚡", 
                style="magenta")
    
    return logo

def get_compact_logo() -> Text:
    """Return a compact version of the logo for smaller displays."""
    logo = Text()
    
    compact_art = """
╔══════════════════════════════════════╗
║  ██╗    ██╗██████╗                   ║
║  ██║ █╗ ██║██╔══██╗                  ║
║  ╚███╔███╔╝██║  ██║ █████╗ ███████╗  ║
║   ╚══╝╚══╝ ██║  ██║ ╚════╝ ╚══════╝  ║
║            ██████╔╝                  ║
║            ╚═════╝                   ║
╚══════════════════════════════════════╝
"""
    
    logo.append(compact_art, style="bright_cyan")
    logo.append("\n    WonderDash - AWS Terminal Console", style="magenta")
    
    return logo

def get_loading_spinner_frames() -> list[str]:
    """Return frames for a neon-style loading animation."""
    return [
        "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"
    ]

def get_neon_border(width: int = 60) -> str:
    """Return a neon-style border."""
    return "═" * width

def get_welcome_message() -> Text:
    """Return a styled welcome message."""
    message = Text()
    message.append("🌟 Welcome to ", style="white")
    message.append("WonderDash", style="bold bright_cyan")
    message.append(" - Your AWS command center! 🌟", style="white")
    return message