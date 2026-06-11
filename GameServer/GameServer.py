import os
import time

while True:
    # Get the script's directory and set it as the working directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    os.system('python3 Launch.py')  # Ensure using Python 3 explicitly
    print("Script terminated. Restarting...")
    time.sleep(5)  # Prevents a tight loop in case of immediate failure