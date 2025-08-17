import sys
from pathlib import Path

# Add the current directory to Python path to import modules
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from agent.information_extractor import WebsiteInformationExtractor


def main():
    """Main function - simple and straightforward"""
    try:
        extractor = WebsiteInformationExtractor()
        extractor.run()
        
        
        
    except KeyboardInterrupt:
        print("\nInformation extraction interrupted by user")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()