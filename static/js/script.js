document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('articleForm');
    const downloadAllButton = document.getElementById('downloadAllPdfs');
    const clearAllUrlsButton = document.getElementById('clearAllUrls');

    // URL validation and form submission
    form.addEventListener('submit', function(event) {
        const urls = Array.from(form.querySelectorAll('input[type="url"]'))
                           .filter(input => input.value.trim() !== '');

        if (urls.length === 0) {
            event.preventDefault();
            alert('Please enter at least one URL');
        } else if (urls.length > 5) {
            event.preventDefault();
            alert('Maximum 5 URLs allowed');
        }
    });

    // Clear All URLs functionality
    clearAllUrlsButton.addEventListener('click', function() {
        const urlInputs = document.querySelectorAll('input[type="url"]');
        urlInputs.forEach(input => input.value = '');
    });
    
    // Download All PDFs functionality
    function setupDownloadAllButton() {
        const pdfLinks = document.querySelectorAll('.download-pdf');
        if (pdfLinks.length > 0) {
            downloadAllButton.style.display = 'inline-block';

            downloadAllButton.onclick = function () {
                const pdfUrls = Array.from(pdfLinks).map(link => link.href);

                // Send AJAX request to Flask to create zip file
                fetch('/zip_pdfs', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({pdf_urls: pdfUrls})
                })
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'downloaded_pdfs.zip';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                })
                .catch(error => console.error('Error creating zip:', error));
            };
        } else {
            downloadAllButton.style.display = 'none';
        }
    }

    // Call on page load and whenever PDFs are added
    setupDownloadAllButton();
});