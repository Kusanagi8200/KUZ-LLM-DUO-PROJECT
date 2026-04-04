#!/bin/bash

# This program is free software : you can redistribute it and/or modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

echo "===== NODE A : FHC2 / KUZAI ====="
hostnamectl
cat /etc/os-release
uname -a

echo
echo "===== IDENTITE / RESEAU ====="
hostname
ip -br a
ip r
ping -c 2 10.141.52.126 || true

echo
echo "===== GPU / CUDA ====="
nvidia-smi
which nvcc || true
nvcc --version || true
ls -ld /usr/local/cuda /usr/local/cuda-13.2 2>/dev/null || true

echo
echo "===== LLAMA.CPP ====="
ls -ld /opt/src/llama.cpp /opt/src/llama.cpp/build/bin 2>/dev/null || true
ls -1 /opt/src/llama.cpp/build/bin | grep '^llama-' || true

echo
echo "===== MODELES ====="
ls -lh /opt/llm/models 2>/dev/null || true

echo
echo "===== SERVICE KUZAI ====="
systemctl status llama-server-a.service --no-pager -l
systemctl is-enabled llama-server-a.service
ss -ltnp | grep ':8080' || true

echo
echo "===== API LOCALE KUZAI ====="
curl -s http://127.0.0.1:8080/v1/models | jq
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Reply in one short sentence and confirm that KUZAI on fhc2 is working locally."
      }
    ]
  }' | jq -r '.choices[0].message.content'

echo
echo "===== ORCHESTRATOR ENV ====="
ls -ld /opt/llm/orchestrator /opt/llm/orchestrator/venv 2>/dev/null || true
/opt/llm/orchestrator/venv/bin/python3 --version
/opt/llm/orchestrator/venv/bin/pip show requests || true
