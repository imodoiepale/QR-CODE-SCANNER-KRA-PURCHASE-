from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import re
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="KRA Invoice Checker API",
    description="API to fetch invoice details from the KRA iTax portal.",
    version="1.1.0" # Updated version
)

# Base URL for the KRA invoice check
KRA_BASE_URL = "https://itax.kra.go.ke/KRA-Portal/invoiceChk.htm"

# Pydantic model for the request body for multiple invoices
class InvoiceNumbersRequest(BaseModel):
    """Request body model for fetching multiple invoice details."""
    invoice_numbers: List[str] = Field(
        ..., # Ellipsis indicates the field is required
        description="List of KRA Control Unit Invoice Numbers to fetch details for."
    )

# Pydantic model for the response structure for a single result in the batch
class InvoiceDetailResult(BaseModel):
    """Structure for a single invoice lookup result in the batch response."""
    invoice_number: str = Field(..., description="The original invoice number requested.")
    status: str = Field(..., description="'success' or 'error'.")
    data: Optional[Dict[str, Any]] = Field(None, description="The scraped invoice data if status is 'success'.")
    error: Optional[str] = Field(None, description="Error message if status is 'error'.")

# Pydantic model for the response structure for multiple invoices
class MultipleInvoicesResponse(BaseModel):
    """Response body model for fetching multiple invoice details."""
    results: List[InvoiceDetailResult] = Field(..., description="List of results for each requested invoice number.")


