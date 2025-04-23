document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const sitemapForm = document.getElementById('sitemapForm');
    const sitemapUrl = document.getElementById('sitemapUrl');
    const submitBtn = document.getElementById('submitBtn');
    const submitText = document.getElementById('submitText');
    const spinnerIcon = document.getElementById('spinnerIcon');
    const processingSection = document.getElementById('processingSection');
    const resultsSection = document.getElementById('resultsSection');
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');
    
    // Summary elements
    const totalUrls = document.getElementById('totalUrls');
    const successCount = document.getElementById('successCount');
    const redirectCount = document.getElementById('redirectCount');
    const clientErrorCount = document.getElementById('clientErrorCount');
    const serverErrorCount = document.getElementById('serverErrorCount');
    const otherCount = document.getElementById('otherCount');
    const processingTime = document.getElementById('processingTime');
    
    // Table elements
    const resultsTableBody = document.getElementById('resultsTableBody');
    const pagination = document.getElementById('pagination');
    
    // Export buttons
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    
    // Store current results
    let currentResults = null;
    let currentPage = 1;
    const itemsPerPage = 100;
    let currentFilter = null; // Track current filter
    
    // Add click handlers for status count badges
    successCount.addEventListener('click', function() {
        toggleFilter('success', 200, 299);
    });
    
    redirectCount.addEventListener('click', function() {
        toggleFilter('redirect', 300, 399);
    });
    
    clientErrorCount.addEventListener('click', function() {
        toggleFilter('client_error', 400, 499);
    });
    
    serverErrorCount.addEventListener('click', function() {
        toggleFilter('server_error', 500, 599);
    });
    
    otherCount.addEventListener('click', function() {
        toggleFilter('other', null, null);
    });
    
    // Handle form submission
    sitemapForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Validate URL
        const url = sitemapUrl.value.trim();
        if (!url) {
            showError('Please enter a sitemap URL');
            return;
        }
        
        // Show processing state
        setProcessingState(true);
        hideResults();
        hideError();
        showProcessing();
        
        // Send request to server
        fetch('/process_sitemap', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ sitemap_url: url }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to process sitemap');
                });
            }
            return response.json();
        })
        .then(data => {
            // Store current results
            currentResults = data;
            
            // Update UI with results
            displayResults(data);
            setProcessingState(false);
            hideProcessing();
            showResults();
        })
        .catch(error => {
            console.error('Error:', error);
            showError(error.message || 'An error occurred while processing the sitemap');
            setProcessingState(false);
            hideProcessing();
        });
    });
    
    // Set up export buttons
    exportCsvBtn.addEventListener('click', function() {
        if (currentResults) {
            exportToCsv(currentResults.results, 'sitemap_results');
        }
    });
    
    exportExcelBtn.addEventListener('click', function() {
        if (currentResults) {
            exportToExcel(currentResults.results, 'sitemap_results');
        }
    });
    
    // Function to display results
    function displayResults(data) {
        // Update summary
        totalUrls.textContent = data.total_urls;
        successCount.textContent = data.stats.status_categories.success;
        redirectCount.textContent = data.stats.status_categories.redirect;
        clientErrorCount.textContent = data.stats.status_categories.client_error;
        serverErrorCount.textContent = data.stats.status_categories.server_error;
        otherCount.textContent = data.stats.status_categories.other;
        processingTime.textContent = `${data.processing_time}s`;
        
        // Create chart
        createStatusChart('statusChart', data.stats);
        
        // Display results table with pagination
        displayResultsTable(data.results, 1);
    }
    
    // Function to display results table with pagination
    function displayResultsTable(results, page) {
        // Clear existing table
        resultsTableBody.innerHTML = '';
        
        // Calculate pagination
        const totalPages = Math.ceil(results.length / itemsPerPage);
        const startIndex = (page - 1) * itemsPerPage;
        const endIndex = Math.min(startIndex + itemsPerPage, results.length);
        
        // Display current page of results
        for (let i = startIndex; i < endIndex; i++) {
            const result = results[i];
            const row = document.createElement('tr');
            
            // Set row class based on status code
            let statusClass = 'status-error';
            if (result.status_code >= 200 && result.status_code < 300) {
                statusClass = 'status-2xx';
            } else if (result.status_code >= 300 && result.status_code < 400) {
                statusClass = 'status-3xx';
            } else if (result.status_code >= 400 && result.status_code < 500) {
                statusClass = 'status-4xx';
            } else if (result.status_code >= 500 && result.status_code < 600) {
                statusClass = 'status-5xx';
            }
            row.classList.add(statusClass);
            
            // URL column with truncation
            const urlCell = document.createElement('td');
            const urlSpan = document.createElement('span');
            urlSpan.classList.add('truncate-url');
            urlSpan.textContent = result.url;
            urlSpan.title = result.url;
            urlCell.appendChild(urlSpan);
            
            // Status code column
            const statusCell = document.createElement('td');
            statusCell.textContent = result.status_code;
            
            // Status message column
            const messageCell = document.createElement('td');
            messageCell.textContent = result.status_message;
            
            // Redirect column
            const redirectCell = document.createElement('td');
            if (result.is_redirect && result.redirect_url) {
                const redirectLink = document.createElement('a');
                redirectLink.href = result.redirect_url;
                redirectLink.target = '_blank';
                redirectLink.textContent = 'View';
                redirectCell.appendChild(redirectLink);
            } else {
                redirectCell.textContent = '-';
            }
            
            // Append cells to row
            row.appendChild(urlCell);
            row.appendChild(statusCell);
            row.appendChild(messageCell);
            row.appendChild(redirectCell);
            
            // Append row to table
            resultsTableBody.appendChild(row);
        }
        
        // Update pagination
        updatePagination(page, totalPages, results);
    }
    
    // Function to update pagination controls
    function updatePagination(currentPage, totalPages, results) {
        pagination.innerHTML = '';
        
        if (totalPages <= 1) {
            return;
        }
        
        // Previous button
        const prevItem = document.createElement('li');
        prevItem.classList.add('page-item');
        if (currentPage === 1) {
            prevItem.classList.add('disabled');
        }
        const prevLink = document.createElement('a');
        prevLink.classList.add('page-link');
        prevLink.href = '#';
        prevLink.setAttribute('aria-label', 'Previous');
        prevLink.innerHTML = '<span aria-hidden="true">&laquo;</span>';
        prevItem.appendChild(prevLink);
        pagination.appendChild(prevItem);
        
        // Calculate page numbers to show
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }
        
        // Page numbers
        for (let i = startPage; i <= endPage; i++) {
            const pageItem = document.createElement('li');
            pageItem.classList.add('page-item');
            if (i === currentPage) {
                pageItem.classList.add('active');
            }
            const pageLink = document.createElement('a');
            pageLink.classList.add('page-link');
            pageLink.href = '#';
            pageLink.textContent = i;
            pageItem.appendChild(pageLink);
            pagination.appendChild(pageItem);
            
            // Add click event
            pageLink.addEventListener('click', function(e) {
                e.preventDefault();
                displayResultsTable(results, i);
            });
        }
        
        // Next button
        const nextItem = document.createElement('li');
        nextItem.classList.add('page-item');
        if (currentPage === totalPages) {
            nextItem.classList.add('disabled');
        }
        const nextLink = document.createElement('a');
        nextLink.classList.add('page-link');
        nextLink.href = '#';
        nextLink.setAttribute('aria-label', 'Next');
        nextLink.innerHTML = '<span aria-hidden="true">&raquo;</span>';
        nextItem.appendChild(nextLink);
        pagination.appendChild(nextItem);
        
        // Add click events for prev/next
        if (currentPage > 1) {
            prevLink.addEventListener('click', function(e) {
                e.preventDefault();
                displayResultsTable(results, currentPage - 1);
            });
        }
        
        if (currentPage < totalPages) {
            nextLink.addEventListener('click', function(e) {
                e.preventDefault();
                displayResultsTable(results, currentPage + 1);
            });
        }
    }
    
    // Helper functions for UI state
    function setProcessingState(isProcessing) {
        if (isProcessing) {
            submitBtn.disabled = true;
            submitText.textContent = 'Processing...';
            spinnerIcon.classList.remove('d-none');
        } else {
            submitBtn.disabled = false;
            submitText.textContent = 'Check Sitemap';
            spinnerIcon.classList.add('d-none');
        }
    }
    
    function showProcessing() {
        processingSection.classList.remove('d-none');
    }
    
    function hideProcessing() {
        processingSection.classList.add('d-none');
    }
    
    function showResults() {
        resultsSection.classList.remove('d-none');
    }
    
    function hideResults() {
        resultsSection.classList.add('d-none');
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorSection.classList.remove('d-none');
    }
    
    function hideError() {
        errorSection.classList.add('d-none');
    }
    
    // Set sample URL if needed
    if (!sitemapUrl.value) {
        sitemapUrl.value = 'https://www.goibibo.com/hotels/sitemap_gi-hotels-gi_city_under_price_template-1-new.xml';
    }
    
    // Function to toggle filter
    function toggleFilter(filterName, minStatus, maxStatus) {
        if (currentFilter === filterName) {
            // If clicking the same filter, remove it
            currentFilter = null;
            // Reset badge styles
            resetBadgeStyles();
            // Show all results
            if (currentResults) {
                displayResultsTable(currentResults.results, 1);
            }
        } else {
            // Apply new filter
            currentFilter = filterName;
            // Reset and highlight selected badge
            resetBadgeStyles();
            highlightBadge(filterName);
            // Filter and display results
            if (currentResults) {
                const filteredResults = filterResults(currentResults.results, minStatus, maxStatus);
                displayResultsTable(filteredResults, 1);
            }
        }
    }
    
    // Function to filter results
    function filterResults(results, minStatus, maxStatus) {
        if (!minStatus && !maxStatus) {
            // Handle "other" category
            return results.filter(result => {
                const status = result.status_code;
                return status < 200 || status >= 600 || isNaN(status);
            });
        }
        return results.filter(result => {
            const status = result.status_code;
            return status >= minStatus && status <= maxStatus;
        });
    }
    
    // Function to reset badge styles
    function resetBadgeStyles() {
        [successCount, redirectCount, clientErrorCount, serverErrorCount, otherCount].forEach(badge => {
            badge.style.cursor = 'pointer';
            badge.style.opacity = '1';
        });
    }
    
    // Function to highlight active badge
    function highlightBadge(filterName) {
        const badgeMap = {
            'success': successCount,
            'redirect': redirectCount,
            'client_error': clientErrorCount,
            'server_error': serverErrorCount,
            'other': otherCount
        };
        
        Object.entries(badgeMap).forEach(([name, badge]) => {
            if (name === filterName) {
                badge.style.opacity = '1';
            } else {
                badge.style.opacity = '0.5';
            }
        });
    }
});

