import os
import subprocess
import sys
import time
import webbrowser
import asyncio
import websockets
import json

# 1. Define your paths and configuration
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_SCRIPT = os.path.abspath(__file__)
FRONTEND_FILE = "Trade Bot Tester.html"

# List the core packages your trading bot relies on
REQUIRED_PACKAGES = {
    "flask": "flask",
    "flask-socketio": "flask_socketio",
    "websockets": "websockets",
    "pandas": "pandas",
    "numpy": "numpy",
    "alpaca-py": "alpaca",
    "python-dotenv": "dotenv"
}

def check_and_install_dependencies():
    """Silently checks and installs any missing python libraries."""
    print("[-] Checking system dependencies...")
    for package, module in REQUIRED_PACKAGES.items():
        try:
            __import__(module)
        except ImportError:
            print(f"[!] Missing {package}. Installing now...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    print("[+] All dependencies verified.")

async def start_dealer_server():
    """Starts the WebSocket server that the trading bots connect to."""
    async def handler(websocket):
        print("[+] New client connected to Arena Dealer.")
        try:
            # Send a handshake message to the bot
            await websocket.send(json.dumps({"type": "MARKET_STATUS", "status": "CONNECTED_TO_ARENA"}))
            async for message in websocket:
                # This is where you'll eventually process orders or logs from the bot
                pass
        except websockets.ConnectionClosed:
            print("[-] Client disconnected from Dealer.")

    async with websockets.serve(handler, "127.0.0.1", 8765):
        await asyncio.Future()  # run forever

def launch_system():
    # Prevent infinite recursion if this script is named "Trade Bot Tester.py"
    if "--backend" in sys.argv:
        print("[+] Backend Server Mode Active. Starting Dealer on port 8765...")
        try:
            asyncio.run(start_dealer_server())
        except KeyboardInterrupt:
            pass
        return

    # Ensure we are working out of the correct repository directory
    if os.path.exists(REPO_DIR):
        os.chdir(REPO_DIR)
    else:
        print(f"[X] Error: Could not find directory {REPO_DIR}")
        return

    # Run dependency check
    check_and_install_dependencies()

    # 2. Start the Backend Server
    print(f"[-] Launching backend server ({BACKEND_SCRIPT})...")
    # Using subprocess.Popen allows the backend to run continuously in the background
    backend_process = subprocess.Popen(
        [sys.executable, BACKEND_SCRIPT, "--backend"],
        stdout=None,  # Keeps logs visible in this terminal window
        stderr=None
    )

    # Give the backend server a moment (2 seconds) to bind to its port before launching UI
    time.sleep(2)

    # 3. Launch the Frontend UI automatically
    frontend_path = os.path.join(REPO_DIR, FRONTEND_FILE)
    print(f"[-] Opening user interface: {FRONTEND_FILE}")
    webbrowser.open(f"file:///{frontend_path}")

    print("\n[+] System successfully automated and running!")
    print("[*] Keep this terminal open while testing. Press Ctrl+C here to shut down.")
    
    try:
        # Keep the main script alive so the background server doesn't close immediately
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n[-] Shutting down trading environment...")
        backend_process.terminate()

if __name__ == "__main__":
    launch_system()