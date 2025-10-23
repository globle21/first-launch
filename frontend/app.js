/**
 * Frontend Application for Product Discovery
 * Handles API communication, real-time updates, and UI interactions
 */

// Configuration
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000'
    : 'https://your-backend-app.onrender.com'; // Replace with your Render backend URL

// Global state
let currentSessionId = null;
let selectedProductIndex = null;
let selectedVariantIndex = null;
let eventSource = null;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeEnterKeyHandlers();
});

/**
 * Initialize tab switching
 */
function initializeTabs() {
    const tabs = document.querySelectorAll('.tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Update active content
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => {
                if (content.getAttribute('data-content') === tabName) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });
        });
    });
}

/**
 * Initialize Enter key handlers for inputs
 */
function initializeEnterKeyHandlers() {
    document.getElementById('keyword-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            startSearch('keyword');
        }
    });
    
    document.getElementById('url-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            startSearch('url');
        }
    });
}

// ============================================================================
// Search Flow
// ============================================================================

/**
 * Start search workflow
 */
async function startSearch(inputType) {
    // Get input value
    const input = inputType === 'keyword' 
        ? document.getElementById('keyword-input').value.trim()
        : document.getElementById('url-input').value.trim();
    
    // Validate input
    if (!input) {
        alert('Please enter a search query');
        return;
    }
    
    // Show loading
    showLoading(true);
    
    try {
        // Call API to start workflow
        const response = await fetch(`${API_BASE_URL}/api/workflow/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                input_type: inputType,
                user_input: input
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        currentSessionId = data.session_id;
        
        // Hide input section, show progress section
        hideAllSections();
        showSection('progress-section');
        
        // Start listening for progress updates
        startProgressStream();
        
        showLoading(false);
        
    } catch (error) {
        showLoading(false);
        showError(`Failed to start search: ${error.message}`);
    }
}

/**
 * Start Server-Sent Events stream for progress updates
 */
function startProgressStream() {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource(`${API_BASE_URL}/api/workflow/progress/${currentSessionId}`);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'log') {
            addProgressLog(data.data);
        } else if (data.type === 'status') {
            handleStatusUpdate(data.data);
        } else if (data.type === 'complete') {
            handleWorkflowComplete(data.data);
        } else if (data.type === 'error') {
            handleWorkflowError(data.data);
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('SSE Error:', error);
        eventSource.close();
    };
}

/**
 * Add progress log entry
 */
function addProgressLog(logData) {
    const logsContainer = document.getElementById('progress-logs');
    
    const logEntry = document.createElement('div');
    logEntry.className = 'progress-log';
    
    const statusIcon = {
        'started': '🔄',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'waiting': '⏳',
        'skipped': '⏭️'
    }[logData.status] || '📝';
    
    logEntry.innerHTML = `
        <div>${statusIcon} <strong>${logData.stage}</strong>: ${logData.message}</div>
        <div class="progress-log-time">${new Date(logData.timestamp).toLocaleTimeString()}</div>
    `;
    
    logsContainer.appendChild(logEntry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

/**
 * Handle status updates
 */
async function handleStatusUpdate(statusData) {
    // Check if confirmation is needed
    if (statusData.needs_product_confirmation) {
        await showProductConfirmation();
    } else if (statusData.needs_variant_confirmation) {
        await showVariantConfirmation();
    } else if (statusData.needs_url_extraction_confirmation) {
        await showExtractionConfirmation();
    }
}

/**
 * Show product confirmation UI
 */
async function showProductConfirmation() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/workflow/status/${currentSessionId}`);
        const data = await response.json();
        
        if (!data.needs_product_confirmation) return;
        
        // Check if we're already showing this confirmation (prevent re-rendering)
        const currentSection = document.getElementById('confirmation-section');
        const productConfirmation = document.getElementById('product-confirmation');
        if (!currentSection.classList.contains('hidden') && !productConfirmation.classList.contains('hidden')) {
            return; // Already showing product confirmation, don't recreate
        }
        
        hideAllSections();
        showSection('confirmation-section');
        
        document.getElementById('confirmation-title').textContent = 'Select Product';
        document.getElementById('confirmation-message').textContent = 
            `We found ${data.product_candidates.length} matching products. Please select the correct one:`;
        
        // Show product confirmation content
        document.getElementById('product-confirmation').classList.remove('hidden');
        document.getElementById('variant-confirmation').classList.add('hidden');
        document.getElementById('extraction-confirmation').classList.add('hidden');
        
        // Populate product list (only once)
        const productList = document.getElementById('product-list');
        productList.innerHTML = '';
        
        data.product_candidates.forEach((product, index) => {
            const item = document.createElement('div');
            item.className = 'confirmation-item';
            item.onclick = () => selectItem('product', index);
            
            item.innerHTML = `
                <div class="confirmation-radio"></div>
                <div class="confirmation-details">
                    <strong>${product.name}</strong>
                    <small>${product.url}</small>
                    ${product.description ? `<small>${product.description}</small>` : ''}
                </div>
            `;
            
            productList.appendChild(item);
        });
        
    } catch (error) {
        console.error('Failed to load product confirmation:', error);
    }
}

