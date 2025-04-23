/**
 * Exports the results to a CSV file
 * @param {Array} results - The array of URL status results
 * @param {string} filename - The name of the file to download
 */
function exportToCsv(results, filename) {
    // Create CSV content
    let csvContent = 'URL,Status Code,Status Message,Is Redirect,Redirect URL\n';
    
    // Add each result as a row
    results.forEach(result => {
        // Handle special characters in CSV
        const url = `"${result.url.replace(/"/g, '""')}"`;
        const statusMessage = `"${result.status_message ? result.status_message.replace(/"/g, '""') : ''}"`;
        const redirectUrl = result.redirect_url ? `"${result.redirect_url.replace(/"/g, '""')}"` : '""';
        
        csvContent += `${url},${result.status_code},${statusMessage},${result.is_redirect},${redirectUrl}\n`;
    });
    
    // Create and download the file
    downloadFile(csvContent, `${filename}.csv`, 'text/csv');
}

/**
 * Exports the results to an Excel file
 * @param {Array} results - The array of URL status results
 * @param {string} filename - The name of the file to download
 */
function exportToExcel(results, filename) {
    // Convert results to worksheet data
    const worksheetData = [
        ['URL', 'Status Code', 'Status Message', 'Is Redirect', 'Redirect URL']
    ];
    
    // Add each result as a row
    results.forEach(result => {
        worksheetData.push([
            result.url,
            result.status_code,
            result.status_message || '',
            result.is_redirect ? 'Yes' : 'No',
            result.redirect_url || ''
        ]);
    });
    
    // Create a new workbook
    const workbook = XLSX.utils.book_new();
    
    // Add a worksheet
    const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);
    
    // Add the worksheet to the workbook
    XLSX.utils.book_append_sheet(workbook, worksheet, 'URL Status');
    
    // Generate Excel file
    const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
    
    // Convert buffer to Blob
    const blob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    
    // Download the file
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Helper function to download a file
 * @param {string} content - The content of the file
 * @param {string} filename - The name of the file
 * @param {string} contentType - The MIME type of the file
 */
function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Formats the results data for export with additional summary information
 * @param {Object} data - The complete results data from the API
 * @return {Array} Formatted array of data rows
 */
function formatDataForExport(data) {
    const formattedData = [];
    
    // Add summary information
    formattedData.push(['Sitemap Monitor Report']);
    formattedData.push(['Generated on', new Date().toLocaleString()]);
    formattedData.push(['Sitemap URL', data.sitemap_url]);
    formattedData.push(['Processing Time', `${data.processing_time} seconds`]);
    formattedData.push(['Total URLs', data.total_urls]);
    formattedData.push([]);
    
    // Add status summary
    formattedData.push(['Status Summary']);
    formattedData.push(['Success (200-299)', data.stats.status_categories.success]);
    formattedData.push(['Redirect (300-399)', data.stats.status_categories.redirect]);
    formattedData.push(['Client Error (400-499)', data.stats.status_categories.client_error]);
    formattedData.push(['Server Error (500-599)', data.stats.status_categories.server_error]);
    formattedData.push(['Other Errors', data.stats.status_categories.other]);
    formattedData.push([]);
    
    // Add detailed results header
    formattedData.push(['URL Details']);
    formattedData.push(['URL', 'Status Code', 'Status Message', 'Is Redirect', 'Redirect URL']);
    
    // Add each result
    data.results.forEach(result => {
        formattedData.push([
            result.url,
            result.status_code,
            result.status_message || '',
            result.is_redirect ? 'Yes' : 'No',
            result.redirect_url || ''
        ]);
    });
    
    return formattedData;
}
