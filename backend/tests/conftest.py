import os

from dotenv import load_dotenv

# Load environment variables from backend/.env or root .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
