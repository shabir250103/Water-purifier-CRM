import os
import sys
from waitress import serve
from django.core.wsgi import get_wsgi_application
from pathlib import Path

# Setup paths for PyInstaller environment
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    # sys._MEIPASS is where PyInstaller unpacks the bundle
    base_dir = Path(sys._MEIPASS)
else:
    # Running from source
    base_dir = Path(__file__).resolve().parent

# Ensure the backend directory is in the python path
sys.path.append(str(base_dir))

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartcrm.settings")

# Prepare the WSGI application
application = get_wsgi_application()

if __name__ == '__main__':
    # If arguments are provided (e.g., "SmartCRM.exe createsuperuser"), run them as management commands
    if len(sys.argv) > 1:
        from django.core.management import execute_from_command_line
        execute_from_command_line(sys.argv)
    else:
        # Otherwise, run the default server
        print("====================================================================")
        print("      SmartCRM Application - Secure Deployment")
        print("====================================================================")
        print("  Server is starting...")
        print("  Access the application at: http://localhost:8000")
        print("  Keep this window open to run the server.")
        print("====================================================================")
        
        # Run the server using Waitress
        serve(application, host='0.0.0.0', port=8000, threads=6)
