from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import re
import uvicorn
import logging
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="KRA Invoice Checker API",
    description="API to fetch invoice details from the KRA iTax portal.",
    version="1.1.0" # Updated version
)

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Base URL for the KRA invoice check
KRA_BASE_URL = "https://itax.kra.go.ke/KRA-Portal/invoiceChk.htm"

# Configure session parameters
REQUEST_TIMEOUT = 20
MAX_CONCURRENT_REQUESTS = 5  # Limit concurrent requests to avoid overloading the KRA server

# Semaphore to limit concurrent requests
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

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


async def scrape_kra_invoice_async(invoice_number: str, session: aiohttp.ClientSession) -> Dict[str, str]:
    """
    Asynchronously fetches and scrapes invoice details from the KRA iTax portal for a single invoice.

    Args:
        invoice_number: The KRA Control Unit Invoice Number.
        session: Async HTTP session to use for the request.

    Returns:
        A dictionary containing the extracted invoice data if successful.

    Raises:
        aiohttp.ClientError: For network or HTTP errors.
        ValueError: If expected data is not found on the page (indicating invoice not found or structure change).
        Exception: For any other unexpected errors.
    """
    url = f"{KRA_BASE_URL}?actionCode=loadPage&invoiceNo={invoice_number}"
    logger.info(f"Attempting to scrape invoice: {invoice_number} from {url}")

    async with semaphore:  # Limit concurrent requests
        try:
            # Make the request with a timeout
            async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
                if response.status != 200:
                    logger.error(f"HTTP error {response.status} fetching data for invoice {invoice_number}")
                    raise ValueError(f"HTTP error: {response.status}")
                
                # Read the response content
                html_content = await response.text()
                
                # Use lxml parser for better performance
                soup = BeautifulSoup(html_content, 'lxml')

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
                
                # Try to extract data directly from table rows first
                try:
                    # First attempt: Use CSS selector to find the main fieldset table
                    # This is matching the selector from the user comment
                    main_table = soup.select_one("fieldset > table")
                    
                    if main_table:
                        # Process each row in the table
                        rows = main_table.find_all('tr')
                        
                        for row in rows:
                            cells = row.find_all('td')
                            
                            # Process all cells looking for labels and values
                            for i in range(len(cells)):
                                cell = cells[i]
                                b_tag = cell.find('b')
                                
                                if b_tag:
                                    label = b_tag.get_text(strip=True)
                                    
                                    # Handle different fields with specific logic
                                    if "Control Unit Invoice Number" in label and i+1 < len(cells):
                                        data['Control Unit Invoice Number'] = cells[i+1].get_text(strip=True)
                                    
                                    elif "Trader System Invoice No" in label and i+1 < len(cells):
                                        data['Trader System Invoice No'] = cells[i+1].get_text(strip=True)
                                    
                                    elif "Invoice Date" in label and i+1 < len(cells):
                                        data['Invoice Date'] = cells[i+1].get_text(strip=True)
                                    
                                    elif "Total Taxable Amount" in label and i+1 < len(cells):
                                        data['Total Taxable Amount'] = cells[i+1].get_text(strip=True)
                                    
                                    elif "Total Tax Amount" in label:
                                        # Special handling for Total Tax Amount
                                        # Look for value in the same row
                                        tax_amount = ""
                                        for j in range(i+1, len(cells)):
                                            text = cells[j].get_text(strip=True)
                                            if text:
                                                tax_amount = text
                                                break
                                        
                                        data['Total Tax Amount'] = tax_amount or "0"
                                    
                                    elif "Total Invoice Amount" in label:
                                        # Special handling for Total Invoice Amount
                                        # It's often in a different position
                                        
                                        # First check next cell (standard position)
                                        if i+1 < len(cells) and cells[i+1].get_text(strip=True):
                                            data['Total Invoice Amount'] = cells[i+1].get_text(strip=True)
                                        else:
                                            # Look for value elsewhere in the row
                                            for j in range(i+1, len(cells)):
                                                text = cells[j].get_text(strip=True)
                                                if text:
                                                    data['Total Invoice Amount'] = text
                                                    break
                                    
                                    elif "Supplier Name" in label and i+1 < len(cells):
                                        data['Supplier Name'] = cells[i+1].get_text(strip=True)
                        
                        # If Total Invoice Amount wasn't found, try specific cell positions from the HTML structure
                        if 'Total Invoice Amount' not in data or not data['Total Invoice Amount']:
                            # Check if we have the 3rd row with expected structure
                            if len(rows) >= 3:
                                third_row_cells = rows[2].find_all('td')
                                # Check if the 6th cell contains a value (based on the HTML structure)
                                if len(third_row_cells) >= 6:
                                    invoice_amount = third_row_cells[5].get_text(strip=True)
                                    if invoice_amount:
                                        data['Total Invoice Amount'] = invoice_amount
                    
                except Exception as e:
                    logger.error(f"Error during primary table parsing: {e}")
                
                # If primary extraction failed, try the fallback approach
                if not data.get('Control Unit Invoice Number') or not data.get('Supplier Name'):
                    logger.info(f"Primary parsing failed for {invoice_number}, using fallback methods")
                    
                    # Try regex extraction directly from HTML for speed
                    html_str = str(soup)
                    
                    # Extract invoice number
                    if not data.get('Control Unit Invoice Number'):
                        invoice_match = re.search(r'Control Unit Invoice Number</b></td>\s*<td[^>]*>([^<]+)', html_str)
                        if invoice_match:
                            data['Control Unit Invoice Number'] = invoice_match.group(1).strip()
                    
                    # Extract trader system invoice number
                    if not data.get('Trader System Invoice No'):
                        trader_match = re.search(r'Trader System Invoice No</b></td>\s*<td[^>]*>([^<]+)', html_str)
                        if trader_match:
                            data['Trader System Invoice No'] = trader_match.group(1).strip()
                    
                    # Extract invoice date
                    if not data.get('Invoice Date'):
                        date_match = re.search(r'Invoice Date</b></td>\s*<td[^>]*>([^<]+)', html_str)
                        if date_match:
                            data['Invoice Date'] = date_match.group(1).strip()
                    
                    # Extract taxable amount
                    if not data.get('Total Taxable Amount'):
                        taxable_match = re.search(r'Total Taxable Amount</b></td>\s*<td[^>]*>([^<]+)', html_str)
                        if taxable_match:
                            data['Total Taxable Amount'] = taxable_match.group(1).strip()
                    
                    # Extract tax amount
                    if not data.get('Total Tax Amount'):
                        tax_match = re.search(r'Total Tax Amount</b></td>\s*<td[^>]*>\s*</td>\s*<td[^>]*>([^<]+)', html_str)
                        if tax_match:
                            data['Total Tax Amount'] = tax_match.group(1).strip()
                        else:
                            data['Total Tax Amount'] = "0"
                    
                    # Extract invoice amount
                    if not data.get('Total Invoice Amount'):
                        amount_match = re.search(r'Total Invoice Amount</b></td>\s*<td[^>]*>\s*</td>\s*<td[^>]*>([^<]+)', html_str)
                        if amount_match:
                            data['Total Invoice Amount'] = amount_match.group(1).strip()
                    
                    # Extract supplier name
                    if not data.get('Supplier Name'):
                        supplier_match = re.search(r'Supplier Name</b></td>\s*<td[^>]*>([^<]+)', html_str)
                        if supplier_match:
                            data['Supplier Name'] = supplier_match.group(1).strip()
                
                # --- Final validation ---
                if not data.get('Control Unit Invoice Number') or not data.get('Supplier Name'):
                    logger.error(f"Could not find critical data fields for invoice {invoice_number}. Structure changed?")
                    raise ValueError("Could not find expected invoice data on the page. Page structure might have changed.")
                
                # Set default values for missing fields
                if not data.get('Total Tax Amount'):
                    data['Total Tax Amount'] = "0"
                
                # Ensure invoice number matches what was requested, accounting for potential formatting differences
                extracted_invoice = data.get('Control Unit Invoice Number', '').strip()
                if extracted_invoice and extracted_invoice != invoice_number:
                    logger.warning(f"Extracted invoice number ({extracted_invoice}) doesn't match requested number ({invoice_number})")
                    # Still continue as this might be a formatting difference or the way KRA displays it
                
                logger.info(f"Successfully scraped data for invoice: {invoice_number}")
                return data

        except asyncio.TimeoutError:
            logger.error(f"Request to KRA portal timed out for invoice {invoice_number}.")
            raise ValueError(f"Request to KRA portal timed out for {invoice_number}.")
        except aiohttp.ClientError as e:
            logger.error(f"Network or HTTP error fetching data for invoice {invoice_number}: {e}")
            raise ValueError(f"Network or HTTP error for {invoice_number}: {e}")
        except ValueError as e:
            logger.warning(f"Value error during scraping for invoice {invoice_number}: {e}")
            raise ValueError(str(e))
        except Exception as e:
            # Catch any other unexpected errors during parsing or processing
            logger.error(f"An unexpected error occurred during scraping for invoice {invoice_number}: {e}")
            raise ValueError(f"An unexpected error occurred during scraping for {invoice_number}: {e}")