/**
 * Show variant confirmation UI
 */
async function showVariantConfirmation() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/workflow/status/${currentSessionId}`);
        const data = await response.json();
        
        if (!data.needs_variant_confirmation) return;
        
        // Check if we're already showing this confirmation (prevent re-rendering)
        const currentSection = document.getElementById('confirmation-section');
        const variantConfirmation = document.getElementById('variant-confirmation');
        if (!currentSection.classList.contains('hidden') && !variantConfirmation.classList.contains('hidden')) {
            return; // Already showing variant confirmation, don't recreate
        }
        
        hideAllSections();
        showSection('confirmation-section');
        
        document.getElementById('confirmation-title').textContent = 'Select Variant';
        document.getElementById('confirmation-message').textContent = 
            `We found ${data.variant_candidates.length} variants. Please select the one you want:`;
        
        // Show variant confirmation content
        document.getElementById('product-confirmation').classList.add('hidden');
        document.getElementById('variant-confirmation').classList.remove('hidden');
        document.getElementById('extraction-confirmation').classList.add('hidden');
        
        // Populate variant list (only once)
        const variantList = document.getElementById('variant-list');
        variantList.innerHTML = '';
        
        data.variant_candidates.forEach((variant, index) => {
            const item = document.createElement('div');
            item.className = 'confirmation-item';
            item.onclick = () => selectItem('variant', index);
            
            item.innerHTML = `
                <div class="confirmation-radio"></div>
                <div class="confirmation-details">
                    <strong>${variant.value}</strong>
                    <small>Type: ${variant.type}</small>
                </div>
            `;
            
            variantList.appendChild(item);
        });
        
    } catch (error) {
        console.error('Failed to load variant confirmation:', error);
    }
}

/**
 * Show URL extraction confirmation UI
 */
async function showExtractionConfirmation() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/workflow/status/${currentSessionId}`);
        const data = await response.json();
        
        if (!data.needs_url_extraction_confirmation) return;
        
        hideAllSections();
        showSection('confirmation-section');
        
        document.getElementById('confirmation-title').textContent = 'Confirm Extracted Details';
        document.getElementById('confirmation-message').textContent = 
            'We extracted the following details from the URL. Are they correct?';
        
        // Show extraction confirmation content
        document.getElementById('product-confirmation').classList.add('hidden');
        document.getElementById('variant-confirmation').classList.add('hidden');
        document.getElementById('extraction-confirmation').classList.remove('hidden');
        
        // Populate extracted details
        const detailsContainer = document.getElementById('extracted-details');
        detailsContainer.innerHTML = `
            <div>
                <strong>Brand</strong>
                <span>${data.extracted_details.brand}</span>
            </div>
            <div>
                <strong>Product</strong>
                <span>${data.extracted_details.product}</span>
            </div>
            <div>
                <strong>Variant</strong>
                <span>${data.extracted_details.variant}</span>
            </div>
        `;
        
    } catch (error) {
        console.error('Failed to load extraction confirmation:', error);
    }
}

/**
 * Select confirmation item
 */
function selectItem(type, index) {
    const listId = type === 'product' ? 'product-list' : 'variant-list';
    const items = document.querySelectorAll(`#${listId} .confirmation-item`);
    
    items.forEach((item, i) => {
        if (i === index) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
    
    if (type === 'product') {
        selectedProductIndex = index;
    } else {
        selectedVariantIndex = index;
    }
}

/**
 * Confirm selection (product or variant)
 */
async function confirmSelection(type) {
    const index = type === 'product' ? selectedProductIndex : selectedVariantIndex;
    
    if (index === null) {
        alert(`Please select a ${type}`);
        return;
    }
    
    showLoading(true);
    
    try {
        const endpoint = type === 'product' 
            ? `/api/workflow/confirm-product/${currentSessionId}`
            : `/api/workflow/confirm-variant/${currentSessionId}`;
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                [`${type}_index`]: index
            })
        });
        
        if (!response.ok) {
            throw new Error(`Confirmation failed: ${response.status}`);
        }
        
        // Reset selection
        if (type === 'product') {
            selectedProductIndex = null;
        } else {
            selectedVariantIndex = null;
        }
        
        // Go back to progress view
        hideAllSections();
        showSection('progress-section');
        
        showLoading(false);
        
    } catch (error) {
        showLoading(false);
        showError(`Failed to confirm ${type}: ${error.message}`);
    }
}

