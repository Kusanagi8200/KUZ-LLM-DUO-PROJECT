
echo "===== CONNECTIVITE KUZAI -> DARKAI ====="
ping -c 4 10.141.52.126 || true

echo
echo "===== MODELS DARKAI ====="
curl -s http://10.141.52.126:8080/v1/models | jq

echo
echo "===== CHAT DARKAI ====="
curl -s http://10.141.52.126:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Reply in one short sentence and confirm that DARKAI is reachable from KUZAI."
      }
    ]
  }' | jq -r '.choices[0].message.content'
