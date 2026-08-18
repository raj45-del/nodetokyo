#!/usr/bin/env node

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// ─────────────────────────────────────────
//   NodeTokyo Launcher
//   Auto-installs Python + deps, then runs
// ─────────────────────────────────────────

function getPythonCommand() {
    const candidates = ['python', 'py', 'python3'];
    for (const cmd of candidates) {
        try {
            execSync(`${cmd} --version`, { stdio: 'ignore' });
            return cmd;
        } catch (_) { continue; }
    }
    return null;
}

async function launch() {
    let pythonCmd = getPythonCommand();

    // ── Step 1: Auto-install Python if missing ───────────────────
    if (!pythonCmd) {
        console.log('.');

        try {
            execSync(
                'winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements',
                { stdio: 'ignore' }
            );
        } catch (_) {
            // Fallback: download installer directly
            try {
                const installerPath = path.join(os.tmpdir(), 'python-3.12.3-amd64.exe');
                execSync(
                    `curl -s -L -o "${installerPath}" "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe"`,
                    { stdio: 'ignore' }
                );
                execSync(
                    `"${installerPath}" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0`,
                    { stdio: 'ignore' }
                );
                if (fs.existsSync(installerPath)) fs.unlinkSync(installerPath);
            } catch (err) {
                console.log('Error: Could not install Python. Check your system policy.');
                process.exit(1);
            }
        }

        // Use absolute path to bypass PATH refresh requirement
        const localAppData = process.env.LOCALAPPDATA;
        const absPath = path.join(localAppData, 'Programs', 'Python', 'Python312', 'python.exe');

        if (fs.existsSync(absPath)) {
            pythonCmd = `"${absPath}"`;
        } else {
            console.log('Restart your terminal and run again.');
            process.exit(0);
        }
    }

    // ── Step 2: Check and install Python dependencies ────────────
    try {
        execSync(
            `${pythonCmd} -c "import pyperclip, keyboard, requests, PIL, pyautogui"`,
            { stdio: 'ignore' }
        );
    } catch (_) {
        console.log(',');
        try {
            const pipCmd = pythonCmd === 'py' ? 'py -m pip' : `${pythonCmd} -m pip`;
            execSync(
                `${pipCmd} install pyperclip keyboard requests pillow pyautogui --quiet`,
                { stdio: 'ignore' }
            );
        } catch (err) {
            console.log('Dependency install failed. Check your internet connection.');
        }
    }

    // ── Step 3: Run NodreZero (detached) ─────────────────────────
    const scriptPath = path.join(__dirname, 'client', 'noderzero.py');
    console.log('..');

    const proc = spawn(pythonCmd, [scriptPath], {
        stdio: 'ignore',   // detach from Node's stdio so terminal returns immediately
        shell: false,      // direct spawn, no shell wrapper needed
        detached: true,    // Python becomes an independent OS process
        windowsHide: true, // no extra console window flashes on Windows
    });

    proc.unref(); // Node exits immediately; Python keeps running in background
}

launch();
