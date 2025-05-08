#!/usr/bin/env python3

import re
import os
import sys
import shutil

def extract_function(content, function_name):
    """Extract a function from the content based on its name"""
    pattern = rf"((?:@app\.route.*?\n)?def {function_name}\([^)]*\):.*?)(?:\n\n|$)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1)
    return None

def patch_app_file():
    # Make sure we have both files
    if not os.path.exists('app.py'):
        print("Error: app.py not found")
        return False
    
    if not os.path.exists('fixed_app.py'):
        print("Error: fixed_app.py not found")
        return False
    
    # Create backup
    print("Creating backup of app.py...")
    shutil.copy('app.py', 'app.py.bak')
    
    # Read the files
    with open('fixed_app.py', 'r') as f:
        fixed_content = f.read()
    
    with open('app.py', 'r') as f:
        app_content = f.read()
    
    # Extract fixed functions
    print("Extracting fixed functions...")
    auth_check_function = extract_function(fixed_content, 'auth_check')
    growth_advisor_function = extract_function(fixed_content, 'generate_growth_advisor_recommendations')
    customer_data_function = extract_function(fixed_content, 'customer_data_request')
    
    if not auth_check_function:
        print("Error: Could not extract auth_check function")
        return False
    
    if not growth_advisor_function:
        print("Error: Could not extract generate_growth_advisor_recommendations function")
        return False
    
    if not customer_data_function:
        print("Error: Could not extract customer_data_request function")
        return False
    
    # Replace functions in app.py content
    print("Applying fixed functions to app.py...")
    
    # Replace auth_check function
    auth_check_start = app_content.find('@app.route(\'/api/auth-check\'')
    if auth_check_start < 0:
        auth_check_start = app_content.find('def auth_check()')
    
    auth_check_end = app_content.find('def log(message, level="info"):', auth_check_start)
    
    if auth_check_start >= 0 and auth_check_end >= 0:
        app_content = app_content[:auth_check_start] + auth_check_function + '\n\n' + app_content[auth_check_end:]
    else:
        print("Warning: Could not locate auth_check function in app.py")
    
    # Replace generate_growth_advisor_recommendations function
    growth_advisor_start = app_content.find('def generate_growth_advisor_recommendations(shop_data):')
    if growth_advisor_start >= 0:
        growth_advisor_end = app_content.find('# Haupt-Ausführung', growth_advisor_start)
        if growth_advisor_end >= 0:
            app_content = app_content[:growth_advisor_start] + growth_advisor_function + '\n\n' + app_content[growth_advisor_end:]
        else:
            print("Warning: Could not locate end of generate_growth_advisor_recommendations function in app.py")
    else:
        print("Warning: Could not locate generate_growth_advisor_recommendations function in app.py")
    
    # Replace customer_data_request function
    customer_data_start = app_content.find('@app.route(\'/webhook/customers/data_request\'')
    if customer_data_start >= 0:
        customer_data_end = app_content.find('@app.route(\'/webhook/customers/redact\'', customer_data_start)
        if customer_data_end >= 0:
            app_content = app_content[:customer_data_start] + customer_data_function + '\n\n' + app_content[customer_data_end:]
        else:
            print("Warning: Could not locate end of customer_data_request function in app.py")
    else:
        print("Warning: Could not locate customer_data_request function in app.py")
    
    # Write patched content to app.py
    print("Writing patched content to app.py...")
    with open('app.py', 'w') as f:
        f.write(app_content)
    
    print("Done! app.py has been patched with fixed functions.")
    print("Original file is backed up as app.py.bak")
    return True

if __name__ == "__main__":
    if patch_app_file():
        sys.exit(0)
    else:
        print("Patching failed. Please restore from backup: cp app.py.bak app.py")
        sys.exit(1) 