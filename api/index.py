import os
import sys

# Add project root directory to sys.path for Vercel serverless runtime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