def scrape_kra_invoice(invoice_number: str) -> Dict[str, str]:
    """
    Synchronous wrapper for the async scraping function.

    Args:
        invoice_number: The KRA Control Unit Invoice Number.

    Returns:
        A dictionary containing the extracted invoice data if successful.
    """
    async def _scrape():
        async with aiohttp.ClientSession() as session:
            return await scrape_kra_invoice_async(invoice_number, session)
    
    # Run the async function in the current event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If inside an async context, create a new event loop
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_scrape())
        loop.close()
        return result
    else:
        # If not inside an async context, use the existing loop
        return loop.run_until_complete(_scrape())


# Define the API endpoint for a single invoice (keep existing one)
@app.get("/invoice/{invoice_number}", response_class=JSONResponse)
async def get_invoice_details_single(invoice_number: str):
    """
    Fetches details for a single KRA Control Unit Invoice Number from the iTax portal.
    """
    logger.info(f"Received single invoice request for: {invoice_number}")
    try:
        # Call the scraping function through the async version
        async with aiohttp.ClientSession() as session:
            invoice_details = await scrape_kra_invoice_async(invoice_number, session)
        return invoice_details
    except ValueError as e:
        # Handle specific ValueErrors from scrape function as 404 Not Found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # All other errors as 500 Internal Server Error
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# Define the API endpoint for multiple invoices
@app.post("/invoices/details", response_model=MultipleInvoicesResponse)
async def get_invoice_details_multiple(request_body: InvoiceNumbersRequest):
    """
    Fetches details for a list of KRA Control Unit Invoice Numbers from the iTax portal.

    Processes each invoice number in parallel and returns results for all.
    """
    invoice_numbers = request_body.invoice_numbers
    logger.info(f"Received multiple invoice request for {len(invoice_numbers)} numbers.")
    
    # Process invoices in parallel
    async with aiohttp.ClientSession() as session:
        # Create tasks for all invoice numbers
        tasks = []
        for invoice_number in invoice_numbers:
            task = asyncio.create_task(process_invoice(invoice_number, session))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
    
    logger.info(f"Finished processing {len(invoice_numbers)} invoices. Returning results.")
    # Return the list of results wrapped in the response model
    return MultipleInvoicesResponse(results=results)


async def process_invoice(invoice_number: str, session: aiohttp.ClientSession) -> InvoiceDetailResult:
    """
    Process a single invoice and return a result object.
    
    Args:
        invoice_number: The invoice number to process
        session: The aiohttp client session to use
        
    Returns:
        An InvoiceDetailResult object with the processing result
    """
    try:
        # Call the scraping function for each invoice number
        data = await scrape_kra_invoice_async(invoice_number, session)
        # If successful, add a success result
        return InvoiceDetailResult(
            invoice_number=invoice_number,
            status="success",
            data=data,
            error=None
        )
    except ValueError as e:
        # Handle "not found" errors specifically
        return InvoiceDetailResult(
            invoice_number=invoice_number,
            status="error",
            data=None,
            error=str(e)
        )
    except Exception as e:
        # Handle any other unexpected errors during scraping
        return InvoiceDetailResult(
            invoice_number=invoice_number,
            status="error",
            data=None,
            error=f"Unexpected error: {e}"
        )


# To run the application:
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)