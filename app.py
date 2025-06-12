from flask import Flask, request, render_template_string, redirect
import threading, time, requests, pytz
from datetime import datetime
import uuid
import os
import json

app = Flask(__name__)

# Generate a secret key for session management
app.secret_key = os.urandom(24)

# Storage for tasks and logs
stop_events = {}
task_logs = {}

# Basic authentication credentials (change these!)
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "password123"

def add_log(task_id, log_message):
    if task_id not in task_logs:
        task_logs[task_id] = []
    task_logs[task_id].append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {log_message}")

def check_auth(username, password):
    """This function is called to check if a username/password combination is valid."""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return (
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    """Decorator to require authentication for routes"""
    from functools import wraps
    
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>C3C MESSAGE SENDER</title>
    <style>
        body {
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: 'Roboto', sans-serif;
        }
        h1 {
            color: #00ff00;
            text-align: center;
        }
        .content {
            max-width: 900px;
            margin: auto;
            padding: 40px;
            background-color: #292929;
            border-radius: 10px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        .form-label {
            color: #00ff00;
            display: block;
            margin-bottom: 8px;
        }
        .form-control {
            width: 100%;
            padding: 10px;
            background-color: #333;
            color: white;
            border: 1px solid #444;
            border-radius: 6px;
        }
        .btn {
            width: 100%;
            padding: 12px;
            margin-top: 10px;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:hover {
            opacity: 0.9;
            transform: scale(1.01);
        }
        .btn-primary {
            background-color: #FFA500;
            color: white;
        }
        .btn-secondary {
            background-color: #FFA500;
            color: white;
        }
        .btn-danger {
            background-color: #ff3333;
            color: white;
        }
        .log-entry {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            background-color: #333;
        }
        .success {
            color: #00cc66;
        }
        .error {
            color: #ff3333;
        }
    </style>
</head>
<body>
    <h1>C3C MESSAGE SENDER</h1>
    <div class="content">
        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label class="form-label">Cookies File (JSON format):</label>
                <input type="file" name="cookiesFile" class="form-control" required>
            </div>
            <div class="form-group">
                <label class="form-label">Conversation ID:</label>
                <input type="text" name="convo" class="form-control" required>
            </div>
            <div class="form-group">
                <label class="form-label">Message File:</label>
                <input type="file" name="msgFile" class="form-control" required>
            </div>
            <div class="form-group">
                <label class="form-label">Interval (sec):</label>
                <input type="number" name="interval" class="form-control" required>
            </div>
            <div class="form-group">
                <label class="form-label">Sender Name:</label>
                <input type="text" name="senderName" class="form-control" required>
            </div>
            <button class="btn btn-primary" type="submit">Start</button>
        </form>

        <form method="POST" action="/stop">
            <div class="form-group">
                <label class="form-label">Task ID to Stop:</label>
                <input type="text" name="task_id" class="form-control" required>
            </div>
            <button class="btn btn-danger" type="submit">Stop Task</button>
        </form>

        <form method="POST" action="/check-cookies">
            <div class="form-group">
                <label class="form-label">Check Cookies:</label>
                <input type="file" name="cookiesFile" class="form-control" required>
            </div>
            <button class="btn btn-primary" type="submit">Check Cookies</button>
        </form>

        <form method="POST" action="/view-logs">
            <div class="form-group">
                <label class="form-label">View Logs by Task ID:</label>
                <input type="text" name="task_id" class="form-control" required>
            </div>
            <button class="btn btn-secondary" type="submit">View Logs</button>
        </form>
    </div>
</body>
</html>
"""

LOG_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Task Logs</title>
    <style>
        body { background-color: #1e1e1e; color: #e0e0e0; font-family: 'Roboto', sans-serif; padding: 20px; }
        h1 { color: #00ff00; }
        .log-entry { margin: 10px 0; padding: 10px; border-radius: 5px; background-color: #292929; }
        .success { color: #00cc66; }
        .error { color: #ff3333; }
        .info { color: #66b3ff; }
    </style>
    <script>
        function refreshLogs() {
            fetch(window.location.href)
                .then(response => response.text())
                .then(data => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(data, 'text/html');
                    const newLogs = doc.getElementById('logs').innerHTML;
                    document.getElementById('logs').innerHTML = newLogs;
                });
        }
        
        // Refresh every 3 seconds
        setInterval(refreshLogs, 3000);
    </script>
</head>
<body>
    <h1>Logs for Task ID: {{ task_id }}</h1>
    <div id="logs">
        {% for log in logs %}
        <div class="log-entry {% if '✅' in log %}success{% elif '❌' in log %}error{% elif 'ℹ️' in log %}info{% endif %}">{{ log }}</div>
        {% endfor %}
    </div>
    <script>
        // Scroll to bottom on load
        window.onload = function() {
            window.scrollTo(0, document.body.scrollHeight);
        };
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
@requires_auth
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/", methods=["POST"])
@requires_auth
def handle_form():
    try:
        # Get form data
        convo = request.form["convo"]
        interval = int(request.form["interval"])
        sender_name = request.form["senderName"]
        
        # Process cookies file
        if 'cookiesFile' not in request.files:
            return "❌ Cookies file is required", 400
            
        cookies_file = request.files["cookiesFile"]
        if cookies_file.filename == '':
            return "❌ No selected cookies file", 400
            
        try:
            cookies_data = json.loads(cookies_file.read().decode())
            if not isinstance(cookies_data, list):
                return "❌ Invalid cookies format - should be a JSON array", 400
        except json.JSONDecodeError:
            return "❌ Invalid JSON format in cookies file", 400
            
        # Process message file
        if 'msgFile' not in request.files:
            return "❌ Message file is required", 400
            
        msg_file = request.files["msgFile"]
        if msg_file.filename == '':
            return "❌ No selected message file", 400
            
        msgs = [msg.strip() for msg in msg_file.read().decode().splitlines() if msg.strip()]

        # Create task
        task_id = str(uuid.uuid4())
        stop_events[task_id] = threading.Event()
        threading.Thread(
            target=start_messaging, 
            args=(cookies_data, msgs, convo, interval, sender_name, task_id),
            daemon=True
        ).start()
        
        add_log(task_id, f"Task created with ID: {task_id}")
        return f"📨 Messaging started for conversation {convo}. Task ID: {task_id}"
        
    except Exception as e:
        return f"❌ Error processing request: {str(e)}", 500

@app.route("/stop", methods=["POST"])
@requires_auth
def stop_task():
    task_id = request.form["task_id"]
    if task_id in stop_events:
        stop_events[task_id].set()
        add_log(task_id, "🛑 Stop request received")
        return f"🛑 Task with ID {task_id} has been stopped."
    else:
        return f"⚠️ No active task with ID {task_id}."

@app.route("/check-cookies", methods=["POST"])
@requires_auth
def check_cookies():
    try:
        if 'cookiesFile' not in request.files:
            return "❌ Cookies file is required", 400
            
        cookies_file = request.files["cookiesFile"]
        if cookies_file.filename == '':
            return "❌ No selected cookies file", 400
            
        try:
            cookies_data = json.loads(cookies_file.read().decode())
            if not isinstance(cookies_data, list):
                return "❌ Invalid cookies format - should be a JSON array", 400
        except json.JSONDecodeError:
            return "❌ Invalid JSON format in cookies file", 400
            
        # Test cookies by fetching user info
        session = requests.Session()
        
        # Convert cookies list to dict and add to session
        cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_data if 'name' in cookie and 'value' in cookie}
        session.cookies.update(cookies_dict)
        
        # Make request to Facebook to check cookies
        try:
            response = session.get("https://www.facebook.com/api/graphql/", params={
                "variables": json.dumps({
                    "fetchViewer": True
                }),
                "doc_id": "6627634225271924"  # This is a common GraphQL doc ID for user info
            })
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'data' in data and 'viewer' in data['data']:
                        user_id = data['data']['viewer'].get('actor_id', 'N/A')
                        name = data['data']['viewer'].get('name', 'Unknown')
                        return f"✅ Valid Cookies<br>👤 Name: {name}<br>🆔 UID: {user_id}"
                    return "❌ Could not fetch user info (invalid cookies?)"
                except ValueError:
                    return "❌ Invalid response from Facebook (cookies may be expired)"
            return f"❌ Facebook returned status {response.status_code} (cookies may be invalid)"
            
        except requests.RequestException as e:
            return f"❌ Error checking cookies: {str(e)}"
            
    except Exception as e:
        return f"❌ Error processing request: {str(e)}", 500

@app.route("/view-logs", methods=["GET", "POST"])
@requires_auth
def view_logs():
    if request.method == "POST":
        task_id = request.form["task_id"]
        return redirect(f"/view-logs/{task_id}")
    return render_template_string("""
        <form method="POST" style="max-width: 500px; margin: 20px auto;">
            <input type="text" name="task_id" class="form-control" placeholder="Enter Task ID" required>
            <button class="btn btn-secondary" type="submit" style="margin-top: 10px;">View Logs</button>
        </form>
    """)

@app.route("/view-logs/<task_id>")
@requires_auth
def show_logs(task_id):
    logs = task_logs.get(task_id, ["No logs found for this task."])
    return render_template_string(LOG_TEMPLATE, task_id=task_id, logs=logs)

def start_messaging(cookies_list, messages, convo_id, interval, sender_name, task_id):
    try:
        stop_event = stop_events[task_id]
        add_log(task_id, f"🚀 Task started for conversation: {convo_id}")
        
        # Create session with cookies
        session = requests.Session()
        cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_list if 'name' in cookie and 'value' in cookie}
        session.cookies.update(cookies_dict)
        
        # Get user info to verify cookies
        try:
            user_info = get_user_info(session)
            if user_info:
                add_log(task_id, f"ℹ️ Logged in as: {user_info.get('name')} (ID: {user_info.get('id')})")
        except Exception as e:
            add_log(task_id, f"⚠️ Could not verify user info: {str(e)}")
        
        # Get group info
        group_info = get_group_info(session, convo_id)
        if group_info:
            add_log(task_id, f"ℹ️ Target conversation: {group_info.get('name', 'Unknown')}")
        
        # Main messaging loop
        while not stop_event.is_set() and messages:
            for msg in messages:
                if stop_event.is_set():
                    add_log(task_id, "🛑 Task stopped manually.")
                    break
                    
                if not msg.strip():
                    continue
                    
                send_message(session, convo_id, f"{sender_name}: {msg}", task_id)
                time.sleep(interval)
                
    except Exception as e:
        add_log(task_id, f"❌ Critical error in messaging task: {str(e)}")
    finally:
        add_log(task_id, "🏁 Task finished")

def get_user_info(session):
    try:
        response = session.get("https://www.facebook.com/api/graphql/", params={
            "variables": json.dumps({
                "fetchViewer": True
            }),
            "doc_id": "6627634225271924"
        })
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'viewer' in data['data']:
                return {
                    'id': data['data']['viewer'].get('actor_id'),
                    'name': data['data']['viewer'].get('name')
                }
    except:
        pass
    return None

def get_group_info(session, convo_id):
    try:
        response = session.get(f"https://www.facebook.com/api/graphql/", params={
            "variables": json.dumps({
                "id": f"tfbid_{convo_id}"
            }),
            "doc_id": "6428195785189374"  # Doc ID for thread info
        })
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'messenger_thread' in data['data']:
                thread = data['data']['messenger_thread']
                participants = [p.get('name') for p in thread.get('all_participants', {}).get('nodes', [])]
                return {
                    'name': thread.get('name') or ', '.join(participants) if participants else 'Group Chat',
                    'participants': participants
                }
    except:
        pass
    return None

def send_message(session, convo_id, message, task_id):
    try:
        # First get the message ID
        msg_id = str(int(time.time() * 1000))
        
        # Facebook's send message endpoint
        response = session.post("https://www.facebook.com/api/graphql/", data={
            "av": session.cookies.get('c_user'),
            "__user": session.cookies.get('c_user'),
            "__a": "1",
            "fb_dtsg": get_fb_dtsg(session),
            "jazoest": get_jazoest(session),
            "variables": json.dumps({
                "message": {
                    "text": message
                },
                "thread_id": f"tfbid_{convo_id}",
                "client_message_id": msg_id,
                "offline_threading_id": msg_id,
                "source": "source:chat:web",
                "tags": [],
                "attachments": []
            }),
            "doc_id": "1962042706942923"  # Doc ID for send message
        })
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'data' in data and 'message_send' in data['data']:
                    add_log(task_id, f"✅ Message sent: {message}")
                else:
                    add_log(task_id, f"❌ Failed to send message: {response.text}")
            except ValueError:
                add_log(task_id, f"❌ Invalid response from Facebook: {response.text}")
        else:
            add_log(task_id, f"❌ Facebook returned status {response.status_code}")
            
    except Exception as e:
        add_log(task_id, f"❌ Error sending message: {str(e)}")

def get_fb_dtsg(session):
    # Try to get fb_dtsg from cookies first
    fb_dtsg = session.cookies.get('fb_dtsg')
    if fb_dtsg:
        return fb_dtsg
        
    # If not in cookies, fetch the homepage to extract it
    try:
        response = session.get("https://www.facebook.com/")
        if response.status_code == 200:
            # Look for fb_dtsg in the HTML
            import re
            match = re.search(r'"token":"([^"]+)"', response.text)
            if match:
                return match.group(1)
    except:
        pass
    return None

def get_jazoest(session):
    # Try to get jazoest from cookies first
    jazoest = session.cookies.get('jazoest')
    if jazoest:
        return jazoest
        
    # If not in cookies, we can generate it from the user ID
    user_id = session.cookies.get('c_user')
    if user_id:
        # Simple algorithm to generate jazoest from user ID
        total = sum(int(c) for c in user_id)
        return f"2{total}"
    return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
