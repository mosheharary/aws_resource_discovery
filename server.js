#!/usr/bin/env node

import express from 'express';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Configure middleware for form handling and static files
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static('public'));

// Store active Python processes for cleanup
const runningProcesses = new Map();

// Serve HTML form interface for AWS discovery configuration
app.get('/', (req, res) => {
    res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Resource To Neo4j Graph DB</title>
    <style>
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8fafc;
            --bg-tertiary: #f1f5f9;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --text-muted: #94a3b8;
            --border-color: #e2e8f0;
            --border-focus: #3b82f6;
            --accent-primary: #3b82f6;
            --accent-hover: #2563eb;
            --accent-disabled: #94a3b8;
            --success-bg: #dcfce7;
            --success-text: #166534;
            --success-border: #bbf7d0;
            --error-bg: #fef2f2;
            --error-text: #dc2626;
            --error-border: #fecaca;
            --info-bg: #eff6ff;
            --info-text: #1d4ed8;
            --info-border: #bfdbfe;
            --output-bg: #0f172a;
            --output-text: #f1f5f9;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }

        [data-theme="dark"] {
            --bg-primary: #1e293b;
            --bg-secondary: #0f172a;
            --bg-tertiary: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --text-muted: #94a3b8;
            --border-color: #475569;
            --border-focus: #60a5fa;
            --accent-primary: #60a5fa;
            --accent-hover: #3b82f6;
            --accent-disabled: #64748b;
            --success-bg: #064e3b;
            --success-text: #6ee7b7;
            --success-border: #047857;
            --error-bg: #7f1d1d;
            --error-text: #fca5a5;
            --error-border: #dc2626;
            --info-bg: #1e3a8a;
            --info-text: #93c5fd;
            --info-border: #2563eb;
            --output-bg: #020617;
            --output-text: #e2e8f0;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            transition: all 0.3s ease;
        }

        .header {
            background: var(--bg-primary);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 0;
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.2rem;
        }

        h1 {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0;
        }

        .theme-toggle {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.5rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            transition: all 0.2s ease;
        }

        .theme-toggle:hover {
            background: var(--bg-tertiary);
            transform: translateY(-1px);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            align-items: start;
        }

        .form-panel {
            background: var(--bg-primary);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--border-color);
        }

        .output-panel {
            background: var(--bg-primary);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--border-color);
            height: 80vh;
            max-height: 800px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .panel-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: var(--text-primary);
            font-size: 0.875rem;
        }

        input[type="text"], input[type="password"], input[type="number"], select, textarea {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 2px solid var(--border-color);
            border-radius: 8px;
            background: var(--bg-secondary);
            color: var(--text-primary);
            font-size: 0.875rem;
            font-family: inherit;
            transition: all 0.2s ease;
        }

        input[type="text"]:focus, input[type="password"]:focus, input[type="number"]:focus, select:focus, textarea:focus {
            border-color: var(--border-focus);
            outline: none;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            background: var(--bg-primary);
        }

        textarea {
            resize: vertical;
            min-height: 120px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.8rem;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: var(--accent-primary);
        }

        .submit-btn {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-hover));
            color: white;
            padding: 0.875rem 1.5rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 600;
            width: 100%;
            margin-top: 1rem;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        .submit-btn:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: var(--shadow-lg);
        }

        .submit-btn:disabled {
            background: var(--accent-disabled);
            cursor: not-allowed;
            transform: none;
        }

        .help-text {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }

        .status {
            margin-bottom: 1.5rem;
            padding: 1rem;
            border-radius: 8px;
            display: none;
            font-weight: 500;
        }

        .status.success {
            background-color: var(--success-bg);
            color: var(--success-text);
            border: 1px solid var(--success-border);
        }

        .status.error {
            background-color: var(--error-bg);
            color: var(--error-text);
            border: 1px solid var(--error-border);
        }

        .status.info {
            background-color: var(--info-bg);
            color: var(--info-text);
            border: 1px solid var(--info-border);
        }

        .output {
            background: var(--output-bg);
            color: var(--output-text);
            padding: 1.5rem;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.8rem;
            flex: 1;
            overflow-y: auto;
            white-space: pre-wrap;
            display: none;
            border: 1px solid var(--border-color);
            margin-top: 1rem;
            min-height: 0;
        }

        .output::-webkit-scrollbar {
            width: 8px;
        }

        .output::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }

        .output::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3);
            border-radius: 4px;
        }

        .output::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.5);
        }

        @media (max-width: 1200px) {
            .container {
                grid-template-columns: 1fr;
                max-width: 800px;
            }
            
            .output-panel {
                height: 60vh;
                max-height: 600px;
            }
        }

        @media (max-width: 768px) {
            .header-content {
                padding: 0 1rem;
            }
            
            .container {
                padding: 0 1rem;
            }
            
            .form-panel, .output-panel {
                padding: 1.5rem;
            }
            
            .output-panel {
                height: 50vh;
                max-height: 400px;
            }
            
            .form-grid {
                grid-template-columns: 1fr;
            }
            
            h1 {
                font-size: 1.25rem;
            }
        }

        .icon {
            width: 20px;
            height: 20px;
            fill: currentColor;
        }

        .fade-in {
            animation: fadeIn 0.3s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon">📊</div>
                <h1>AWS Resource To Neo4j Graph DB</h1>
            </div>
            <button class="theme-toggle" id="themeToggle" type="button" aria-label="Toggle theme">
                <svg class="icon" id="sunIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="5"></circle>
                    <line x1="12" y1="1" x2="12" y2="3"></line>
                    <line x1="12" y1="21" x2="12" y2="23"></line>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                    <line x1="1" y1="12" x2="3" y2="12"></line>
                    <line x1="21" y1="12" x2="23" y2="12"></line>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                </svg>
                <svg class="icon" id="moonIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: none;">
                    <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"></path>
                </svg>
            </button>
        </div>
    </header>

    <div class="container">
        <div class="form-panel">
            <div class="panel-title">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14,2 14,8 20,8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10,9 9,9 8,9"></polyline>
                </svg>
                Configuration
            </div>
            <form id="discoveryForm">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="region">AWS Region *</label>
                        <input type="text" id="region" name="region" placeholder="e.g., us-east-1, eu-west-1" required>
                        <div class="help-text">Enter the AWS region for discovery</div>
                    </div>

                    <div class="form-group">
                        <label for="accountName">Account Name</label>
                        <input type="text" id="accountName" name="accountName" placeholder="e.g., Production-Account">
                        <div class="help-text">Friendly name for this AWS account</div>
                    </div>
                </div>

                <div class="form-group">
                    <label for="awsCredentials">AWS Credentials *</label>
                    <textarea id="awsCredentials" name="awsCredentials" rows="5" placeholder="Paste AWS credentials in either format:

export AWS_ACCESS_KEY_ID=&quot;xxxxxxxxxxxxxxxxxx&quot;
export AWS_SECRET_ACCESS_KEY=&quot;xxxxxxxxxxxxxxxxxx&quot;
export AWS_SESSION_TOKEN=&quot;xxxxxxxxxxxxxxxxxx&quot;

OR

AWS_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxx
AWS_SESSION_TOKEN=xxxxxxxxxxxxxxxxxx" required></textarea>
                    <div class="help-text">Supports both export format and plain key=value format (SESSION_TOKEN is optional)</div>
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <label for="graphDbUrl">Neo4j Database URL *</label>
                        <input type="text" id="graphDbUrl" name="graphDbUrl" placeholder="localhost:7687" required>
                        <div class="help-text">Neo4j database connection URL</div>
                    </div>

                    <div class="form-group">
                        <label for="graphDbPassword">Neo4j Password *</label>
                        <input type="password" id="graphDbPassword" name="graphDbPassword" placeholder="Enter Neo4j password" required>
                        <div class="help-text">Password for Neo4j database</div>
                    </div>
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <label for="maxWorkers">Max Workers</label>
                        <input type="number" id="maxWorkers" name="maxWorkers" placeholder="10" min="1" max="50">
                        <div class="help-text">Number of parallel workers for discovery</div>
                    </div>

                    <div class="form-group">
                        <label for="filter">Service Filter</label>
                        <input type="text" id="filter" name="filter" placeholder="e.g., ec2, s3, lambda">
                        <div class="help-text">Optional: Filter by specific AWS service</div>
                    </div>
                    <div class="form-group">
                        <label for="exclude">Exclude Resource Types</label>
                        <textarea id="exclude" name="exclude" rows="3" placeholder="AWS::S3::Bucket, AWS::EC2::Instance, AWS::IAM::User, AWS::Lambda::Version"></textarea>
                        <div class="help-text">Optional: Comma-separated list of AWS resource types to exclude from discovery. Useful for skipping resource types that aren't needed or take too long to scan.</div>
                    </div>
                </div>

                <div class="form-grid">
                    <div class="form-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="resetGraph" name="resetGraph">
                            <label for="resetGraph">Reset Graph Database</label>
                        </div>
                        <div class="help-text">Clear existing data before discovery</div>
                    </div>

                    <div class="form-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="individualDescriptions" name="individualDescriptions">
                            <label for="individualDescriptions">Generate Individual Descriptions</label>
                        </div>
                        <div class="help-text">Create detailed description files for each resource</div>
                    </div>
                </div>

                <div class="form-group">
                    <button type="button" class="submit-btn" id="testNeo4jBtn" style="background: linear-gradient(135deg, #10b981, #059669); margin-bottom: 1rem;">
                        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"></path>
                            <polyline points="22,4 12,14.01 9,11.01"></polyline>
                        </svg>
                        Test Neo4j Connection
                    </button>
                </div>

                <button type="submit" class="submit-btn" id="submitBtn">
                    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M12 1v6m0 6v6"></path>
                        <path d="M1 12h6m6 0h6"></path>
                    </svg>
                    Start AWS Discovery
                </button>
            </form>
        </div>

        <div class="output-panel">
            <div class="panel-title">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14,2 14,8 20,8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10,9 9,9 8,9"></polyline>
                </svg>
                Discovery Output
            </div>
            <div id="status" class="status"></div>
            <div id="output" class="output"></div>
        </div>
    </div>

    <script>
        // Theme management
        const themeToggle = document.getElementById('themeToggle');
        const sunIcon = document.getElementById('sunIcon');
        const moonIcon = document.getElementById('moonIcon');
        
        // Initialize theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeIcons(savedTheme);
        
        function updateThemeIcons(theme) {
            if (theme === 'dark') {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            } else {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            }
        }
        
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcons(newTheme);
        });

        // Form elements
        const form = document.getElementById('discoveryForm');
        const submitBtn = document.getElementById('submitBtn');
        const status = document.getElementById('status');
        const output = document.getElementById('output');

        // Display status messages with styling
        function showStatus(message, type = 'info') {
            status.innerHTML = \`<div class="fade-in">\${message}</div>\`;
            status.className = \`status \${type}\`;
            status.style.display = 'block';
        }

        // Append text to output console
        function appendOutput(text) {
            output.textContent += text;
            output.style.display = 'block';
            output.scrollTop = output.scrollHeight;
        }

        // Test Neo4j connectivity
        document.getElementById('testNeo4jBtn').addEventListener('click', async () => {
            const testBtn = document.getElementById('testNeo4jBtn');
            const graphDbUrl = document.getElementById('graphDbUrl').value;
            const graphDbPassword = document.getElementById('graphDbPassword').value;
            
            if (!graphDbUrl || !graphDbPassword) {
                showStatus('❌ Please enter Neo4j URL and password first', 'error');
                return;
            }
            
            testBtn.disabled = true;
            testBtn.textContent = '⏳ Testing Connection...';
            
            try {
                const response = await fetch('/test-neo4j', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        graphDbUrl,
                        graphDbPassword
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showStatus(\`✅ Neo4j connection successful! \${result.message}\`, 'success');
                } else {
                    showStatus(\`❌ Neo4j connection failed: \${result.error}\`, 'error');
                }
                
            } catch (error) {
                showStatus(\`❌ Connection test failed: \${error.message}\`, 'error');
            } finally {
                testBtn.disabled = false;
                testBtn.textContent = '🔗 Test Neo4j Connection';
            }
        });

        // Handle form submission and start discovery process
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Running Discovery...';
            output.textContent = '';
            output.style.display = 'block';
            
            showStatus('Starting AWS discovery...', 'info');

            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            
            // Convert checkbox values to boolean
            data.resetGraph = form.resetGraph.checked;
            data.individualDescriptions = form.individualDescriptions.checked;

            try {
                const response = await fetch('/run-discovery', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });

                if (!response.ok) {
                    throw new Error(\`HTTP error! status: \${response.status}\`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                // Stream response data to output
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const text = decoder.decode(value);
                    appendOutput(text);
                }

                showStatus('✅ AWS discovery completed successfully!', 'success');
                
            } catch (error) {
                showStatus(\`❌ Error: \${error.message}\`, 'error');
                appendOutput(\`\\nError: \${error.message}\\n\`);
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 Start AWS Discovery';
            }
        });
    </script>
</body>
</html>
    `);
});

