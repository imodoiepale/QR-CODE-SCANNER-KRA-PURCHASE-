/**
 * Command-line KRA Invoice Checker
 * Run with: node check_invoice.js [invoice_number]
 */

// Import the core functions
const API_URL = "https://kra-invoice-checker-production.up.railway.app/invoices/details";

// Get the invoice number from command line arguments
const invoiceNumber = process.argv[2];

if (!invoiceNumber) {
    console.error('Error: Please provide an invoice number');
    console.error('Usage: node check_invoice.js [invoice_number]');
    process.exit(1);
}

// Function to check an invoice
async function checkInvoice(invoiceNumber) {
    try {
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
            })
        });

        // Handle API errors
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API error (${response.status}): ${errorText}`);
        }

        // Parse the response
        const data = await response.json();
        
        // Return the first result
        if (data.results && data.results.length > 0) {
            return data.results[0];
        } else {
            throw new Error('No results returned from API');
        }
    } catch (error) {
        console.error('Error checking invoice:', error.message);
        return { status: 'error', error: error.message };
    }
}

// Display invoice result in a nice format
function displayInvoiceResult(result) {
    console.log('\n========== INVOICE CHECK RESULT ==========');
    console.log(`Invoice Number: ${result.invoice_number}`);
    console.log(`Status: ${result.status.toUpperCase()}`);
    
    if (result.status === 'success' && result.data) {
        console.log('\nINVOICE DETAILS:');
        console.log(`Control Unit Invoice Number: ${result.data['Control Unit Invoice Number'] || 'N/A'}`);
        console.log(`Trader System Invoice No: ${result.data['Trader System Invoice No'] || 'N/A'}`);
        console.log(`Invoice Date: ${result.data['Invoice Date'] || 'N/A'}`);
        console.log(`Total Taxable Amount: ${result.data['Total Taxable Amount'] || 'N/A'}`);
        console.log(`Total Tax Amount: ${result.data['Total Tax Amount'] || 'N/A'}`);
        console.log(`Total Invoice Amount: ${result.data['Total Invoice Amount'] || 'N/A'}`);
        console.log(`Supplier Name: ${result.data['Supplier Name'] || 'N/A'}`);
    } else if (result.error) {
        console.log(`\nERROR: ${result.error}`);
    }
    console.log('=========================================\n');
}

// Main execution
(async () => {
    try {
        const result = await checkInvoice(invoiceNumber);
        displayInvoiceResult(result);
    } catch (error) {
        console.error('Failed to check invoice:', error.message);
    }
})();
