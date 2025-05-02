import requests
import json
import sys # To exit if API isn't running
import argparse # Added for command line arguments

# --- Parse Command Line Arguments ---
parser = argparse.ArgumentParser(description='Test the KRA Invoice Checker API')
parser.add_argument('--url', default="http://127.0.0.1:8000", 
                    help='Base URL of the API (default: http://127.0.0.1:8000)')
parser.add_argument('--valid-invoice', default="0010195720000234911", 
                    help='A valid invoice number for testing')
parser.add_argument('--timeout', type=int, default=30,
                    help='Request timeout in seconds (default: 30)')
args = parser.parse_args()

# --- Configuration ---
API_BASE_URL = args.url
VALID_INVOICE_NUMBER_1 = args.valid_invoice
# If you have another known valid one, add it here for batch tests
# VALID_INVOICE_NUMBER_2 = "ANOTHER_VALID_NUMBER_HERE"

# An clearly invalid invoice number
INVALID_INVOICE_NUMBER_1 = "0010195720000234911"
INVALID_INVOICE_NUMBER_2 = "0010195720000234911"

# Request timeout
REQUEST_TIMEOUT = args.timeout

# --- Helper Function for Colored Output ---
def print_status(message, status):
    """Prints messages with color based on status."""
    color_code = ""
    if status == "PASS":
        color_code = "\033[92m"  # Green
    elif status == "FAIL":
        color_code = "\033[91m"  # Red
    elif status == "INFO":
        color_code = "\033[94m"  # Blue
    else:
        color_code = "\033[0m"  # Reset
    print(f"{color_code}[{status}] {message}\033[0m")


# --- Test Functions ---

