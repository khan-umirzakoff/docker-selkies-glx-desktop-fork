import os
import docker
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
docker_client = docker.from_env()

# --- Database & User Management (Placeholder) ---
# In a real application, you would have a database (like PostgreSQL, MySQL, or MongoDB)
# and a proper user model. For this example, we'll use a simple dictionary to mock a user database.
MOCK_USERS = {
    "user_A": {
        "id": "user_A",
        "username": "testuser",
        "steam_login": "steam_login_A",
        # In a real app, this should be stored securely encrypted, not in plain text.
        "steam_password_encrypted": "steam_password_A"
    }
}

def get_user_from_request(req):
    # In a real app, you would validate a JWT or session cookie.
    # For this example, we'll use a simple "Authorization" header like "Bearer user_A".
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        user_id = auth_header.split(' ')[1]
        return MOCK_USERS.get(user_id)
    return None

def get_steam_credentials(user_id):
    user = MOCK_USERS.get(user_id)
    if user:
        # In a real app, you would decrypt the password here.
        return {
            "login": user['steam_login'],
            "password": user['steam_password_encrypted']
        }
    return None
# ----------------------------------------------------

@app.route('/api/v1/games/launch', methods=['POST'])
def launch_game():
    # 1. Authenticate user
    user = get_user_from_request(request)
    if not user:
        return jsonify({"error": "Authentication required. Provide 'Authorization: Bearer <user_id>' header."}), 401

    # 2. Get game AppID from request body
    data = request.get_json()
    game_app_id = data.get('game_app_id')
    if not game_app_id:
        return jsonify({"error": "game_app_id is required in request body"}), 400

    # 3. Get user's Steam credentials
    steam_creds = get_steam_credentials(user['id'])
    if not steam_creds:
        return jsonify({"error": "Steam credentials not found for user"}), 404

    container = None
    try:
        # 4. Prepare user-specific data volume path on the host
        # The base path should be configured via environment variables.
        user_data_base_path = os.getenv("USER_DATA_PATH", "./user-data")
        user_data_path = os.path.join(os.path.abspath(user_data_base_path), user['id'])
        os.makedirs(user_data_path, exist_ok=True)

        print(f"Starting container for user {user['id']} with game {game_app_id}...")

        # 5. Run the Docker container
        container = docker_client.containers.run(
            image="menda-cloud-gaming:latest",
            detach=True,
            volumes={
                'games': {'bind': '/home/steam/games', 'mode': 'ro'},
                user_data_path: {'bind': '/home/ubuntu/.steam', 'mode': 'rw'}
            },
            tmpfs={'/dev/shm': 'rw,size=1g'},
            device_requests=[
                docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])
            ],
            # It's good practice to remove the container once it's stopped
            auto_remove=True
        )

        print(f"Container {container.id[:12]} started. Executing launch script...")

        # 6. Execute the launch script inside the container
        exec_env = {
            "STEAM_USER": steam_creds['login'],
            "STEAM_PASS": steam_creds['password'],
            "GAME_APP_ID": str(game_app_id),
            "DISPLAY": os.getenv("CONTAINER_DISPLAY", ":20")
        }
        exit_code, (output) = container.exec_run(
            cmd="/usr/local/bin/launch_game.sh",
            environment=exec_env
        )

        if exit_code != 0:
            raise Exception(f"Failed to launch game. Logs: {output.decode()}")

        # 7. Get connection info and return to frontend
        container.reload()
        container_ip = container.attrs['NetworkSettings']['IPAddress']
        sunshine_port = os.getenv("SUNSHINE_PORT", "47989")

        print(f"Session for user {user['id']} is live at {container_ip}:{sunshine_port}")

        return jsonify({
            "message": "Session started successfully",
            "connection_info": {
                "ip": container_ip,
                "port": sunshine_port
            },
            "container_id": container.id
        })

    except Exception as e:
        print(f"An error occurred: {e}")
        # Cleanup: stop the container if it was created
        if container:
            print(f"Stopping and removing container {container.id[:12]} due to error.")
            container.stop()
            # auto_remove=True handles removal
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
