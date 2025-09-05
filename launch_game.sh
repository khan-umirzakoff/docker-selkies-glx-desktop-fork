#!/bin/bash
set -e

# Check for required environment variables
if [ -z "$STEAM_USER" ] || [ -z "$STEAM_PASS" ] || [ -z "$GAME_APP_ID" ]; then
  echo "Error: STEAM_USER, STEAM_PASS, and GAME_APP_ID environment variables must be set."
  exit 1
fi

echo "Starting game launch sequence..."

# It's better to use a two-factor auth code if enabled.
# For this script, we assume password and guard code (if any) are passed in STEAM_PASS.
# The orchestrator should handle getting the guard code from the user if needed.
echo "Logging into Steam..."
/usr/games/steamcmd +login "$STEAM_USER" "$STEAM_PASS" +quit

# The login command saves the credentials. Now we can launch the game.
# The game needs to connect to the existing X server, so the DISPLAY variable is crucial.
# We assume the orchestrator (e.g., `docker exec -e DISPLAY=:20`) sets this.
if [ -z "$DISPLAY" ]; then
  echo "Error: DISPLAY environment variable is not set. Cannot launch graphical application."
  exit 1
fi

echo "Launching game with AppID: $GAME_APP_ID"
# Use the graphical steam client to launch the game, not steamcmd
# The `steam` command is usually a script that sets up the environment.
# We need to find its exact location or hope it's in the PATH for the 'ubuntu' user.
# A typical path could be /home/ubuntu/.steam/steam.sh
# For now, we'll assume `steam` is in the path.
steam -applaunch "$GAME_APP_ID"

echo "Game launch command issued."
