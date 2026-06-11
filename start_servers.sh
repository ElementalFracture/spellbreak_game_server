#!/bin/bash
# Made with <3 by Doobs in Miami, FL. 03/17/2025

# Ensure script runs from the correct directory
cd ./Instances/GameServer || exit 1

# Default values if environment variables are not set
PATCH_ENV=${PATCH_ENV:-prod}  # Default to "Live" if not set
GAMEMODE=${GAMEMODE:-Solo}
GAMEPORT=${GAMEPORT:-7777}
SERVERNAME=${SERVERNAME:-Spellbreak}
ELIXIRPORT=${ELIXIRPORT:-8877}
ELIXIRHOST=${ELIXIRHOST:-spellbreak_matchmaking-dev}
IDLETIMER=${IDLETIMER:-60}
MATCHTRACKLISTENPORT=${MATCHTRACKLISTENPORT:-8889}
MATCHTRACKFREQUENCY=${MATCHTRACKFREQUENCY:-5}
PATCH_URL=${PATCH_URL:-https://cdn.elefrac.com/patch/latest.zip}
PATCH_TEST_URL=${PATCH_TEST_URL:-http://cdn.elefrac.com/patch/dev.zip}

CONFIG_PATH="/spellbreak-server/Instances/GameServer/config.ini"
PATCH_URL=$PATCH_URL
PATCH_TEST_URL=$PATCH_TEST_URL
PATCH_DIR="/spellbreak-server/BaseServer/g3/Content/Paks"
PATCH_FILE="$PATCH_DIR/latest.zip"
PATCH_TESTING_FILE="$PATCH_DIR/dev.zip"

# Ensure the patch directory exists
mkdir -p "$PATCH_DIR"

# Skip patch installation if PATCH_ENV is set to "vanilla"
if [ "$PATCH_ENV" = "vanilla" ]; then
    echo "PATCH_ENV is set to vanilla. Skipping patch installation."
else
    # Determine which patch to deploy based on PATCH_ENV
    if [ "$PATCH_ENV" = "dev" ]; then
        PATCH_TO_DEPLOY="$PATCH_TESTING_FILE"
        PATCH_SOURCE_URL="$PATCH_TEST_URL"
        echo "Deployment mode: dev"
    else
        PATCH_TO_DEPLOY="$PATCH_FILE"
        PATCH_SOURCE_URL="$PATCH_URL"
        echo "Deployment mode: production"
    fi

    # Download and extract the selected patch
    echo "Downloading patch from $PATCH_SOURCE_URL..."
    if curl -fSL "$PATCH_SOURCE_URL" -o "$PATCH_TO_DEPLOY"; then
        echo "Extracting patch..."
        unzip -o "$PATCH_TO_DEPLOY" -d "$PATCH_DIR"
        echo "Patch extracted successfully."

        # Delete the zip file after extraction
        rm -f "$PATCH_TO_DEPLOY"
    else
        echo "Failed to download patch. Check network or URL."
    fi
fi

# Generate the config file dynamically
cat <<EOF > $CONFIG_PATH
[GameSettings]
gamepathdirectory = /spellbreak-server/BaseServer/
logdirectory = /spellbreak-server/BaseServer/g3/Saved/Logs/
gamemode = $GAMEMODE
gameport = $GAMEPORT
servername = $SERVERNAME

[ServerSettings]
elixirPort = $ELIXIRPORT
elixirHost = $ELIXIRHOST
idletimer = $IDLETIMER

[MatchTracker]
broadcastport = $MATCHTRACKLISTENPORT
frequency = $MATCHTRACKFREQUENCY
EOF

echo "Generated config.ini:"
cat $CONFIG_PATH

# Start the game server using Wine
python3 Launch.py &

# Wait for all background processes to finish
wait
