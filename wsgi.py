import os
import sys
import ssl
import certifi

# Fix SSL certificate issues before importing app
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE'] = certifi.where()

# Fix Python's SSL module to use the certifi certificates
ssl._create_default_https_context = ssl.create_default_context

# Import the Flask app
from app import app

if __name__ == "__main__":
    app.run() 