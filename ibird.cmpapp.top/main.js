let csvContent = '';

function parseChineseDate(dateStr) {
    // Expected format: "DD日 MM月 YYYY年" (e.g., "11日 6月 2025年")
    const match = dateStr.match(/^(\d{1,2})日\s*(\d{1,2})月\s*(\d{4})年$/);
    if (!match) {
        return null;
    }
    const [, day, month, year] = match;
    // Create Date object (month is 0-based in JavaScript)
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    if (isNaN(date.getTime())) {
        return null;
    }
    return date;
}

function formatDate(dateStr) {
    const date = parseChineseDate(dateStr);
    return date ? date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    }) : dateStr || 'N/A';
}

function fetchBirdData() {
    fetch('hk_birds.csv')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(data => {
            csvContent = data; // Store CSV content for DeepSeek queries
            // Parsing CSV data with PapaParse
            Papa.parse(data, {
                header: true,
                skipEmptyLines: true,
                transformHeader: header => header.trim().replace(/^"|"$/g, ''),
                transform: (value, header) => value.trim().replace(/^"|"$/g, ''),
                complete: results => {
                    displayBirdData(results.data);
                    document.getElementById('loading').style.display = 'none';
                },
                error: err => {
                    console.error('Error parsing CSV:', err);
                    document.getElementById('loading').textContent = 'Error parsing bird observations.';
                }
            });
        })
        .catch(err => {
            console.error('Error fetching CSV:', err);
            document.getElementById('loading').textContent = 'Error loading bird observations. Ensure hk_birds.csv is accessible in the same S3 bucket.';
        });
}

// Displaying bird data in the table
function displayBirdData(data) {
    const tableBody = document.getElementById('bird-table-body');
    tableBody.innerHTML = '';

    data.forEach(row => {
        // Skip the remark row
        if (row['Chinese Name'].startsWith('備註:')) return;

        // Using English Name as fallback if Chinese Name is "N/A"
        const chineseName = row['Chinese Name'] === 'N/A' ? row['English Name'] : row['Chinese Name'];

        // Format the date
        const formattedDate = formatDate(row['Date']);

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${chineseName}</td>
            <td>${row['English Name']}</td>
            <td>${row['Description']}</td>
            <td>${row['Location']}</td>
            <td>${formattedDate}</td>
            <td><a href="${row['URL']}" target="_blank">More Info</a></td>
        `;
        tableBody.appendChild(tr);
    });
}

// Handling DeepSeek query submission
function submitDeepSeekQuery() {
    const apiKey = document.getElementById('api-key-input').value.trim();
    const query = document.getElementById('query-input').value.trim();
    const loading = document.getElementById('query-loading');
    const errorDiv = document.getElementById('query-error');
    const resultDiv = document.getElementById('query-result');

    // Reset UI
    errorDiv.textContent = '';
    resultDiv.textContent = '';
    loading.hidden = false;

    // Validate API key
    if (!apiKey || apiKey.length < 10) {
        loading.hidden = true;
        errorDiv.textContent = 'Please enter a valid DeepSeek API key (check length and format).';
        return;
    }

    if (!query) {
        loading.hidden = true;
        errorDiv.textContent = 'Please enter a query.';
        return;
    }

    if (!csvContent) {
        loading.hidden = true;
        errorDiv.textContent = 'CSV data not loaded. Please ensure hk_birds.csv is accessible.';
        return;
    }

    // Prepare the prompt for DeepSeek
    const prompt = `You are an AI assistant with access to a CSV file containing bird observations in Hong Kong. The CSV content is:

${csvContent}

Answer the following query based on the CSV data: ${query}`;

    fetch('https://api.deepseek.com/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
            model: 'deepseek-rag', // Verify with DeepSeek documentation
            messages: [
                { role: 'system', content: 'You are a helpful assistant specialized in analyzing CSV data.' },
                { role: 'user', content: prompt }
            ],
            max_tokens: 500,
            temperature: 0.7
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(`HTTP error! Status: ${response.status}, Details: ${JSON.stringify(errorData)}`);
            });
        }
        return response.json();
    })
    .then(data => {
        loading.hidden = true;
        if (data.choices && data.choices[0] && data.choices[0].message) {
            resultDiv.textContent = data.choices[0].message.content;
        } else {
            errorDiv.textContent = 'Unexpected response format from DeepSeek API.';
        }
    })
    .catch(err => {
        loading.hidden = true;
        errorDiv.textContent = `Error querying DeepSeek: ${err.message}`;
        console.error('DeepSeek API error:', err);
    });
}

// Initializing event listeners
document.addEventListener('DOMContentLoaded', () => {
    fetchBirdData();
    document.getElementById('query-submit').addEventListener('click', submitDeepSeekQuery);
});