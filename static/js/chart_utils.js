/**
 * Creates a chart displaying the status code distribution
 * @param {string} canvasId - The ID of the canvas element
 * @param {object} stats - The statistics object from the API response
 */
function createStatusChart(canvasId, stats) {
    // Get the canvas element
    const canvas = document.getElementById(canvasId);
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Prepare data for the chart
    const data = {
        labels: [
            'Success (200-299)',
            'Redirect (300-399)',
            'Client Error (400-499)',
            'Server Error (500-599)',
            'Other Errors'
        ],
        datasets: [{
            data: [
                stats.status_categories.success,
                stats.status_categories.redirect,
                stats.status_categories.client_error,
                stats.status_categories.server_error,
                stats.status_categories.other
            ],
            backgroundColor: [
                'rgba(40, 167, 69, 0.7)',  // Success - Green
                'rgba(23, 162, 184, 0.7)',  // Redirect - Blue
                'rgba(255, 193, 7, 0.7)',   // Client Error - Yellow
                'rgba(220, 53, 69, 0.7)',   // Server Error - Red
                'rgba(108, 117, 125, 0.7)'  // Other - Gray
            ],
            borderColor: [
                'rgba(40, 167, 69, 1)',
                'rgba(23, 162, 184, 1)',
                'rgba(255, 193, 7, 1)',
                'rgba(220, 53, 69, 1)',
                'rgba(108, 117, 125, 1)'
            ],
            borderWidth: 1
        }]
    };
    
    // Create the chart
    canvas.chart = new Chart(canvas, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#ffffff'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    return canvas.chart;
}

/**
 * Creates a bar chart showing the most common status codes
 * @param {string} canvasId - The ID of the canvas element
 * @param {object} stats - The statistics object from the API response
 */
function createStatusCodesChart(canvasId, stats) {
    // Get the canvas element
    const canvas = document.getElementById(canvasId);
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Get the status counts and sort them
    const statusCounts = stats.status_counts;
    const sortedCodes = Object.keys(statusCounts).sort((a, b) => statusCounts[b] - statusCounts[a]);
    
    // Take only the top 10 status codes
    const topCodes = sortedCodes.slice(0, 10);
    const topValues = topCodes.map(code => statusCounts[code]);
    
    // Color mapping function
    function getColorForStatusCode(code) {
        code = parseInt(code);
        if (code >= 200 && code < 300) {
            return 'rgba(40, 167, 69, 0.7)';  // Success - Green
        } else if (code >= 300 && code < 400) {
            return 'rgba(23, 162, 184, 0.7)';  // Redirect - Blue
        } else if (code >= 400 && code < 500) {
            return 'rgba(255, 193, 7, 0.7)';   // Client Error - Yellow
        } else if (code >= 500 && code < 600) {
            return 'rgba(220, 53, 69, 0.7)';   // Server Error - Red
        } else {
            return 'rgba(108, 117, 125, 0.7)';  // Other - Gray
        }
    }
    
    // Prepare data for the chart
    const data = {
        labels: topCodes.map(code => `Status ${code}`),
        datasets: [{
            label: 'Count',
            data: topValues,
            backgroundColor: topCodes.map(getColorForStatusCode),
            borderColor: topCodes.map(code => getColorForStatusCode(code).replace('0.7', '1')),
            borderWidth: 1
        }]
    };
    
    // Create the chart
    canvas.chart = new Chart(canvas, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return `Status Code: ${context[0].label.replace('Status ', '')}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#ffffff'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#ffffff'
                    }
                }
            }
        }
    });
    
    return canvas.chart;
}
