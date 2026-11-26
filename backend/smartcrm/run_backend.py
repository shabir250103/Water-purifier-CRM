import os
import sys
from django.core.management import execute_from_command_line

from waitress import serve
from smartcrm.wsgi import application

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartcrm.settings')
    
    # If no arguments provided, run with Waitress (Production)
    if len(sys.argv) == 1:
        print("Starting AvrinaCRM Production Server (Waitress)...")
        print("Serving on http://localhost:8000")
        serve(application, host='0.0.0.0', port=8000)
    else:
        # Allow running other commands like 'migrate' if needed
        execute_from_command_line(sys.argv)

import traceback
import time

if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("\nCRITICAL ERROR: The application failed to start.")
        print("Please send the error message above to the developer.")
        input("Press Enter to close this window...")
        sys.exit(1)
