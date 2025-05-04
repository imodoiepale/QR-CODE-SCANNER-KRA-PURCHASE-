/**
 * Simple KRA Invoice Checker
 * This script makes a request to check invoice details using an invoice number
 */

// API URL (can be changed as needed)
const API_URL = "https://kra-invoice-checker-production.up.railway.app/invoices/details";

/**
 * Checks a single invoice number against the KRA API
 * @param {string} invoiceNumber - The invoice number to check
 * @returns {Promise} - Promise that resolves with the invoice details
 */
async function checkInvoice(invoiceNumber) {
    try {
        // Validate input
        if (!invoiceNumber || invoiceNumber.trim() === '') {
            throw new Error('Invoice number is required');
        }

        console.log(`Checking invoice: ${invoiceNumber}...`);
        
        // Make the API request
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                invoice_numbers: [invoiceNumber.trim()]
            }),
            // 30 second timeout
            signal: AbortSignal.timeout(30000)
        });

        // Handle API errors
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API error (${response.status}): ${errorText}`);
        }

        // Parse the response
        const data = await response.json();
        console.log('API Response:', data);
        
        // Return the first result (should only be one since we sent one invoice)
        if (data.results && data.results.length > 0) {
            return data.results[0];
        } else {
            throw new Error('No results returned from API');
        }
    } catch (error) {
        console.error('Error checking invoice:', error);
        throw error;
    }
}

/**
 * Example usage:
 * 
 * checkInvoice('0010195720000234911')
 *   .then(result => {
 *     console.log('Invoice check result:', result);
 *     if (result.status === 'success') {
 *       console.log('Invoice data:', result.data);
 *     } else {
 *       console.log('Error:', result.error);
 *     }
 *   })
 *   .catch(error => {
 *     console.error('Failed to check invoice:', error.message);
 *   });
 */

// Optional: Function to display results in a simpler way
function displayInvoiceResult(result) {
    if (!result) {
        console.log('No result to display');
        return;
    }

    console.log(`\nInvoice: ${result.invoice_number}`);
    console.log(`Status: ${result.status.toUpperCase()}`);
    
    if (result.status === 'success' && result.data) {
        console.log('Details:');
        console.log(`- Control Unit Invoice Number: ${result.data['Control Unit Invoice Number'] || 'N/A'}`);
        console.log(`- Trader System Invoice No: ${result.data['Trader System Invoice No'] || 'N/A'}`);
        console.log(`- Invoice Date: ${result.data['Invoice Date'] || 'N/A'}`);
        console.log(`- Total Amount: ${result.data['Total Invoice Amount'] || 'N/A'}`);
        console.log(`- Supplier: ${result.data['Supplier Name'] || 'N/A'}`);
    } else if (result.error) {
        console.log(`Error: ${result.error}`);
    }
}
