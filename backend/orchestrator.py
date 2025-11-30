import subprocess
import time
import sys
import os
import signal

# Define the scripts to run
SCRIPTS = {
    "producers": "producers.py",
    "consumer": "consumer.py",
    "api": "api.py"
}

processes = {}

def start_process(name, script_name):
    """Starts a process and stores the handle."""
    # Using sys.executable ensures we use the same python interpreter
    cmd = [sys.executable, script_name]
    print(f"Starting {name}...")
    
    # Open log file
    log_path = os.path.join("logs", f"{name}.log")
    # We open in append mode so we don't lose history on restart
    log_file = open(log_path, "a")
    
    # Start the process
    # start_new_session=True ensures the child process is in a new session
    # and does not receive signals from the controlling terminal (like Ctrl+C).
    # The orchestrator will manage sending signals to it.
    # We redirect stdout and stderr to the log file to keep the orchestrator output clean.
    p = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True)
    processes[name] = (p, log_file)
    return p

def main():
    # Ensure we are in the correct directory
    # This script is in backend/, and assumes other scripts are in the same dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Initial start
    for name, script in SCRIPTS.items():
        start_process(name, script)

    print("Orchestrator running. Press Ctrl+C to exit.")
    print("Logs are being written to backend/logs/")

    try:
        while True:
            time.sleep(2)
            
            for name, script in SCRIPTS.items():
                p_info = processes.get(name)
                if p_info:
                    p, log_file = p_info
                    
                    # Check if process has exited
                    if p.poll() is not None:
                        print(f"SERVICE {name.upper()} DIED. RESTARTING...")
                        # Close old log file handle
                        try:
                            log_file.close()
                        except:
                            pass
                        # Restart the process
                        start_process(name, script)
                
    except KeyboardInterrupt:
        print("\nStopping orchestrator...")
        # Terminate all processes on exit
        for name, p_info in processes.items():
            p, log_file = p_info
            if p.poll() is None:
                print(f"Terminating {name}...")
                # Send SIGINT to allow graceful shutdown (e.g. producers cleaning up children)
                p.send_signal(signal.SIGINT)
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"Force killing {name}...")
                    p.kill()
            
            # Close log file
            try:
                log_file.close()
            except:
                pass
        print("All services stopped.")

if __name__ == "__main__":
    main()