/**
 * Confirm or reject URL extraction
 */
async function confirmExtraction(confirmed) {
    showLoading(true);
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/workflow/confirm-extraction/${currentSessionId}`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ confirmed })
            }
        );
        
        if (!response.ok) {
            throw new Error(`Confirmation failed: ${response.status}`);
        }
        
        if (confirmed) {
            // Go back to progress view
            hideAllSections();
            showSection('progress-section');
        } else {
            // Show error
            showError('Extraction rejected. Please try with keywords instead.');
        }
        
        showLoading(false);
        
    } catch (error) {
        showLoading(false);
        showError(`Failed to confirm extraction: ${error.message}`);
    }
}

/**
 * Handle workflow completion
 */
function handleWorkflowComplete(data) {
    if (eventSource) {
        eventSource.close();
    }
    
    hideAllSections();
    showSection('results-section');
    
    displayResults(data.results);
}

/**
 * Handle workflow error
 */
function handleWorkflowError(data) {
    if (eventSource) {
        eventSource.close();
    }
    
    showError(data.error || 'Workflow failed');
}

/**
 * Display results
 */
function displayResults(results) {
    const resultsGrid = document.getElementById('results-grid');
    const resultsCount = document.getElementById('results-count');
    
    resultsCount.textContent = `${results.length} product${results.length !== 1 ? 's' : ''} found`;
    
    resultsGrid.innerHTML = '';
    
    results.forEach(result => {
        const card = document.createElement('div');
        card.className = 'result-card';
        
        const productType = result.product_type || 'individual';
        const perUnitPrice = result.per_unit_price;
        const price = result.price;
        const productName = result.product_name || result.name || 'Unknown Product';
        const platform = result.platform || 'Unknown Platform';
        const url = result.url || '#';
        
        // Determine what price to show
        let priceDisplay = '';
        let priceLabel = '';
        
        if (perUnitPrice && perUnitPrice !== 'null') {
            priceDisplay = `₹${parseFloat(perUnitPrice).toFixed(2)}`;
            priceLabel = 'Per Unit Price';
        } else if (price && price !== 'null') {
            priceDisplay = `₹${parseFloat(price).toFixed(2)}`;
            priceLabel = 'Price';
        } else {
            priceDisplay = 'Price not available';
            priceLabel = '';
        }
        
        card.innerHTML = `
            <div class="result-badge ${productType}">${productType.toUpperCase()}</div>
            <div class="result-price">${priceDisplay}</div>
            ${priceLabel ? `<div class="result-price-label">${priceLabel}</div>` : ''}
            <div class="result-name">${productName}</div>
            <div class="result-platform">${platform}</div>
            <a href="${url}" target="_blank" class="result-link">View Product</a>
        `;
        
        resultsGrid.appendChild(card);
    });
}

// ============================================================================
// UI Helpers
// ============================================================================

/**
 * Show/hide sections
 */
function hideAllSections() {
    const sections = ['input-section', 'progress-section', 'confirmation-section', 'results-section', 'error-section'];
    sections.forEach(id => {
        document.getElementById(id).classList.add('hidden');
    });
}

function showSection(sectionId) {
    document.getElementById(sectionId).classList.remove('hidden');
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
    }
}

/**
 * Show error
 */
function showError(message) {
    hideAllSections();
    showSection('error-section');
    document.getElementById('error-message').textContent = message;
}

/**
 * Reset search (start over)
 */
function resetSearch() {
    // Close SSE connection
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    
    // Reset state
    currentSessionId = null;
    selectedProductIndex = null;
    selectedVariantIndex = null;
    
    // Clear inputs
    document.getElementById('keyword-input').value = '';
    document.getElementById('url-input').value = '';
    
    // Clear progress logs
    document.getElementById('progress-logs').innerHTML = '';
    
    // Show input section
    hideAllSections();
    showSection('input-section');
}
