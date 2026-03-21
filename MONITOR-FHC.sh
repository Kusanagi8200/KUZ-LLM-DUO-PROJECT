#!/bin/bash

# This program is free software : you can redistribute it and/or modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

echo "===== NODE B : FHC / DARKAI ====="
hostnamectl
cat /etc/os-release
uname -a

echo
echo "===== IDENTITE / RESEAU ====="
hostname
ip -br a
ip r
ping -c 2 10.141.52.19 || true

echo
echo "===== GPU / CUDA ====="
nvidia-smi
which nvcc || true
nvcc --version || true
ls -ld /usr/local/cuda /usr/local/cuda-12.9 /usr/local/cuda-13.2 2>/dev/null || true

echo
echo "===== OLLAMA ====="
systemctl status ollama --no-pager -l 2>/dev/null || true
which ollama || true
find /etc/systemd/system /usr/local/bin /usr/share /var/lib /var/log /root /home -maxdepth 3 \( -iname '*ollama*' -o -iname '.ollama' \) 2>/dev/null

echo
echo "===== LLAMA.CPP ====="
ls -ld /opt/src/llama.cpp /opt/src/llama.cpp/build/bin 2>/dev/null || true
ls -1 /opt/src/llama.cpp/build/bin | grep '^llama-' || true

echo
echo "===== MODELES ====="
ls -lh /opt/llm/models 2>/dev/null || true

echo
echo "===== SERVICE DARKAI ====="
systemctl status llama-server-b.service --no-pager -l
systemctl is-enabled llama-server-b.service
ss -ltnp | grep ':8080' || true

echo
echo "===== API LOCALE DARKAI ====="
curl -s http://127.0.0.1:8080/v1/models | jq
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Reply in one short sentence and confirm that DARKAI on fhc is working locally."
      }
    ]
  }' | jq -r '.choices[0].message.content'