// Execute AWS discovery Python script with provided parameters
app.post('/run-discovery', (req, res) => {
    const {
        region,
        awsCredentials,
        accountName,
        graphDbUrl,
        graphDbPassword,
        maxWorkers,
        filter,
        exclude,
        resetGraph,
        individualDescriptions
    } = req.body;

    // Parse AWS credentials from export command format or plain key=value format
    function parseAwsExports(exportText) {
        const lines = exportText.split('\n').map(line => line.trim()).filter(line => line);
        const credentials = {};
        
        for (const line of lines) {
            // Extract AWS variables from export commands: export AWS_KEY="value"
            let match = line.match(/export\s+(AWS_[A-Z_]+)=["']?([^"'\s]+)["']?/);
            if (match) {
                const [, key, value] = match;
                credentials[key] = value;
                continue;
            }
            
            // Extract AWS variables from plain format: AWS_KEY=value
            match = line.match(/^(AWS_[A-Z_]+)=["']?([^"'\s]+)["']?$/);
            if (match) {
                const [, key, value] = match;
                credentials[key] = value;
                continue;
            }
        }
        
        return credentials;
    }

    const parsedCredentials = parseAwsExports(awsCredentials);
    
    // Validate required AWS credentials
    if (!parsedCredentials.AWS_ACCESS_KEY_ID || !parsedCredentials.AWS_SECRET_ACCESS_KEY) {
        return res.status(400).json({ 
            error: 'Missing required AWS credentials. Please provide AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY' 
        });
    }

    // Set up environment variables for Python process
    const env = {
        ...process.env,
        AWS_ACCESS_KEY_ID: parsedCredentials.AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY: parsedCredentials.AWS_SECRET_ACCESS_KEY
    };

    if (parsedCredentials.AWS_SESSION_TOKEN) {
        env.AWS_SESSION_TOKEN = parsedCredentials.AWS_SESSION_TOKEN;
    }

    // Build command arguments for Python script
    const args = [
        'main.py',
        '--region', region,
        '--update-graph',
        '--graph-db-url', graphDbUrl,
        '--graph-db-password', graphDbPassword,
        '--account-name', accountName || `Account-${Date.now()}`,
        '--max-workers', (maxWorkers || 10).toString(),
        '--log-level', 'INFO',
        '--console-log-level', 'INFO'
    ];

    if (resetGraph) {
        args.push('--reset-graph');
    }

    if (individualDescriptions) {
        args.push('--individual-descriptions');
    }

    if (filter && filter.trim()) {
        args.push('--filter', filter.trim());
    }

    if (exclude && exclude.trim()) {
        // Parse comma-separated resource types and add them as individual arguments
        // Expected format: AWS::ServiceName::ResourceType (e.g., AWS::S3::Bucket)
        const excludeTypes = exclude.split(',')
            .map(type => type.trim())
            .filter(type => type.length > 0 && type.includes('AWS::'));
        
        if (excludeTypes.length > 0) {
            args.push('--exclude', ...excludeTypes);
        }
    }

    // Configure response for streaming output
    res.setHeader('Content-Type', 'text/plain');
    res.setHeader('Transfer-Encoding', 'chunked');

    // Spawn Python discovery process
    const pythonProcess = spawn('python', args, {
        env: env,
        stdio: ['pipe', 'pipe', 'pipe']
    });

    // Stream stdout to client
    pythonProcess.stdout.on('data', (data) => {
        res.write(data);
    });

    // Stream stderr to client
    pythonProcess.stderr.on('data', (data) => {
        res.write(`ERROR: ${data}`);
    });

    // Handle process completion
    pythonProcess.on('close', (code) => {
        if (code === 0) {
            res.write('\\n✅ AWS discovery completed successfully!\\n');
        } else {
            res.write(`\\n❌ Process exited with code ${code}\\n`);
        }
        res.end();
    });

    // Handle process startup errors
    pythonProcess.on('error', (error) => {
        res.write(`\\n❌ Failed to start Python script: ${error.message}\\n`);
        res.end();
    });

    // Track process for potential cleanup
    const processId = Date.now().toString();
    runningProcesses.set(processId, pythonProcess);

    // Clean up process tracking when done
    pythonProcess.on('close', () => {
        runningProcesses.delete(processId);
    });
});

