#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Path to the Python orchestrator relative to this script
const pythonScriptPath = path.join(__dirname, '..', 'aegis_scanner.py');

const fs = require('fs');

// Find the python executable
function getPythonCommand() {
    const cwd = process.cwd();
    const isWindows = process.platform === 'win32';
    
    // Check common virtual environment locations relative to process.cwd()
    const venvPaths = ['.venv', 'venv', 'env'];
    for (const venv of venvPaths) {
        const localPy = isWindows 
            ? path.join(cwd, venv, 'Scripts', 'python.exe')
            : path.join(cwd, venv, 'bin', 'python');
            
        if (fs.existsSync(localPy)) {
            return localPy;
        }
    }

    // Try standard python or python3 based on OS
    const commands = process.platform === 'win32' ? ['python', 'python3'] : ['python3', 'python'];
    for (const cmd of commands) {
        try {
            // execSync will throw if the command fails/is not found
            require('child_process').execSync(`${cmd} --version`, { stdio: 'ignore' });
            return cmd;
        } catch (e) {
            // ignore and try next
        }
    }
    return null;
}

const pythonCmd = getPythonCommand();
if (!pythonCmd) {
    console.error('\x1b[31mError: Aegis-Scanner requires Python 3 to be installed on your system.\x1b[0m');
    console.error('Please install Python 3 (https://www.python.org/downloads/) and try again.');
    process.exit(1);
}

// Forward all command line arguments
const args = [pythonScriptPath, ...process.argv.slice(2)];

// Run the python script
const child = spawn(pythonCmd, args, {
    stdio: 'inherit',
    env: process.env
});

child.on('close', (code) => {
    process.exit(code);
});
