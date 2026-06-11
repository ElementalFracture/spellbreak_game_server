# Final Robust Launch.py - Unified Logic & Match Tracker
import os, time, socket, logging, subprocess, configparser, threading, signal, sys, json, psutil
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# 1. Load Configuration
config_path = "config.ini"
if not os.path.exists(config_path):
    print(f"CRITICAL ERROR: {config_path} not found.", flush=True); os._exit(1)

config = configparser.ConfigParser()
config.read(config_path)

try:
    gameMode = config.get('GameSettings', 'GameMode')
    gamePort = config.get('GameSettings', 'gameport')
    serverName = config.get('GameSettings', 'servername')
    serverLogDir = os.path.join(config.get('GameSettings', 'logdirectory'), serverName)
    gamePathDir = config.get('GameSettings', 'GamePathDirectory')
    elixirPort = config.getint('ServerSettings', 'elixirPort')
    elixirHost = config.get('ServerSettings', 'elixirHost')
    broadcastPort = config.getint('MatchTracker', 'broadcastport')
    trackerFreq = config.getint('MatchTracker', 'frequency')
except Exception as e:
    print(f"CRITICAL ERROR: Config read failed: {e}", flush=True); os._exit(1)

# Global State for Match Tracker
last_player_data = '{"state": "WaitingForPlayers", "players": []}'
data_lock = threading.Lock()

# 2. Match Tracker Logic
def query_tracker():
    """Queries the DLL on port 4951 for player data."""
    global last_player_data
    while True:
        time.sleep(trackerFreq)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2); s.connect(("localhost", 4951))
                s.sendall(b'get_players'); s.shutdown(socket.SHUT_WR)
                data = b""
                while True:
                    chunk = s.recv(1024)
                    if not chunk: break
                    data += chunk
                if data:
                    new_data = data.decode('utf-8')
                    json.loads(new_data) # Validate
                    with data_lock: last_player_data = new_data
        except: pass # Game server might not be ready yet

def broadcast_data():
    """Broadcasts player data to the Discord Bot."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', broadcastPort)); s.listen(5)
        log(f"Tracker: Broadcasting on port {broadcastPort}")
        while True:
            conn, _ = s.accept()
            threading.Thread(target=handle_broadcast, args=(conn,), daemon=True).start()

def handle_broadcast(conn):
    try:
        while True:
            with data_lock: msg = last_player_data
            conn.sendall((msg + '\n').encode('utf-8'))
            time.sleep(1)
    except: conn.close()

# 3. Cleanup Logic
def trigger_elixir_cleanup():
    log(f"Notifying Elixir at {elixirHost}:{elixirPort}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5); s.connect((elixirHost, elixirPort))
            s.sendall(b"CMD_REFRESH"); log(">>> Success: Sent CMD_REFRESH.")
    except Exception as e: log(f"ERROR: Elixir unreachable: {e}")

def monitor_logs():
    log_file = os.path.join(serverLogDir, "g3.log")
    while not os.path.exists(log_file): time.sleep(2)
    log("Monitor: Log detected. Following stream...")
    with open(log_file, 'r') as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line: time.sleep(1); continue
            if "R:GameServer: The match was complete" in line:
                log("Match completion detected. Triggering Elixir..."); trigger_elixir_cleanup(); break

def listen_for_commands():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', elixirPort)); s.listen(1)
        while True:
            conn, _ = s.accept()
            if conn.recv(16).decode('utf-8') == "CMD_REFRESH":
                log("Manager: Shutdown signal confirmed."); break
    os.kill(os.getpid(), signal.SIGKILL)

# 4. Main
if __name__ == "__main__":
    log(f"--- Starting {serverName} Launcher ---")
    threading.Thread(target=monitor_logs, daemon=True).start()
    threading.Thread(target=listen_for_commands, daemon=True).start()
    threading.Thread(target=query_tracker, daemon=True).start()
    threading.Thread(target=broadcast_data, daemon=True).start()

    log_file = os.path.join(serverLogDir, "g3.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    game_exec = os.path.join(gamePathDir, "g3", "Binaries", "Win64", "g3Server-Win64-Test.exe")
    env = os.environ.copy(); env["WINEDLLOVERRIDES"] = "match_tracker.dll=n,b"
    
    with open(log_file, 'a') as f:
        try:
            proc = subprocess.Popen(["wine", game_exec, f"Alpha_Resculpt?game={gameMode}", f"-port={gamePort}", f"-LOG={log_file}"], 
                                    cwd=os.path.dirname(game_exec), env=env, stdout=f, stderr=f)
            log(f"Game process started (PID: {proc.pid})"); proc.wait()
        except Exception as e: log(f"LAUNCH ERROR: {e}")
    # If we get here, the match is over or a refresh was requested
    log("Main process shutting down. Entering 60s cooldown for port release...")
    time.sleep(60)
    os._exit(0)