// Test Neo4j connectivity endpoint
app.post('/test-neo4j', async (req, res) => {
    const { graphDbUrl, graphDbPassword } = req.body;
    
    if (!graphDbUrl || !graphDbPassword) {
        return res.json({
            success: false,
            error: 'Missing Neo4j URL or password'
        });
    }
    
    try {
        // Import neo4j driver dynamically
        const neo4j = await import('neo4j-driver');
        
        // Create driver with proper URI format
        const uri = graphDbUrl.startsWith('bolt://') ? graphDbUrl : `bolt://${graphDbUrl}`;
        const driver = neo4j.default.driver(uri, neo4j.default.auth.basic('neo4j', graphDbPassword));
        
        // Test connection with a simple query
        const session = driver.session();
        
        try {
            const result = await session.run('RETURN "Connection successful!" as message, datetime() as timestamp');
            const record = result.records[0];
            const message = record.get('message');
            const timestamp = record.get('timestamp').toString();
            
            await session.close();
            await driver.close();
            
            res.json({
                success: true,
                message: `${message} (${timestamp})`
            });
            
        } catch (queryError) {
            await session.close();
            await driver.close();
            
            res.json({
                success: false,
                error: `Query failed: ${queryError.message}`
            });
        }
        
    } catch (error) {
        res.json({
            success: false,
            error: `Connection failed: ${error.message}`
        });
    }
});

// Health check endpoint for monitoring
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        runningProcesses: runningProcesses.size,
        timestamp: new Date().toISOString()
    });
});

// Start Express server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🌐 AWS Discovery Runner server running on http://0.0.0.0:${PORT}`);
    console.log(`📋 Open your browser and navigate to http://localhost:${PORT}`);
});

export default app;
