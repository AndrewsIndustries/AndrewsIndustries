import subprocess
import time
import sys
import os

def run_automation():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_stocks.py")
    print(f"[*] Starting Stock Watch Automation Loop")
    print(f"[*] Target: {script_path}")
    print("[*] Interval: 300 seconds (5 minutes)")
    print("[*] Press Ctrl+C to stop the automation.")

    while True:
        try:
            print(f"\n[{time.strftime('%H:%M:%S')}] Executing sync...")
            # Uses the same Python interpreter currently running this script
            subprocess.run([sys.executable, script_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[!] Sync failed: {e}")
        except KeyboardInterrupt:
            print("\n[-] Automation stopped.")
            break
        
        time.sleep(300) # Wait 5 minutes

if __name__ == "__main__":
    run_automation()