import subprocess
import time
import sys
import os

def run_automation():
    # List of all scripts we want to automate on a 5-minute cycle
    scripts = ["sync_stocks.py", "sync_X_news.py", "sync_digital_downloads.py"]
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"[*] Andrews Industries Master Sync initialized.")
    print(f"[*] Managing: {', '.join(scripts)}")
    print(f"[*] Frequency: Every 300 seconds (5 minutes)")
    print("[*] Press Ctrl+C to stop the automation.\n")

    while True:
        current_time = time.strftime('%H:%M:%S')
        print(f"--- Global Sync Cycle Started: {current_time} ---")
        
        for script in scripts:
            script_path = os.path.join(base_dir, script)
            print(f"[>] Syncing {script}...", end=" ", flush=True)
            try:
                # Runs the script and waits for it to finish
                subprocess.run([sys.executable, script_path], check=True, capture_output=True)
                print("SUCCESS")
            except Exception as e:
                print(f"FAILED\n[!] Error: {e}")
        
        print(f"--- Cycle Complete. Waiting 5 minutes. ---\n")
        time.sleep(300)

if __name__ == "__main__":
    run_automation()