def scrape_kra_invoice(invoice_number: str) -> Dict[str, str]:
    """
    Fetches and scrapes invoice details from the KRA iTax portal for a single invoice.

    Args:
        invoice_number: The KRA Control Unit Invoice Number.

    Returns:
        A dictionary containing the extracted invoice data if successful.

    Raises:
        requests.exceptions.RequestException: For network or HTTP errors.
        ValueError: If expected data is not found on the page (indicating invoice not found or structure change).
        Exception: For any other unexpected errors.
    """
    url = f"{KRA_BASE_URL}?actionCode=loadPage&invoiceNo={invoice_number}"
    logger.info(f"Attempting to scrape invoice: {invoice_number} from {url}")

    try:
        # Make the request with a timeout
        response = requests.get(url, timeout=20) # Increased timeout slightly

        # Raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()

        # Use lxml parser for better performance
        soup = BeautifulSoup(response.content, 'lxml')

        # --- Check for Error Messages on the Page ---
        # KRA page often returns 200 OK even for invalid numbers but shows an error.
        error_message_element = soup.find(text=re.compile(r'Invalid Invoice Number|Invoice details not found|Error occurred', re.IGNORECASE))
        if error_message_element:
             error_text = error_message_element.strip()
             logger.warning(f"Error text found for {invoice_number}: {error_text}")
             # Look for a specific error message div if available
             error_div = soup.find('div', class_='errorMessage')
             if error_div and error_div.get_text(strip=True):
                  error_text = error_div.get_text(strip=True)

             # Check if the page *lacks* the expected data structure (the main table)
             # even if a generic error text is present. This confirms it's likely an error page.
             main_data_table = soup.find('table', width="100%")
             if not main_data_table or "No Data Found" in soup.get_text(): # Added check for "No Data Found"
                  raise ValueError(f"Invoice details not found: {error_text}")
             # If a table was found, maybe the error message is supplementary, try scraping anyway?
             # Or, maybe the table is just the standard template. Let's trust the error message check first.
             # If we reach here, it means an error *text* was found, but the page *also* seems to have the data structure.
             # This is ambiguous. Let's prioritize the explicit error message and treat it as 'not found'.
             raise ValueError(f"Invoice details not found or issue reported: {error_text}")

        # --- Direct Scraping Logic Based on the Provided HTML Structure ---
        data = {}
        
        # Try to extract data directly from table rows first (based on the HTML you shared)
        try:
            # Find all table rows
            table_rows = soup.find_all('tr')
            
            # Looking for rows with the specific data we need
            for row in table_rows:
                # Find all cells in this row
                cells = row.find_all('td')
                
                # Skip rows with too few cells
                if len(cells) < 2:
                    continue
                
                # Look for <b> tags and their values
                for i, cell in enumerate(cells):
                    b_tag = cell.find('b')
                    if b_tag and i+1 < len(cells):
                        # Get the label text
                        label = b_tag.get_text(strip=True)
                        
                        # Get the value from the next cell
                        value = cells[i+1].get_text(strip=True)
                        
                        # Map the label to appropriate key in our data dictionary
                        if "Control Unit Invoice Number" in label:
                            data['Control Unit Invoice Number'] = value
                        elif "Trader System Invoice No" in label:
                            data['Trader System Invoice No'] = value
                        elif "Invoice Date" in label:
                            data['Invoice Date'] = value
                        elif "Total Taxable Amount" in label:
                            data['Total Taxable Amount'] = value
                        elif "Total Tax Amount" in label:
                            data['Total Tax Amount'] = value
                        elif "Total Invoice Amount" in label:
                            data['Total Invoice Amount'] = value
                        elif "Supplier Name" in label:
                            data['Supplier Name'] = value
            
            # Special case for Total Tax Amount, which might be in a different layout
            if 'Total Tax Amount' not in data or not data['Total Tax Amount']:
                # Look for the cell with this label
                tax_label_cell = None
                for cell in soup.find_all('td', class_="textAlignLeft"):
                    if cell.find('b') and "Total Tax Amount" in cell.get_text():
                        tax_label_cell = cell
                        break
                
                if tax_label_cell:
                    # Try to find adjacent cells that might contain the tax amount
                    next_cells = tax_label_cell.find_next_siblings('td', limit=3)
                    for cell in next_cells:
                        value = cell.get_text(strip=True)
                        if value and value.isdigit():
                            data['Total Tax Amount'] = value
                            break
            
            # Default value for Total Tax Amount if still not found
            if 'Total Tax Amount' not in data or not data['Total Tax Amount']:
                data['Total Tax Amount'] = "0"
                
        except Exception as e:
            logger.error(f"Error during direct table parsing: {e}")
            # We'll continue with the fallback approach below
        
        # If we couldn't extract critical fields, try a more general approach
        if not data.get('Control Unit Invoice Number') or not data.get('Supplier Name'):
            logger.info("Falling back to general HTML parsing approach")
            
            # Helper function to find the value text after a label <td>
            def find_value_after_label(soup_obj, label_text):
                # Find the <td> that contains a <b> tag with the exact or similar label text
                for b_tag in soup_obj.find_all('b'):
                    if label_text in b_tag.get_text(strip=True):
                        # Found the label, get its parent TD
                        label_td = b_tag.find_parent('td')
                        if label_td:
                            # Try to get the next TD's text
                            next_td = label_td.find_next_sibling('td')
                            if next_td and next_td.get_text(strip=True):
                                return next_td.get_text(strip=True)
                            
                            # If that didn't work, try to find the value in nearby TDs
                            for sibling in label_td.find_next_siblings('td', limit=3):
                                text = sibling.get_text(strip=True)
                                if text:
                                    return text
                            
                            # If still no value, the value might be in the same row but in a different column structure
                            row = label_td.find_parent('tr')
                            if row:
                                cells = row.find_all('td')
                                # Skip the first cell (which has our label)
                                for cell in cells[1:]:
                                    text = cell.get_text(strip=True)
                                    if text:
                                        return text
                return ""  # Return empty string if no value found
            
            # Try to extract each field if not already found
            if not data.get('Control Unit Invoice Number'):
                data['Control Unit Invoice Number'] = find_value_after_label(soup, 'Control Unit Invoice Number')
            if not data.get('Trader System Invoice No'):
                data['Trader System Invoice No'] = find_value_after_label(soup, 'Trader System Invoice No')
            if not data.get('Invoice Date'):
                data['Invoice Date'] = find_value_after_label(soup, 'Invoice Date')
            if not data.get('Total Taxable Amount'):
                data['Total Taxable Amount'] = find_value_after_label(soup, 'Total Taxable Amount')
            if not data.get('Total Tax Amount'):
                data['Total Tax Amount'] = find_value_after_label(soup, 'Total Tax Amount') or "0"
            if not data.get('Total Invoice Amount'):
                data['Total Invoice Amount'] = find_value_after_label(soup, 'Total Invoice Amount')
            if not data.get('Supplier Name'):
                data['Supplier Name'] = find_value_after_label(soup, 'Supplier Name')
        
        # --- Validation ---
        # Last attempt: try direct extraction from the raw HTML for critical fields
        if not data.get('Control Unit Invoice Number') or not data.get('Supplier Name'):
            html_str = str(soup)
            # Try to extract invoice number with regex
            invoice_match = re.search(r'Control Unit Invoice Number</b></td>\s*<td[^>]*>([^<]+)', html_str)
            if invoice_match:
                data['Control Unit Invoice Number'] = invoice_match.group(1).strip()
            
            # Try to extract supplier name with regex
            supplier_match = re.search(r'Supplier Name</b></td>\s*<td[^>]*>([^<]+)', html_str)
            if supplier_match:
                data['Supplier Name'] = supplier_match.group(1).strip()
        
        # Final validation
        if not data.get('Control Unit Invoice Number') or not data.get('Supplier Name'):
            logger.error(f"Could not find critical data fields for invoice {invoice_number}. Structure changed?")
            raise ValueError("Could not find expected invoice data on the page. Page structure might have changed.")

        # Ensure invoice number matches what was requested
        if data.get('Control Unit Invoice Number') != invoice_number:
            logger.warning(f"Extracted invoice number ({data.get('Control Unit Invoice Number')}) doesn't match requested number ({invoice_number})")
            # Still continue as this might be a formatting difference or the way KRA displays it
        
        logger.info(f"Successfully scraped data for invoice: {invoice_number}")
        return data

    except requests.exceptions.Timeout:
        logger.error(f"Request to KRA portal timed out for invoice {invoice_number}.")
        raise requests.exceptions.Timeout(f"Request to KRA portal timed out for {invoice_number}.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network or HTTP error fetching data for invoice {invoice_number}: {e}")
        raise requests.exceptions.RequestException(f"Network or HTTP error for {invoice_number}: {e}")
    except ValueError as e:
         logger.warning(f"Value error during scraping for invoice {invoice_number}: {e}")
         raise ValueError(str(e)) # Re-raise ValueErrors specifically for "not found" cases
    except Exception as e:
        # Catch any other unexpected errors during parsing or processing
        logger.error(f"An unexpected error occurred during scraping for invoice {invoice_number}: {e}")
        raise Exception(f"An unexpected error occurred during scraping for {invoice_number}: {e}")


