"""
Generic colorama utility functions for terminal prettification.
Usage: from terminal_prettify import success, error, warning, info, etc.
"""

from colorama import init, Fore, Back, Style

# Initialize colorama for Windows compatibility
init(autoreset=True)

# Color shortcuts
class Colors:
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE
    BLACK = Fore.BLACK
    
    # Bright colors
    BRIGHT_RED = Fore.LIGHTRED_EX
    BRIGHT_GREEN = Fore.LIGHTGREEN_EX
    BRIGHT_YELLOW = Fore.LIGHTYELLOW_EX
    BRIGHT_BLUE = Fore.LIGHTBLUE_EX
    BRIGHT_MAGENTA = Fore.LIGHTMAGENTA_EX
    BRIGHT_CYAN = Fore.LIGHTCYAN_EX
    BRIGHT_WHITE = Fore.LIGHTWHITE_EX
    
    # Background colors
    BG_RED = Back.RED
    BG_GREEN = Back.GREEN
    BG_YELLOW = Back.YELLOW
    BG_BLUE = Back.BLUE
    BG_MAGENTA = Back.MAGENTA
    BG_CYAN = Back.CYAN
    BG_WHITE = Back.WHITE
    BG_BLACK = Back.BLACK
    
    # Styles
    BOLD = Style.BRIGHT
    DIM = Style.DIM
    RESET = Style.RESET_ALL

# Basic print functions
def success(message):
    """Print success message in green."""
    print(f"{Colors.BRIGHT_GREEN}✓ {message}{Colors.RESET}")

def error(message):
    """Print error message in red."""
    print(f"{Colors.BRIGHT_RED}✗ {message}{Colors.RESET}")

def warning(message):
    """Print warning message in yellow."""
    print(f"{Colors.BRIGHT_YELLOW}⚠ {message}{Colors.RESET}")

def info(message):
    """Print info message in blue."""
    print(f"{Colors.BRIGHT_BLUE}ℹ {message}{Colors.RESET}")

def debug(message):
    """Print debug message in magenta."""
    print(f"{Colors.BRIGHT_MAGENTA}🐛 {message}{Colors.RESET}")

def processing(message):
    """Print processing message in cyan."""
    print(f"{Colors.CYAN}⏳ {message}{Colors.RESET}")

def completed(message):
    """Print completion message in green."""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

# Formatting functions
def header(message):
    """Print header message in bold cyan."""
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * len(message)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * len(message)}{Colors.RESET}")

def subheader(message):
    """Print subheader message in bold white."""
    print(f"{Colors.BOLD}{Colors.WHITE}{message}{Colors.RESET}")
    print(f"{Colors.WHITE}{'-' * len(message)}{Colors.RESET}")

def separator(char="─", length=60):
    """Print a separator line."""
    print(f"{Colors.DIM}{char * length}{Colors.RESET}")

def highlight(message):
    """Print highlighted message with background."""
    print(f"{Colors.BG_YELLOW}{Colors.BLACK} {message} {Colors.RESET}")

def banner(text, width=60):
    """Print a banner with text centered."""
    lines = text.split('\n')
    print(f"{Colors.BOLD}{Colors.CYAN}{'█' * width}{Colors.RESET}")
    for line in lines:
        padding = (width - len(line) - 2) // 2
        print(f"{Colors.BOLD}{Colors.CYAN}█{' ' * padding}{line}{' ' * (width - len(line) - padding - 2)}█{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'█' * width}{Colors.RESET}")

# Text formatting functions
def colored(text, color=None, bg_color=None, bold=False, dim=False, underline=False):
    """Return colored text without printing."""
    result = ""
    
    if bold:
        result += Colors.BOLD
    elif dim:
        result += Colors.DIM
        
    if underline:
        result += '\033[4m'  # ANSI underline code
        
    if color:
        result += getattr(Colors, color.upper(), Colors.WHITE)
        
    if bg_color:
        result += getattr(Colors, f"BG_{bg_color.upper()}", "")
        
    result += text + Colors.RESET
    return result

def link(url, text=None):
    """Format a link with white color and underline."""
    display_text = text or url
    return colored(display_text, "white", underline=True)

def label(text):
    """Format a label with text color."""
    return colored(f"{text}", "bright_cyan", bold=True)

# Interactive functions
def prompt(message):
    """Print prompt message and return user input."""
    return input(f"{Colors.BRIGHT_CYAN}❓ {message}: {Colors.RESET}")

def confirm(message):
    """Print confirmation prompt and return boolean."""
    response = input(f"{Colors.BRIGHT_YELLOW}❓ {message} (y/n): {Colors.RESET}").lower()
    return response in ['y', 'yes', '1', 'true']

# Progress and status functions
def progress_bar(current, total, width=50, label_text="Progress"):
    """Display a progress bar."""
    percent = current / total
    filled_width = int(width * percent)
    bar = '█' * filled_width + '░' * (width - filled_width)
    
    print(f"\r{Colors.BRIGHT_BLUE}{label_text}: {Colors.RESET}"
          f"[{Colors.GREEN}{bar}{Colors.RESET}] "
          f"{Colors.BRIGHT_WHITE}{current}/{total} ({percent:.1%}){Colors.RESET}", 
          end='', flush=True)
    
    if current == total:
        print()  # New line when complete

def status_message(message, status_type="info"):
    """Print status message with appropriate icon and color."""
    icons = {
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
        "info": "ℹ",
        "loading": "⏳",
        "question": "❓"
    }
    
    colors = {
        "success": Colors.BRIGHT_GREEN,
        "error": Colors.BRIGHT_RED,
        "warning": Colors.BRIGHT_YELLOW,
        "info": Colors.BRIGHT_BLUE,
        "loading": Colors.CYAN,
        "question": Colors.BRIGHT_CYAN
    }
    
    icon = icons.get(status_type, "•")
    color = colors.get(status_type, Colors.WHITE)
    
    print(f"{color}{icon} {message}{Colors.RESET}")

def table_row(*columns, colors=None):
    """Print a table row with optional column colors."""
    if colors is None:
        colors = [None] * len(columns)
    
    formatted_columns = []
    for col, color in zip(columns, colors):
        if color:
            formatted_columns.append(colored(str(col), color))
        else:
            formatted_columns.append(str(col))
    
    print(" | ".join(formatted_columns))
