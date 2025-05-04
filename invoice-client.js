/**
 * Simple client for interacting with the local invoice API
 * This provides functions to use in your front-end applications
 */

// Local API endpoint
const API_URL = "http://localhost:3000/api/invoice";

/**
 * Check an invoice using the local API server
 * @param {string} invoiceNumber - The invoice number to check
 * @returns {Promise} - Promise resolving with the invoice details
 */
async function checkInvoice(invoiceNumber) {
    try {
        console.log(`Sending request to check invoice: ${invoiceNumber}`);
        
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ invoiceNumber })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API error (${response.status}): ${errorText}`);
        }
        
        const result = await response.json();
        console.log('Invoice check result:', result);
        
        return result;
    } catch (error) {
        console.error('Error checking invoice:', error);
        throw error;
    }
}

// Example usage in browser:
/*
  // Call the function when a button is clicked
  document.getElementById('checkButton').addEventListener('click', async () => {
    const invoiceNumber = document.getElementById('invoiceInput').value;
    
    try {
      const result = await checkInvoice(invoiceNumber);
      
      if (result.status === 'success' && result.data) {
        // Show the invoice details
        displayInvoiceDetails(result.data);
      } else {
        // Show error message
        showError(result.message || 'Failed to check invoice');
      }
    } catch (error) {
      showError(error.message);
    }
  });
  
  function displayInvoiceDetails(invoice) {
    // Your code to display invoice details in the UI
    console.log('Invoice details:', invoice);
  }
  
  function showError(message) {
    // Your code to show error message in the UI
    console.error('Error:', message);
  }
*/