# Define the API endpoint for a single invoice (keep existing one)
@app.get("/invoice/{invoice_number}", response_class=JSONResponse)
async def get_invoice_details_single(invoice_number: str):
    """
    Fetches details for a single KRA Control Unit Invoice Number from the iTax portal.
    """
    logger.info(f"Received single invoice request for: {invoice_number}")
    try:
        # Call the scraping function
        invoice_details = scrape_kra_invoice(invoice_number)
        return invoice_details
    except ValueError as e:
        # Handle specific ValueErrors from scrape function as 404 Not Found
        raise HTTPException(status_code=404, detail=str(e))
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request to KRA portal timed out.")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network or HTTP error fetching data from KRA: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# Define the API endpoint for multiple invoices
@app.post("/invoices/details", response_model=MultipleInvoicesResponse)
async def get_invoice_details_multiple(request_body: InvoiceNumbersRequest):
    """
    Fetches details for a list of KRA Control Unit Invoice Numbers from the iTax portal.

    Processes each invoice number individually and returns results for all.
    """
    invoice_numbers = request_body.invoice_numbers
    logger.info(f"Received multiple invoice request for {len(invoice_numbers)} numbers.")
    results = []

    for invoice_number in invoice_numbers:
        try:
            # Call the scraping function for each invoice number
            data = scrape_kra_invoice(invoice_number)
            # If successful, add a success result
            results.append(InvoiceDetailResult(invoice_number=invoice_number, status="success", data=data, error=None))
        except ValueError as e:
            # Handle "not found" errors specifically
            results.append(InvoiceDetailResult(invoice_number=invoice_number, status="error", data=None, error=str(e)))
        except requests.exceptions.RequestException as e:
            # Handle network/HTTP errors
             results.append(InvoiceDetailResult(invoice_number=invoice_number, status="error", data=None, error=f"Request error: {e}"))
        except Exception as e:
            # Handle any other unexpected errors during scraping
            results.append(InvoiceDetailResult(invoice_number=invoice_number, status="error", data=None, error=f"Unexpected error: {e}"))

    logger.info(f"Finished processing {len(invoice_numbers)} invoices. Returning results.")
    # Return the list of results wrapped in the response model
    return MultipleInvoicesResponse(results=results)


# To run the application:
# uvicorn main:app --reload