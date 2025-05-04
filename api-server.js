/**
 * Simple Express server with an API endpoint for checking KRA invoices
 * Run with: node api-server.js
 */

const express = require('express');
const cors = require('cors');
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));
const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public')); // To serve static files if needed

// KRA API URL
const KRA_API_URL = "https://kra-invoice-checker-production.up.railway.app/invoices/details";

// API endpoint for invoice checking
app.post('/api/invoice', async (req, res) => {
    try {
        const { invoiceNumber } = req.body;
        
        if (!invoiceNumber) {
            return res.status(400).json({
                status: 'error',
                message: 'Invoice number is required'
            });
        }
        
        console.log(`Checking invoice: ${invoiceNumber}`);
        
        // Make request to KRA API
        const response = await fetch(KRA_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                invoice_numbers: [invoiceNumber.trim()]
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`KRA API error (${response.status}): ${errorText}`);
        }
        
        const data = await response.json();
        
        // Return the formatted response
        return res.json({
            status: 'success',
            data: data.results && data.results.length > 0 ? data.results[0] : null
        });
        
    } catch (error) {
        console.error('Error checking invoice:', error);
        
        return res.status(500).json({
            status: 'error',
            message: error.message || 'An error occurred while checking the invoice'
        });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
    console.log(`Invoice API endpoint: http://localhost:${PORT}/api/invoice`);
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('Server shutting down...');
    process.exit(0);
});