def test_get_single_valid_invoice():
    """Tests fetching details for a single valid invoice number."""
    print_status("--- Testing GET /invoice/{valid_number} ---", "INFO")
    url = f"{API_BASE_URL}/invoice/{VALID_INVOICE_NUMBER_1}"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        print_status(f"Request URL: {url}", "INFO")
        print_status(f"Response Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            try:
                data = response.json()
                # Print truncated response for readability
                response_preview = json.dumps(data, indent=2)
                if len(response_preview) > 200:
                    response_preview = response_preview[:200] + "..."
                print_status(f"Response Body: {response_preview}", "INFO")
                
                # Basic validation of response structure
                if isinstance(data, dict) and data.get('Control Unit Invoice Number') == VALID_INVOICE_NUMBER_1:
                     print_status("GET single valid invoice test PASSED.", "PASS")
                else:
                    print_status("GET single valid invoice test FAILED: Unexpected response structure or data.", "FAIL")
                    print(f"Full response: {data}")
            except json.JSONDecodeError:
                 print_status("GET single valid invoice test FAILED: Response is not valid JSON.", "FAIL")
                 print(f"Response text: {response.text}")
        else:
            print_status(f"GET single valid invoice test FAILED: Expected status code 200, got {response.status_code}.", "FAIL")
            print(f"Response text: {response.text}")

    except requests.exceptions.RequestException as e:
        print_status(f"GET single valid invoice test FAILED: Network or request error: {e}", "FAIL")
    except Exception as e:
         print_status(f"GET single valid invoice test FAILED: An unexpected error occurred: {e}", "FAIL")


def test_get_single_invalid_invoice():
    """Tests fetching details for a single invalid/non-existent invoice number."""
    print_status("--- Testing GET /invoice/{invalid_number} ---", "INFO")
    url = f"{API_BASE_URL}/invoice/{INVALID_INVOICE_NUMBER_1}"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        print_status(f"Request URL: {url}", "INFO")
        print_status(f"Response Status Code: {response.status_code}", "INFO")

        if response.status_code == 404:
             try:
                 data = response.json()
                 print_status(f"Response Body: {json.dumps(data)}", "INFO")
                 # Basic validation of response structure for 404
                 if isinstance(data, dict) and 'detail' in data:
                      print_status("GET single invalid invoice test PASSED (received 404 with detail).", "PASS")
                 else:
                     print_status("GET single invalid invoice test FAILED: Expected 'detail' in 404 response.", "FAIL")
             except json.JSONDecodeError:
                  print_status("GET single invalid invoice test FAILED: 404 response is not valid JSON.", "FAIL")
                  print(f"Response text: {response.text}")
        else:
            print_status(f"GET single invalid invoice test FAILED: Expected status code 404, got {response.status_code}.", "FAIL")
            print(f"Response text: {response.text}")

    except requests.exceptions.RequestException as e:
        print_status(f"GET single invalid invoice test FAILED: Network or request error: {e}", "FAIL")
    except Exception as e:
         print_status(f"GET single invalid invoice test FAILED: An unexpected error occurred: {e}", "FAIL")


def test_post_multiple_mixed_invoices():
    """Tests fetching details for a mix of valid and invalid invoice numbers in a batch."""
    print_status("--- Testing POST /invoices/details (Mixed) ---", "INFO")
    url = f"{API_BASE_URL}/invoices/details"
    invoice_list = [VALID_INVOICE_NUMBER_1, INVALID_INVOICE_NUMBER_1, INVALID_INVOICE_NUMBER_2]
    payload = {"invoice_numbers": invoice_list}

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        print_status(f"Request URL: {url}", "INFO")
        print_status(f"Request Body: {json.dumps(payload)}", "INFO")
        print_status(f"Response Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            try:
                data = response.json()
                # Print truncated response for readability
                response_preview = json.dumps(data, indent=2)
                if len(response_preview) > 200:
                    response_preview = response_preview[:200] + "..."
                print_status(f"Response Body (preview): {response_preview}", "INFO")

                # Validate response structure for batch
                if isinstance(data, dict) and isinstance(data.get('results'), list):
                    results = data['results']
                    print_status(f"Received {len(results)} results.", "INFO")

                    # Verify results for each requested invoice number
                    all_checks_passed = True
                    
                    # Create a lookup of results by invoice number for easier checking
                    results_by_invoice = {result.get('invoice_number'): result for result in results}
                    
                    # Check that all requested invoices are in the results
                    missing_invoices = set(invoice_list) - set(results_by_invoice.keys())
                    if missing_invoices:
                        print_status(f"Missing results for invoice numbers: {missing_invoices}", "FAIL")
                        all_checks_passed = False
                    
                    # Check the valid invoice result
                    if VALID_INVOICE_NUMBER_1 in results_by_invoice:
                        valid_result = results_by_invoice[VALID_INVOICE_NUMBER_1]
                        if (valid_result.get('status') == "success" and 
                            isinstance(valid_result.get('data'), dict) and 
                            valid_result.get('error') is None):
                            print_status(f" Result for {VALID_INVOICE_NUMBER_1}: SUCCESS (as expected)", "INFO")
                        else:
                            print_status(f" Result for {VALID_INVOICE_NUMBER_1}: FAILED (Expected success, got status='{valid_result.get('status')}', error='{valid_result.get('error')}')", "FAIL")
                            all_checks_passed = False
                    
                    # Check the invalid invoice results
                    for inv_num in [INVALID_INVOICE_NUMBER_1, INVALID_INVOICE_NUMBER_2]:
                        if inv_num in results_by_invoice:
                            invalid_result = results_by_invoice[inv_num]
                            if (invalid_result.get('status') == "error" and 
                                invalid_result.get('data') is None and 
                                isinstance(invalid_result.get('error'), str) and 
                                len(invalid_result.get('error', "")) > 0):
                                print_status(f" Result for {inv_num}: ERROR (as expected: '{invalid_result.get('error')}')", "INFO")
                            else:
                                print_status(f" Result for {inv_num}: FAILED (Expected error, got status='{invalid_result.get('status')}', data='{invalid_result.get('data')}', error='{invalid_result.get('error')}')", "FAIL")
                                all_checks_passed = False

                    if len(results) == len(invoice_list) and all_checks_passed:
                        print_status("POST multiple mixed invoices test PASSED.", "PASS")
                    else:
                        print_status("POST multiple mixed invoices test FAILED: Mismatch in results count or individual results failed.", "FAIL")
                else:
                    print_status("POST multiple mixed invoices test FAILED: Unexpected response structure.", "FAIL")
                    print(f"Full response: {data}")

            except json.JSONDecodeError:
                print_status("POST multiple mixed invoices test FAILED: Response is not valid JSON.", "FAIL")
                print(f"Response text: {response.text}")
        else:
            # The batch endpoint should typically return 200 if the request format is valid,
            # with errors indicated *within* the results list.
            # A non-200 status usually means an issue with the request *format* itself (like 422 for invalid body).
            print_status(f"POST multiple mixed invoices test FAILED: Expected status code 200 for valid request body, got {response.status_code}.", "FAIL")
            print(f"Response text: {response.text}")

    except requests.exceptions.RequestException as e:
        print_status(f"POST multiple mixed invoices test FAILED: Network or request error: {e}", "FAIL")
    except Exception as e:
         print_status(f"POST multiple mixed invoices test FAILED: An unexpected error occurred: {e}", "FAIL")


def test_post_multiple_all_invalid_invoices():
    """Tests fetching details for only invalid invoice numbers in a batch."""
    print_status("--- Testing POST /invoices/details (All Invalid) ---", "INFO")
    url = f"{API_BASE_URL}/invoices/details"
    invoice_list = [INVALID_INVOICE_NUMBER_1, INVALID_INVOICE_NUMBER_2]
    payload = {"invoice_numbers": invoice_list}

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        print_status(f"Request URL: {url}", "INFO")
        print_status(f"Request Body: {json.dumps(payload)}", "INFO")
        print_status(f"Response Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            try:
                data = response.json()
                # Print truncated response for readability
                if isinstance(data, dict) and isinstance(data.get('results'), list):
                    results = data['results']
                    all_errors = all(result.get('status') == 'error' and 
                                    result.get('data') is None and 
                                    isinstance(result.get('error'), str) and
                                    len(result.get('error', "")) > 0
                                    for result in results)

                    if len(results) == len(invoice_list) and all_errors:
                        print_status("POST multiple all invalid invoices test PASSED.", "PASS")
                    else:
                        print_status("POST multiple all invalid invoices test FAILED: Not all results were errors or results count mismatch.", "FAIL")
                        print(f"Full response: {data}")

                else:
                    print_status("POST multiple all invalid invoices test FAILED: Unexpected response structure.", "FAIL")
                    print(f"Full response: {data}")

            except json.JSONDecodeError:
                print_status("POST multiple all invalid invoices test FAILED: Response is not valid JSON.", "FAIL")
                print(f"Response text: {response.text}")
        else:
             print_status(f"POST multiple all invalid invoices test FAILED: Expected status code 200, got {response.status_code}.", "FAIL")
             print(f"Response text: {response.text}")

    except requests.exceptions.RequestException as e:
        print_status(f"POST multiple all invalid invoices test FAILED: Network or request error: {e}", "FAIL")
    except Exception as e:
         print_status(f"POST multiple all invalid invoices test FAILED: An unexpected error occurred: {e}", "FAIL")

# Add a test case for an empty list
def test_post_multiple_empty_list():
    """Tests sending an empty list of invoice numbers in a batch."""
    print_status("--- Testing POST /invoices/details (Empty List) ---", "INFO")
    url = f"{API_BASE_URL}/invoices/details"
    invoice_list = []
    payload = {"invoice_numbers": invoice_list}

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        print_status(f"Request URL: {url}", "INFO")
        print_status(f"Request Body: {json.dumps(payload)}", "INFO")
        print_status(f"Response Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            try:
                data = response.json()
                print_status(f"Response Body: {json.dumps(data)}", "INFO")
                if isinstance(data, dict) and isinstance(data.get('results'), list) and len(data.get('results', [])) == 0:
                     print_status("POST multiple empty list test PASSED.", "PASS")
                else:
                    print_status("POST multiple empty list test FAILED: Expected empty results list.", "FAIL")
                    print(f"Full response: {data}")

            except json.JSONDecodeError:
                print_status("POST multiple empty list test FAILED: Response is not valid JSON.", "FAIL")
                print(f"Response text: {response.text}")
        else:
            print_status(f"POST multiple empty list test FAILED: Expected status code 200, got {response.status_code}.", "FAIL")
            print(f"Response text: {response.text}")

    except requests.exceptions.RequestException as e:
        print_status(f"POST multiple empty list test FAILED: Network or request error: {e}", "FAIL")
    except Exception as e:
         print_status(f"POST multiple empty list test FAILED: An unexpected error occurred: {e}", "FAIL")

# Add a test case for an invalid request body format (e.g., wrong key name)
def test_post_multiple_invalid_body():
    """Tests sending an invalid request body format to the batch endpoint."""
    print_status("--- Testing POST /invoices/details (Invalid Body) ---", "INFO")
    url = f"{API_BASE_URL}/invoices/details"
    # Incorrect key name 'numbers' instead of 'invoice_numbers'
    payload = {"numbers": [VALID_INVOICE_NUMBER_1]}

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        print_status(f"Request URL: {url}", "INFO")
        print_status(f"Request Body: {json.dumps(payload)}", "INFO")
        print_status(f"Response Status Code: {response.status_code}", "INFO")

        # FastAPI with Pydantic validation returns 422 for invalid request bodies
        if response.status_code == 422:
            try:
                data = response.json()
                print_status(f"Response Body: {json.dumps(data)}", "INFO")
                # Check for the standard FastAPI/Pydantic validation error structure
                if isinstance(data, dict) and isinstance(data.get('detail'), list) and len(data.get('detail', [])) > 0:
                     print_status("POST multiple invalid body test PASSED (received 422 with validation errors).", "PASS")
                else:
                     print_status("POST multiple invalid body test FAILED: Expected validation error details in 422 response.", "FAIL")
            except json.JSONDecodeError:
                 print_status("POST multiple invalid body test FAILED: 422 response is not valid JSON.", "FAIL")
                 print(f"Response text: {response.text}")

        else:
            print_status(f"POST multiple invalid body test FAILED: Expected status code 422, got {response.status_code}.", "FAIL")
            print(f"Response text: {response.text}")

    except requests.exceptions.RequestException as e:
        print_status(f"POST multiple invalid body test FAILED: Network or request error: {e}", "FAIL")
    except Exception as e:
         print_status(f"POST multiple invalid body test FAILED: An unexpected error occurred: {e}", "FAIL")


# --- Main Execution ---
if __name__ == "__main__":
    print_status("--- Starting API Test Suite ---", "INFO")
    print_status(f"Target API Base URL: {API_BASE_URL}", "INFO")
    print_status(f"Using valid invoice number: {VALID_INVOICE_NUMBER_1}", "INFO")
    print_status(f"Request timeout: {REQUEST_TIMEOUT} seconds", "INFO")
    print_status("NOTE: Ensure your FastAPI application is running before executing these tests.", "INFO")
    print("-" * 30)

    # Basic check to see if the API is accessible
    try:
        # Try to hit a known endpoint like the docs or root
        requests.get(API_BASE_URL + "/docs", timeout=5)
        print_status("API appears to be reachable.", "INFO")
    except requests.exceptions.ConnectionError:
        print_status(f"Connection Error: Could not connect to API at {API_BASE_URL}.", "FAIL")
        print_status("Please ensure your FastAPI application is running and the API_BASE_URL is correct.", "FAIL")
        sys.exit(1) # Exit if API isn't running
    except requests.exceptions.Timeout:
         print_status(f"Timeout Error: API at {API_BASE_URL} is reachable but took too long to respond.", "FAIL")
         print_status("Please ensure your FastAPI application is running and responsive.", "FAIL")
         sys.exit(1)
    except requests.exceptions.RequestException as e:
        print_status(f"An unexpected error occurred while checking API reachability: {e}", "FAIL")
        sys.exit(1)

    print("-" * 30)

    # Run the tests sequentially
    test_get_single_valid_invoice()
    print("-" * 30)
    test_get_single_invalid_invoice()
    print("-" * 30)
    test_post_multiple_mixed_invoices()
    print("-" * 30)
    test_post_multiple_all_invalid_invoices() 
    print("-" * 30)
    test_post_multiple_empty_list()
    print("-" * 30)
    test_post_multiple_invalid_body()
    print("-" * 30)

    print_status("--- API Test Suite Finished ---", "INFO")