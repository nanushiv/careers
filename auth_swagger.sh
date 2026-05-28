#!/bin/bash
# Get a fresh Clerk JWT and inject it into Swagger UI (localhost:8000/docs)
# Usage: ./auth_swagger.sh

CLERK_SECRET="sk_test_tMMEGg3aIVHkRS6ddJDirb2eauEbQnKl9O1uvKevgJ"
SESSION_ID="sess_3EJ9BEsHFLpemBggFB5HSRcIksz"

echo "Getting fresh Clerk token..."
TOKEN=$(curl -s -X POST "https://api.clerk.com/v1/sessions/${SESSION_ID}/tokens" \
  -H "Authorization: Bearer ${CLERK_SECRET}" \
  -H "Content-Type: application/json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('jwt','ERROR'))")

if [[ "$TOKEN" == ERROR* ]]; then
  echo "Failed to get token. Session may have expired."
  exit 1
fi

echo "Injecting token into Swagger (localhost:8000/docs)..."
osascript - "$TOKEN" <<'EOF'
on run argv
  set token to item 1 of argv
  set authJson to "{\"bearerAuth\":{\"name\":\"bearerAuth\",\"schema\":{\"type\":\"http\",\"scheme\":\"bearer\"},\"value\":\"" & token & "\"}}"
  set jsCode to "localStorage.setItem('authorized', JSON.stringify(" & authJson & ")); location.reload();"

  tell application "Google Chrome"
    -- Find existing Swagger tab or open a new one
    set swaggerTab to null
    set swaggerWin to null
    repeat with w in every window
      set tabList to every tab of w
      repeat with t in tabList
        if URL of t contains "localhost:8000/docs" then
          set swaggerTab to t
          set swaggerWin to w
          exit repeat
        end if
      end repeat
      if swaggerTab is not null then exit repeat
    end repeat

    if swaggerTab is null then
      open location "http://localhost:8000/docs"
      delay 2
      set swaggerTab to active tab of front window
    else
      set index of swaggerWin to 1
    end if

    execute swaggerTab javascript jsCode
  end tell
end run
EOF

echo "Done! Swagger is now authorized. Token valid for ~60 seconds."
echo "(Re-run this script if you get 401 errors)"
