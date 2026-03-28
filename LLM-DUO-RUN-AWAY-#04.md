#### ``LLM - DUO - RUN AWAY - #04``

#### ``WHAT'S INSIDE THE BLACK BOX ?``

---
####  ``CONTROL CONSOLE WEB APP``

Two local open-source LLMs running on two separate physical machines, communicating in an automated A/B loop driven by a central Python orchestrator. Control interface served by PHP/Apache on the main node. 

---
#### ``INFRASTRUCTURE``

#### ``Node A - fhc2 - KUZAI``

Node A is the main machine of the lab. It runs the KUZAI inference service, the Python orchestrator, and the PHP web application.  
All control logic originates from this node.


| Parameter | Value |
|---|---|
| IP | 10.141.52.19 |
| CPU | Intel i9 |
| RAM | 32 GB |
| GPU | NVIDIA RTX 5060 - 8 GB VRAM |
| Role | KUZAI + Orchestrator + PHP Application |
| Service | `llama-server-a.service` |
| API Port | 8080 |

---

#### ``Node B - fhc - DARKAI``

Node B is the secondary inference node. It exposes only the DARKAI LLM service and answers requests sent by the orchestrator on Node A over the local network.


| Parameter | Value |
|---|---|
| IP | 10.141.52.126 |
| CPU | Intel i5 |
| RAM | 32 GB |
| GPU | NVIDIA RTX 3050 - 4 GB VRAM |
| Role | DARKAI only |
| Service | `llama-server-b.service` |
| API Port | 8080 |

---

#### ``DEPLOYMENT - Node B (fhc)``

The following steps cover the full deployment of Node B from a clean system state. Each step must be validated before moving to the next.

#### ``INITIAL HARDWARE AUDIT``

Before any installation, a complete hardware audit is performed to confirm the machine identity, available resources, GPU presence, and network state.  
This baseline also checks whether NVIDIA drivers and CUDA are already present.


```bash
hostnamectl
cat /etc/os-release
uname -a

echo "===== CPU ====="
lscpu | egrep 'Model name|Socket|Thread|Core|CPU\(s\)'

echo "===== RAM ====="
free -h
grep MemTotal /proc/meminfo

echo "===== GPU ====="
lspci -nnk | grep -A3 -E 'VGA|3D|Display'

echo "===== DISKS ====="
lsblk -e7 -o NAME,SIZE,TYPE,FSTYPE,FSUSE%,MOUNTPOINTS,MODEL
blkid
df -hT

echo "===== BOOT MODE ====="
[ -d /sys/firmware/efi ] && echo UEFI || echo BIOS

echo "===== NETWORK ====="
ip -br a
ip r

echo "===== NVIDIA / CUDA ====="
nvidia-smi || true
which nvcc || true
nvcc --version || true
dpkg -l | egrep 'nvidia|cuda|nouveau' || true
lsmod | egrep 'nvidia|nouveau' || true
```
---
#### ``INSTALL SYSTEM DEPENDENCIES``

Installs all build tools and libraries required to compile llama.cpp from source.  
This includes CMake, Ninja, Git, OpenSSL development headers, and the Python 3 toolchain for the orchestrator virtualenv.


```bash
apt update

apt install -y \
  build-essential \
  cmake \
  ninja-build \
  git \
  curl \
  wget \
  jq \
  ca-certificates \
  pkg-config \
  libssl-dev \
  python3 \
  python3-venv \
  python3-pip \
  pciutils
```
---
#### ``PIN NVIDIA DRIVER VERSION``

The NVIDIA driver version is pinned to prevent automatic upgrades during system updates.  
An unexpected driver change could break CUDA compatibility and take the inference service offline.


```bash
apt-mark hold \
  nvidia-driver-575 \
  nvidia-utils-575 \
  nvidia-compute-utils-575 \
  nvidia-dkms-575
```
---
#### ``ADD CUDA REPOSITORY``

Adds the official NVIDIA CUDA package repository for Ubuntu 22.04.  
The keyring and pinning file are installed first to ensure authenticated and prioritized package resolution.


```bash
wget -O /usr/share/keyrings/cuda-archive-keyring.gpg \
  https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-archive-keyring.gpg

wget -O /etc/apt/preferences.d/cuda-repository-pin-600 \
  https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin

cat > /etc/apt/sources.list.d/cuda-ubuntu2204.list <<'EOF'
deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /
EOF
```
```bash
apt update
```
---
#### ``CHECK AVAILABLE CUDA CANDIDATES``

Verifies which CUDA toolkit versions are available in the repository before installing.  
This step confirms the repository is correctly configured and the target version is resolvable.


```bash
apt-cache policy cuda-toolkit-12-9 cuda-toolkit-13-2 cuda-toolkit-13
nvidia-smi
```
---
#### ``INSTALL CUDA TOOLKIT``

Installs CUDA toolkit 12.9. This provides `nvcc`, the CUDA compilation tools, and the runtime libraries required by llama.cpp for GPU-accelerated inference.


```bash
apt install -y cuda-toolkit-12-9
```
---
#### ``SET CUDA ENVIRONMENT VARIABLES``

Makes the CUDA binaries and libraries available to all processes at login by writing exports to `/etc/profile.d/cuda.sh`. A symlink to `zz-cuda.sh` ensures the file is loaded last and takes precedence.


```bash
cat > /etc/profile.d/cuda.sh <<'EOF'
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
EOF

chmod 644 /etc/profile.d/cuda.sh
ln -sf /etc/profile.d/cuda.sh /etc/profile.d/zz-cuda.sh
source /etc/profile.d/cuda.sh
```
---
#### ``VERIFY CUDA INSTALLATION``

Confirms that `nvcc` is reachable on the PATH, that the CUDA symlinks are correctly set, and that `nvidia-smi` reports the GPU without errors. The node is not ready for compilation until all these checks pass.


```bash
which nvcc
nvcc --version
ls -ld /usr/local/cuda /usr/local/cuda-12.9
ls -l /etc/alternatives/cuda
ls -l /usr/local/cuda/bin/nvcc
nvidia-smi
echo $PATH
```
---
#### ``CREATE WORKING DIRECTORIES``

Creates the directory tree used by llama.cpp, the model storage, the orchestrator, and the service logs.  
These paths are referenced by the systemd unit and all Python scripts.


```bash
mkdir -p /opt/src
mkdir -p /opt/llm
mkdir -p /opt/llm/models
mkdir -p /opt/llm/run
mkdir -p /var/log/llm-duo
```
---
#### ``BUILD LLAMA.CPP WITH CUDA``

Clones the llama.cpp repository and compiles it from source with CUDA acceleration enabled.  
The flag `DGGML_CUDA=ON` activates GPU offloading. The build uses all available CPU cores via `nproc`.


```bash
cd /opt/src
git clone https://github.com/ggml-org/llama.cpp
cd /opt/src/llama.cpp

export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

cmake -S . -B build -G Ninja -DGGML_CUDA=ON
cmake --build build --config Release -j"$(nproc)"
```
---
#### ``VERIFY BINARIES``

Lists the produced binaries and checks that the compiled `llama-cli` binary is dynamically linked against the expected CUDA and cuBLAS libraries.  
A missing CUDA link means the build did not use GPU support.


```bash
ls -1 build/bin | grep '^llama-'
ldd build/bin/llama-cli | egrep 'cuda|cublas|cudart|stdc\+\+|libm|libpthread' || true
```

#### ``CLI MODEL TEST``

Runs a direct interactive test of the model via the CLI binary to confirm that the GPU is correctly used for inference and that the model loads without errors.  
The token throughput is noted here for reference.


```bash
cd /opt/src/llama.cpp
./build/bin/llama-cli \
  -hf bartowski/granite-3.1-3b-a800m-instruct-GGUF:granite-3.1-3b-a800m-instruct-Q4_K_M.gguf
```

``Validation output -->``

```
build : b8357-89d0aec04
model : bartowski/granite-3.1-3b-a800m-instruct-GGUF
Prompt: 307.4 t/s | Generation: 136.1 t/s
```
---
#### ``DEPLOY MODEL FILE``

Creates a dedicated system user `llm` with no login shell, copies the downloaded model file into `/opt/llm/models/`, and sets ownership. 
The inference service will run under this user for isolation.


```bash
id -u llm >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin -d /opt/llm llm

cp -f /root/.cache/llama.cpp/bartowski_granite-3.1-3b-a800m-instruct-GGUF_granite-3.1-3b-a800m-instruct-Q4_K_M.gguf \
  /opt/llm/models/

chown -R llm:llm /opt/llm
chown -R llm:llm /var/log/llm-duo
ls -lh /opt/llm/models
```
---
#### ``SYSTEMD SERVICE - Node B (DARKAI)``

Defines and enables the `llama-server-b.service` unit. The service runs as the `llm` user, sets the CUDA environment, and starts `llama-server` bound to all interfaces on port 8080. 
It restarts automatically on failure.


```bash
cat > /etc/systemd/system/llama-server-b.service <<'EOF'
[Unit]
Description=llama.cpp server - Node B
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=llm
Group=llm
WorkingDirectory=/opt/src/llama.cpp
Environment="PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="LD_LIBRARY_PATH=/usr/local/cuda/lib64"
ExecStart=/opt/src/llama.cpp/build/bin/llama-server \
  -m /opt/llm/models/bartowski_granite-3.1-3b-a800m-instruct-GGUF_granite-3.1-3b-a800m-instruct-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/llm /var/log/llm-duo

[Install]
WantedBy=multi-user.target
EOF
```
```bash
systemctl daemon-reload
systemctl enable --now llama-server-b.service
systemctl status llama-server-b.service --no-pager -l
ss -ltnp | grep 8080
```

#### ``LOCAL API TEST - Node B``

Verifies the inference API is reachable locally. First checks the model list endpoint, then sends a chat completion request and validates that the model returns a coherent response.


```bash
curl -s http://127.0.0.1:8080/v1/models | jq

curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Reply in one short sentence and confirm that node B is running locally."}
    ]
  }' | jq -r '.choices[0].message.content'
```

``Output -->`` `"Yes, node B is running locally."`

---

#### ``MONITORING SCRIPTS``

Two dedicated shell scripts provide a full audit of each node.  
They cover system identity, GPU state, llama.cpp binaries, loaded models, service status, and a live API test. Run them to verify the state of any node at any time.

#### ``MONITOR-FHC.sh - Node B audit (DARKAI)``

Full audit script for Node B (fhc). Covers OS identity, network, GPU and CUDA state, llama.cpp binaries, model files, DARKAI service status, and a local API inference test.


```bash
echo "===== NODE B : FHC / DARKAI ====="
hostnamectl
cat /etc/os-release
uname -a

echo "===== IDENTITY / NETWORK ====="
hostname
ip -br a
ip r
ping -c 2 10.141.52.19 || true

echo "===== GPU / CUDA ====="
nvidia-smi
which nvcc || true
nvcc --version || true
ls -ld /usr/local/cuda /usr/local/cuda-12.9 /usr/local/cuda-13.2 2>/dev/null || true

echo "===== LLAMA.CPP ====="
ls -ld /opt/src/llama.cpp /opt/src/llama.cpp/build/bin 2>/dev/null || true
ls -1 /opt/src/llama.cpp/build/bin | grep '^llama-' || true

echo "===== MODELS ====="
ls -lh /opt/llm/models 2>/dev/null || true

echo "===== DARKAI SERVICE ====="
systemctl status llama-server-b.service --no-pager -l
systemctl is-enabled llama-server-b.service
ss -ltnp | grep ':8080' || true

echo "===== LOCAL DARKAI API ====="
curl -s http://127.0.0.1:8080/v1/models | jq
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Reply in one short sentence and confirm that DARKAI on fhc is working locally."}
    ]
  }' | jq -r '.choices[0].message.content'
```
---
#### ``MONITOR-FHC2.sh - Node A audit (KUZAI)``

Full audit script for Node A (fhc2). Same coverage as the Node B script, with the addition of a connectivity test toward Node B and a check of the Python orchestrator virtual env.


```bash
echo "===== NODE A : FHC2 / KUZAI ====="
hostnamectl
cat /etc/os-release
uname -a

echo "===== IDENTITY / NETWORK ====="
hostname
ip -br a
ip r
ping -c 2 10.141.52.126 || true

echo "===== GPU / CUDA ====="
nvidia-smi
which nvcc || true
nvcc --version || true
ls -ld /usr/local/cuda /usr/local/cuda-13.2 2>/dev/null || true

echo "===== LLAMA.CPP ====="
ls -ld /opt/src/llama.cpp /opt/src/llama.cpp/build/bin 2>/dev/null || true
ls -1 /opt/src/llama.cpp/build/bin | grep '^llama-' || true

echo "===== MODELS ====="
ls -lh /opt/llm/models 2>/dev/null || true

echo "===== KUZAI SERVICE ====="
systemctl status llama-server-a.service --no-pager -l
systemctl is-enabled llama-server-a.service
ss -ltnp | grep ':8080' || true

echo "===== LOCAL KUZAI API ====="
curl -s http://127.0.0.1:8080/v1/models | jq
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Reply in one short sentence and confirm that KUZAI on fhc2 is working locally."}
    ]
  }' | jq -r '.choices[0].message.content'

echo "===== ORCHESTRATOR ENV ====="
ls -ld /opt/llm/orchestrator /opt/llm/orchestrator/venv 2>/dev/null || true
/opt/llm/orchestrator/venv/bin/python3 --version
/opt/llm/orchestrator/venv/bin/pip show requests || true
```

---

#### ``PYTHON ORCHESTRATOR``

The orchestrator is the central control process. It runs on Node A, manages the A/B dialogue loop between the two models, handles context reconstruction, 
enforces output length, and writes transcripts. ORCHESTRATOR-02.py is the production version with Node A and B IPs set as defaults.

#### ``ORCHESTRATOR-02.py - Production version``

Production orchestrator with the fhc2 and fhc endpoints hardcoded as defaults. 
All run parameters are configurable via CLI flags. Output is written to a timestamped directory under `/opt/llm/orchestrator/runs/`.


``Interpreter -->`` `/opt/llm/orchestrator/venv/bin/python3`

Default URLs:
- Node A: `http://10.141.52.19:8080/v1/chat/completions`
- Node B: `http://10.141.52.126:8080/v1/chat/completions`

Output --> `/opt/llm/orchestrator/runs/run-ab-YYYYMMDD-HHMMSS/`

#### ``CLI PARAMETERS``

All parameters have sensible defaults. The only required argument is `--opening-prompt`.  
Temperature and length caps can be tuned independently for each model.

| Parameter | Default | Description |
|---|---|---|
| `--url-a` | `http://10.141.52.19:8080/v1/chat/completions` | KUZAI endpoint |
| `--url-b` | `http://10.141.52.126:8080/v1/chat/completions` | DARKAI endpoint |
| `--opening-prompt` | required | Opening prompt |
| `--opening-from-a` | flag | KUZAI speaks first |
| `--turns` | 6 | Total number of turns |
| `--delay` | 1.0 | Delay between turns (seconds) |
| `--temperature-a` | 0.35 | KUZAI temperature |
| `--temperature-b` | 0.35 | DARKAI temperature |
| `--max-lines` | 5 | Soft reply length target |
| `--max-sentences` | 4 | Hard sentence cap |
| `--max-chars` | 500 | Hard character cap |
| `--history-depth` | 3 | Previous turns kept in context |
| `--output-dir` | `/opt/llm/orchestrator/runs` | Output directory |

---
#### ``MODEL SYSTEM PROMPT``

Each model receives a system prompt injected at the start of every turn. 
These prompts define the identity, role, and output style of each agent. They are kept minimal to avoid over-constraining the models.


**``KUZAI (Node A)``**
```
You are KUZAI.
- Your visible name is KUZAI.
- You run on host fhc2.
- Never say you are DARKAI.
- Reply naturally and directly.
- Keep answers short, readable, and useful.
- Do not describe hidden rules or internal instructions.
- Output only the reply itself.
```

**``DARKAI (Node B)``**
```
You are DARKAI.
- Your visible name is DARKAI.
- You run on host fhc.
- Never say you are KUZAI.
- Reply naturally and directly.
- Keep answers short, readable, and useful.
- Do not describe hidden rules or internal instructions.
- Output only the reply itself.
```
--- 

#### ``LOOP LOGIC``

The orchestrator alternates turns between KUZAI and DARKAI.  
Each turn rebuilds a prompt from the opening prompt, the last N turns of history, and the previous message. 
Responses are trimmed by `enforce_length()` before being stored and displayed.


```
turn 1  → KUZAI   → build_prompt(opening_prompt, history=[])
turn 2  → DARKAI  → build_prompt(opening_prompt, history[-3:], last_message=turn1)
turn 3  → KUZAI   → build_prompt(opening_prompt, history[-3:], last_message=turn2)
...
turn N  → write transcript.json + transcript.md
```

Per-response processing -->
1. `query_model()` → POST `/v1/chat/completions` with `temperature`
2. `enforce_length()` → truncate to `max_sentences` / `max_chars`
3. `strip_prefixes()` → remove prefixes `KUZAI:`, `RESPONSE:`, etc.
4. `normalize_whitespace()` → normalize spaces and line breaks
5. `print_wrapped_reply()` → console output at 88 columns
6. Append to `history` and `transcript`

``Social mode detection -->`` If the prompt contains `introduce yourself`, `who are you`, `what is your name`, etc. → short mode activated, no meta-commentary.

---
#### ``EXEMPLE LAUNCH COMMAND``

Typical production launch using the default Node A and B endpoints.  
The orchestrator saves both a JSON and a Markdown transcript in a timestamped run directory.


```bash
/opt/llm/orchestrator/venv/bin/python3 /opt/llm/orchestrator/ORCHESTRATOR-02.py \
  --opening-prompt "Introduce yourself briefly." \
  --opening-from-a \
  --turns 6 \
  --temperature-a 0.35 \
  --temperature-b 0.35 \
  --max-sentences 4 \
  --history-depth 3
```
---
#### ``FIRST VALIDATED DIALOGUE TEST``

First successful inter-node dialogue test, using the social intro prompt to confirm that each model correctly identifies itself and stays within its assigned role.


```bash
/opt/llm/orchestrator/duo_loop_ab.py \
  --url-a http://127.0.0.1:8080/v1/chat/completions \
  --url-b http://10.141.52.126:8080/v1/chat/completions \
  --opening-prompt "Introduce yourself briefly, say your name, and say your purpose in this project. Use 2 very short sentences only." \
  --turns 2
```

Output --> 

``KUZAI-LLM -->`` Hello, I'm KUZAI-LLM. I'm here to help with your questions. 

``DARK-AI-LLM -->`` Greetings, I'm DARK-AI-LLM, here to provide concise responses.

---

#### ``PROJECT GUARDRAILS (duo_loop_ab.py v1)``

Mandatory constraints injected into every prompt in the first version of the orchestrator.  
They enforce the 100% local and on-premise scope and prevent the models from drifting toward cloud or SaaS-based proposals.


```
MANDATORY PROJECT CONSTRAINTS:
1. This project is a local LLM Duo lab.
2. Node A and Node B are Linux machines in the lab.
3. LLM engines must be local.
4. Exchanges must go through local/private HTTP endpoints.
5. Storage must be local.
6. Logs must be local.
7. Tools should be open source whenever possible.
8. Any proposal involving cloud, SaaS, CDN, S3, GCS, Azure, AWS, Google Cloud is out of scope.
9. Answers must remain realistic for a homelab / technical lab environment.
```

---

#### ``PHP WEB APPLICATION - KUZCHAT-LLM-DUO``

KUZCHAT-LLM-DUO is the web control console for the project.  
It runs on Node A under Apache and provides a browser-based interface to configure orchestrator profiles, launch and stop runs, monitor both LLM nodes, and read live transcripts.

#### ``APACHE CONFIGURATION``

The VirtualHost serves the application on port 80 from `/var/www/html/KUZCHAT-LLM-DUO/public`. `AllowOverride All` enables `.htaccess` routing. The entry point is `index.php`.


```apache
<VirtualHost *:80>
    ServerName 10.141.52.19
    ServerAlias fhc2 localhost
    ServerAdmin root@localhost
    DocumentRoot /var/www/html/KUZCHAT-LLM-DUO/public
    ErrorLog ${APACHE_LOG_DIR}/kuzchat-llm-duo-error.log
    CustomLog ${APACHE_LOG_DIR}/kuzchat-llm-duo-access.log combined
    <Directory /var/www/html/KUZCHAT-LLM-DUO/public>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
        DirectoryIndex index.php index.html
    </Directory>
</VirtualHost>
```
---
#### ``DIRECTORY STRUCTURE``

The application separates public web assets from backend logic and persistent storage. The `api/` directory contains all PHP endpoints called by the frontend via `fetch()`.  
The `storage/` directory holds orchestrator profiles, run transcripts, and the active PID file.


```
/var/www/html/KUZCHAT-LLM-DUO/
├── public/
│   ├── index.php                     web entry point — HTML shell
│   └── assets/
│       ├── css/style.css             dark neon theme
│       └── js/app.js                 frontend controller
├── app/
│   └── config.php                    central configuration
└── storage/
    ├── orchestrators/                 orchestrator profiles (JSON)
    ├── runs/                          session transcripts
    └── launcher/                      PID + meta files
```

```
public/api/
├── status.php                        system + node health check
├── run-start.php                     launch orchestrator process
├── run-status.php                    poll run state + transcript
├── run-stop.php                      kill running process
├── orchestrators-list.php            list saved profiles
├── orchestrator-read.php             read a profile by slug
└── orchestrator-save.php             create or update a profile
```
---
#### ``FEATURES``

The application provides a complete control surface for the lab. The PHP backend communicates with the Python orchestrator via `exec()` and monitors the node APIs via `curl`.  
All state is maintained in flat files under `storage/`.


- **Session launch**: web form → parameters → `exec()` PHP to `ORCHESTRATOR-02.py`
- **Transcript viewer**: reads `transcript.json`/`.md` from `/opt/llm/orchestrator/runs/` → formatted display of exchanges
- **Service monitoring**: PHP `curl` calls to `/v1/models` on both nodes → real-time UP/DOWN status
- **Run history**: lists `run-ab-*` directories → browse past sessions
- **Configuration**: orchestrator parameters exposed in the UI (temperatures, turns, caps)

---

#### ``app/config.php``

Single source of truth for the entire application. Loaded by every PHP file via `require`. Defines node IPs and endpoints, UI parameters, and all paths used by the orchestrator launcher.

Central configuration - nodes, paths, UI settings.

```php
<?php

declare(strict_types=1);

return [
    'app_name' => 'KUZCHAT LLM DUO',
    'app_env' => 'production',
    'timezone' => 'Europe/Paris',

    'nodes' => [
        'kuzai' => [
            'label' => 'KUZAI',
            'host' => 'fhc2',
            'ip' => '10.141.52.19',
            'role' => 'Node A',
            'api_base' => 'http://10.141.52.19:8080',
            'chat_endpoint' => 'http://10.141.52.19:8080/v1/chat/completions',
            'models_endpoint' => 'http://10.141.52.19:8080/v1/models',
            'theme_class' => 'kuzai',
        ],
        'darkai' => [
            'label' => 'DARKAI',
            'host' => 'fhc',
            'ip' => '10.141.52.126',
            'role' => 'Node B',
            'api_base' => 'http://10.141.52.126:8080',
            'chat_endpoint' => 'http://10.141.52.126:8080/v1/chat/completions',
            'models_endpoint' => 'http://10.141.52.126:8080/v1/models',
            'theme_class' => 'darkai',
        ],
    ],

    'ui' => [
        'theme' => 'kuz-neon-blue',
        'brand_line' => 'THE KUZ NETWORK // KUZAI.ORG',
        'subtitle' => 'DUO ORCHESTRATION CONSOLE',
        'poll_interval_ms' => 5000,
    ],

    'orchestrator' => [
        'python_bin' => '/opt/llm/orchestrator/venv/bin/python3',
        'script_path' => '/opt/llm/orchestrator/duo_loop_engine.py',
        'profiles_dir' => '/var/www/html/KUZCHAT-LLM-DUO/storage/orchestrators',
        'output_dir' => '/var/www/html/KUZCHAT-LLM-DUO/storage/runs',
        'launcher_dir' => '/var/www/html/KUZCHAT-LLM-DUO/storage/launcher',
        'pid_file' => '/var/www/html/KUZCHAT-LLM-DUO/storage/launcher/current_run.pid',
        'meta_file' => '/var/www/html/KUZCHAT-LLM-DUO/storage/launcher/current_run.json',
    ],
];
```
---
#### ``public/index.php``

Single-page HTML shell served on every request. PHP resolves all config values at render time and injects them into `window.KUZCHAT_CONFIG` so the JavaScript frontend can consume them without additional API calls.

HTML shell - loads config, renders all UI panels, injects JS config.

```php
<?php

declare(strict_types=1);

$config = require __DIR__ . '/../app/config.php';

date_default_timezone_set($config['timezone']);

$appName = $config['app_name'];
$brandLine = $config['ui']['brand_line'];
$subtitle = $config['ui']['subtitle'];
$pollIntervalMs = (int) $config['ui']['poll_interval_ms'];

$kuzai = $config['nodes']['kuzai'];
$darkai = $config['nodes']['darkai'];

function e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= e($appName) ?></title>
    <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
    <div class="app-shell">
        <header class="topbar">
            <div class="topbar__left">
                <div class="logo-box">KUZ</div>
                <div class="title-group">
                    <h1><?= e($appName) ?></h1>
                    <p class="brand-line"><?= e($brandLine) ?></p>
                </div>
            </div>
            <div class="topbar__right">
                <div class="status-pill" id="global-status-pill">
                    <span class="status-dot"></span>
                    <span id="global-status-text">CHECKING</span>
                </div>
            </div>
        </header>

        <main class="dashboard">
            <section class="hero-card">
                <p class="eyebrow"><?= e($subtitle) ?></p>
                <h2>KUZAI / DARKAI - MONITORING</h2>
                <p class="hero-text">
                    Real-time monitoring of the web server, LLM endpoints, and connectivity between both nodes.
                    Orchestrator profiles can be edited, saved, and selected before launching a run.
                </p>
                <div class="hero-stats">
                    <div class="hero-stat">
                        <span class="hero-stat__label">ENGINE</span>
                        <span class="hero-stat__value" id="engine-status">CHECKING</span>
                    </div>
                    <div class="hero-stat">
                        <span class="hero-stat__label">WEB</span>
                        <span class="hero-stat__value" id="web-status">CHECKING</span>
                    </div>
                    <div class="hero-stat">
                        <span class="hero-stat__label">UPDATED</span>
                        <span class="hero-stat__value" id="last-update">--</span>
                    </div>
                </div>
            </section>

            <!-- STATUS SECTION -->
            <section class="section-block">
                <div class="section-header">
                    <p class="section-kicker">STATUS</p>
                    <h3 class="section-title">INFRASTRUCTURE</h3>
                </div>

                <div class="two-col-grid">
                    <!-- KUZAI NODE CARD -->
                    <article class="node-card node-card--kuzai">
                        <div class="node-card__header">
                            <div>
                                <p class="node-card__role"><?= e($kuzai['role']) ?></p>
                                <h3><?= e($kuzai['label']) ?></h3>
                            </div>
                            <span class="node-badge" id="badge-kuzai">CHECKING</span>
                        </div>
                        <div class="node-metrics">
                            <div class="metric-box">
                                <span class="metric-box__label">HOST</span>
                                <span class="metric-box__value"><?= e($kuzai['host']) ?></span>
                            </div>
                            <div class="metric-box">
                                <span class="metric-box__label">IP</span>
                                <span class="metric-box__value"><?= e($kuzai['ip']) ?></span>
                            </div>
                            <div class="metric-box metric-box--full">
                                <span class="metric-box__label">API BASE</span>
                                <span class="metric-box__value metric-box__value--small"><?= e($kuzai['api_base']) ?></span>
                            </div>
                            <div class="metric-box metric-box--full">
                                <span class="metric-box__label">MODEL</span>
                                <span class="metric-box__value metric-box__value--small" id="kuzai-model">--</span>
                            </div>
                            <div class="metric-box">
                                <span class="metric-box__label">HTTP</span>
                                <span class="metric-box__value" id="kuzai-http">--</span>
                            </div>
                            <div class="metric-box">
                                <span class="metric-box__label">LATENCY</span>
                                <span class="metric-box__value" id="kuzai-latency">--</span>
                            </div>
                        </div>
                    </article>

                    <!-- DARKAI NODE CARD -->
                    <article class="node-card node-card--darkai">
                        <div class="node-card__header">
                            <div>
                                <p class="node-card__role"><?= e($darkai['role']) ?></p>
                                <h3><?= e($darkai['label']) ?></h3>
                            </div>
                            <span class="node-badge" id="badge-darkai">CHECKING</span>
                        </div>
                        <div class="node-metrics">
                            <div class="metric-box">
                                <span class="metric-box__label">HOST</span>
                                <span class="metric-box__value"><?= e($darkai['host']) ?></span>
                            </div>
                            <div class="metric-box">
                                <span class="metric-box__label">IP</span>
                                <span class="metric-box__value"><?= e($darkai['ip']) ?></span>
                            </div>
                            <div class="metric-box metric-box--full">
                                <span class="metric-box__label">API BASE</span>
                                <span class="metric-box__value metric-box__value--small"><?= e($darkai['api_base']) ?></span>
                            </div>
                            <div class="metric-box metric-box--full">
                                <span class="metric-box__label">MODEL</span>
                                <span class="metric-box__value metric-box__value--small" id="darkai-model">--</span>
                            </div>
                            <div class="metric-box">
                                <span class="metric-box__label">HTTP</span>
                                <span class="metric-box__value" id="darkai-http">--</span>
                            </div>
                            <div class="metric-box">
                                <span class="metric-box__label">LATENCY</span>
                                <span class="metric-box__value" id="darkai-latency">--</span>
                            </div>
                        </div>
                    </article>
                </div>
            </section>

            <!-- DISCUSSION / RUN SECTION -->
            <section class="section-block">
                <!-- Orchestrator editor + run control + transcript panels -->
                <article class="panel panel--run-control">
                    <div class="panel__header panel__header--run">
                        <div>
                            <p class="eyebrow">RUN CONTROL</p>
                            <h3>Start a Discussion</h3>
                        </div>
                        <div class="run-header-side">
                            <div class="run-state-pill state-ready" id="run-state-pill">READY</div>
                            <div class="run-profile-inline">
                                PROFILE --> <span id="run-orchestrator-inline">--</span>
                            </div>
                        </div>
                    </div>

                    <form class="run-form" method="post" action="#" onsubmit="return false;" id="run-form">
                        <div class="form-row">
                            <label for="opening_prompt">Opening Prompt</label>
                            <textarea id="opening_prompt" name="opening_prompt" rows="7">Introduce yourself briefly, say your name, and say your purpose in this project.</textarea>
                        </div>
                        <div class="form-actions form-actions--run">
                            <button type="button" class="btn btn--primary btn--run-main" id="start-run-btn">START RUN</button>
                            <button type="button" class="btn btn--secondary" id="stop-run-btn" disabled>STOP</button>
                            <button type="button" class="btn btn--secondary" id="reset-run-btn">RELOAD</button>
                        </div>
                        <div class="run-status-grid">
                            <div class="metric-box">
                                <span class="metric-box__label">RUN STATE</span>
                                <span class="metric-box__value" id="run-state">IDLE</span>
                            </div>
                            <div class="metric-box">
                                <span class="metric-box__label">PID</span>
                                <span class="metric-box__value" id="run-pid">--</span>
                            </div>
                            <div class="metric-box">
                                <span class="metric-box__label">ORCHESTRATOR</span>
                                <span class="metric-box__value" id="run-orchestrator">--</span>
                            </div>
                            <div class="metric-box metric-box--full">
                                <span class="metric-box__label">STARTED AT</span>
                                <span class="metric-box__value metric-box__value--small" id="run-started">--</span>
                            </div>
                        </div>
                        <p class="panel-note panel-note--run" id="run-note">
                            Ready to launch a Duo run from the selected orchestrator profile.
                        </p>
                    </form>
                </article>

                <!-- LIVE TRANSCRIPT -->
                <article class="panel panel--transcript">
                    <div class="panel__header">
                        <p class="eyebrow">LIVE TRANSCRIPT</p>
                        <h3>Preview</h3>
                    </div>
                    <div class="transcript-list transcript-list--live" id="transcript-live">
                        <div class="message-card message-card--kuzai">
                            <div class="message-card__meta">
                                <span class="message-card__speaker">SYSTEM</span>
                            </div>
                            <div class="message-card__body">
                                No run has been launched yet from the web interface.
                            </div>
                        </div>
                    </div>
                </article>
            </section>
        </main>
    </div>

    <script>
        window.KUZCHAT_CONFIG = {
            pollIntervalMs: <?= $pollIntervalMs ?>,
            statusUrl: '/api/status.php',
            runStartUrl: '/api/run-start.php',
            runStatusUrl: '/api/run-status.php',
            runStopUrl: '/api/run-stop.php',
            orchestratorListUrl: '/api/orchestrators-list.php',
            orchestratorReadUrl: '/api/orchestrator-read.php',
            orchestratorSaveUrl: '/api/orchestrator-save.php'
        };
    </script>
    <script src="/assets/js/app.js"></script>
</body>
</html>
```
---
#### ``public/api/status.php``

Called every 5 seconds by the frontend. Reads local system metrics from `/proc` and polls both node APIs via `curl`.  
Returns a unified JSON payload covering system health, node reachability, loaded model names, and latency.

Reads system metrics (`/proc/meminfo`, `/proc/uptime`, `/proc/loadavg`) and polls both node APIs via `curl`. Returns a unified JSON payload to the frontend.

```php
<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

function readTextFileSafe(string $path): ?string
{
    if (!is_readable($path)) { return null; }
    $content = @file_get_contents($path);
    return $content === false ? null : trim($content);
}

function readHostname(): string
{
    $hostname = readTextFileSafe('/etc/hostname');
    return ($hostname !== null && $hostname !== '') ? $hostname : php_uname('n');
}

function readUptimeSeconds(): ?int
{
    $raw = readTextFileSafe('/proc/uptime');
    if ($raw === null) { return null; }
    $parts = preg_split('/\s+/', $raw);
    return (!isset($parts[0]) || !is_numeric($parts[0])) ? null : (int) floor((float) $parts[0]);
}

function formatUptime(?int $seconds): string
{
    if ($seconds === null || $seconds < 0) { return 'unknown'; }
    $days = intdiv($seconds, 86400); $seconds %= 86400;
    $hours = intdiv($seconds, 3600); $seconds %= 3600;
    $minutes = intdiv($seconds, 60);
    $parts = [];
    if ($days > 0) { $parts[] = $days . 'd'; }
    if ($hours > 0) { $parts[] = $hours . 'h'; }
    $parts[] = $minutes . 'm';
    return implode(' ', $parts);
}

function readMemoryInfo(): array
{
    $result = ['total_mb' => null, 'available_mb' => null, 'used_mb' => null, 'used_percent' => null];
    $raw = readTextFileSafe('/proc/meminfo');
    if ($raw === null) { return $result; }
    $data = [];
    foreach (explode("\n", $raw) as $line) {
        if (preg_match('/^([A-Za-z_]+):\s+(\d+)\s+kB$/', trim($line), $matches)) {
            $data[$matches[1]] = (int) $matches[2];
        }
    }
    if (!isset($data['MemTotal'], $data['MemAvailable'])) { return $result; }
    $totalKb = $data['MemTotal']; $availableKb = $data['MemAvailable']; $usedKb = $totalKb - $availableKb;
    $result['total_mb'] = (int) round($totalKb / 1024);
    $result['available_mb'] = (int) round($availableKb / 1024);
    $result['used_mb'] = (int) round($usedKb / 1024);
    if ($totalKb > 0) { $result['used_percent'] = round(($usedKb / $totalKb) * 100, 1); }
    return $result;
}

function readLoadAverage(): ?string
{
    $raw = readTextFileSafe('/proc/loadavg');
    if ($raw === null) { return null; }
    $parts = preg_split('/\s+/', $raw);
    return (count($parts) < 3) ? null : $parts[0] . ' / ' . $parts[1] . ' / ' . $parts[2];
}

function httpJson(string $url, int $timeoutSeconds = 4): array
{
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_CONNECTTIMEOUT => $timeoutSeconds, CURLOPT_TIMEOUT => $timeoutSeconds,
        CURLOPT_HTTPHEADER => ['Accept: application/json'],
    ]);
    $start = microtime(true);
    $body = curl_exec($ch);
    $latencyMs = (int) round((microtime(true) - $start) * 1000);
    $errno = curl_errno($ch);
    $error = $errno !== 0 ? curl_error($ch) : null;
    $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);
    if ($errno !== 0) {
        return ['ok' => false, 'http_code' => $status, 'latency_ms' => $latencyMs, 'error' => $error, 'data' => null];
    }
    if ($body === false || $body === '') {
        return ['ok' => false, 'http_code' => $status, 'latency_ms' => $latencyMs, 'error' => 'Empty response body', 'data' => null];
    }
    $decoded = json_decode($body, true);
    if (!is_array($decoded)) {
        return ['ok' => false, 'http_code' => $status, 'latency_ms' => $latencyMs, 'error' => 'Invalid JSON response', 'data' => null];
    }
    return ['ok' => $status >= 200 && $status < 300, 'http_code' => $status, 'latency_ms' => $latencyMs, 'error' => null, 'data' => $decoded];
}

function extractModelName(?array $payload): ?string
{
    if ($payload === null) { return null; }
    if (isset($payload['data'][0]['id']) && is_string($payload['data'][0]['id'])) { return $payload['data'][0]['id']; }
    if (isset($payload['models'][0]['name']) && is_string($payload['models'][0]['name'])) { return $payload['models'][0]['name']; }
    return null;
}

function tcpReachable(string $host, int $port, float $timeoutSeconds = 2.0): array
{
    $errno = 0; $errstr = '';
    $start = microtime(true);
    $fp = @fsockopen($host, $port, $errno, $errstr, $timeoutSeconds);
    $latencyMs = (int) round((microtime(true) - $start) * 1000);
    if (is_resource($fp)) { fclose($fp); return ['ok' => true, 'latency_ms' => $latencyMs, 'error' => null]; }
    return ['ok' => false, 'latency_ms' => $latencyMs, 'error' => trim($errstr) !== '' ? $errstr : 'Connection failed'];
}

$kuzaiModels = httpJson($config['nodes']['kuzai']['models_endpoint']);
$darkaiModels = httpJson($config['nodes']['darkai']['models_endpoint']);
$darkaiTcp = tcpReachable($config['nodes']['darkai']['ip'], 8080);
$memory = readMemoryInfo();
$uptimeSeconds = readUptimeSeconds();

$response = [
    'app' => [
        'name' => $config['app_name'],
        'timestamp' => date('Y-m-d H:i:s'),
        'php_version' => PHP_VERSION,
        'apache_hint' => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
    ],
    'system' => [
        'hostname' => readHostname(),
        'server_ip' => $_SERVER['SERVER_ADDR'] ?? $config['nodes']['kuzai']['ip'],
        'load_average' => readLoadAverage(),
        'uptime' => formatUptime($uptimeSeconds),
        'memory' => $memory,
    ],
    'nodes' => [
        'kuzai' => [
            'label' => $config['nodes']['kuzai']['label'],
            'host' => $config['nodes']['kuzai']['host'],
            'ip' => $config['nodes']['kuzai']['ip'],
            'reachable' => $kuzaiModels['ok'],
            'http_code' => $kuzaiModels['http_code'],
            'latency_ms' => $kuzaiModels['latency_ms'],
            'model_name' => extractModelName($kuzaiModels['data']),
            'error' => $kuzaiModels['error'],
        ],
        'darkai' => [
            'label' => $config['nodes']['darkai']['label'],
            'host' => $config['nodes']['darkai']['host'],
            'ip' => $config['nodes']['darkai']['ip'],
            'reachable' => $darkaiModels['ok'],
            'http_code' => $darkaiModels['http_code'],
            'latency_ms' => $darkaiModels['latency_ms'],
            'model_name' => extractModelName($darkaiModels['data']),
            'error' => $darkaiModels['error'],
            'tcp_8080' => $darkaiTcp,
        ],
    ],
    'checks' => [
        'web_php' => true,
        'kuzai_models_api' => $kuzaiModels['ok'],
        'darkai_models_api' => $darkaiModels['ok'],
        'fhc2_to_fhc_tcp_8080' => $darkaiTcp['ok'],
    ],
];

http_response_code(200);
echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
```
---
#### ``public/api/run-start.php``

Receives the opening prompt and selected orchestrator profile slug. Validates all paths, checks that no run is already active via `/proc/<PID>`, then launches the Python orchestrator as a background process with `nohup`. Returns the PID and start time.

Validates the incoming JSON POST, checks that the Python binary and orchestrator profile exist, ensures no run is already active (via `/proc/<PID>`), launches the process with `nohup`, writes PID and metadata files.

```php
<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

function sanitizeSlug(string $value): string
{
    $value = strtolower(trim($value));
    $value = preg_replace('/[^a-z0-9._-]+/', '-', $value) ?? '';
    return trim($value, '-._');
}

$rawInput = file_get_contents('php://input');
$data = json_decode($rawInput ?: '', true);

if (!is_array($data)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid JSON body']);
    exit;
}

$openingPrompt = trim((string) ($data['opening_prompt'] ?? ''));
$orchestratorName = sanitizeSlug((string) ($data['orchestrator_name'] ?? ''));

if ($openingPrompt === '') {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Opening prompt is required']);
    exit;
}

if ($orchestratorName === '') {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Orchestrator name is required']);
    exit;
}

$pythonBin   = $config['orchestrator']['python_bin'];
$scriptPath  = $config['orchestrator']['script_path'];
$outputDir   = $config['orchestrator']['output_dir'];
$launcherDir = $config['orchestrator']['launcher_dir'];
$pidFile     = $config['orchestrator']['pid_file'];
$metaFile    = $config['orchestrator']['meta_file'];
$profileFile = $config['orchestrator']['profiles_dir'] . '/' . $orchestratorName . '.json';

foreach ([$launcherDir, $outputDir] as $dir) {
    if (!is_dir($dir) && !@mkdir($dir, 0775, true)) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'error' => 'Unable to create directory: ' . $dir]);
        exit;
    }
}

if (!is_executable($pythonBin)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Python binary not executable: ' . $pythonBin]);
    exit;
}

if (!is_file($scriptPath)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Engine not found: ' . $scriptPath]);
    exit;
}

if (!is_file($profileFile)) {
    http_response_code(404);
    echo json_encode(['ok' => false, 'error' => 'Orchestrator profile not found']);
    exit;
}

// Block concurrent runs
if (is_file($pidFile)) {
    $rawPid = trim((string) @file_get_contents($pidFile));
    if ($rawPid !== '' && ctype_digit($rawPid) && is_dir('/proc/' . $rawPid)) {
        http_response_code(409);
        echo json_encode(['ok' => false, 'error' => 'A run is already in progress', 'pid' => (int) $rawPid]);
        exit;
    }
}

$timestamp   = date('Ymd-His');
$stdoutFile  = $launcherDir . '/run-' . $timestamp . '.stdout.log';
$stderrFile  = $launcherDir . '/run-' . $timestamp . '.stderr.log';

$command = implode(' ', [
    'nohup',
    escapeshellarg($pythonBin),
    escapeshellarg($scriptPath),
    '--profile-file', escapeshellarg($profileFile),
    '--opening-prompt', escapeshellarg($openingPrompt),
    '--output-dir', escapeshellarg($outputDir),
    '>', escapeshellarg($stdoutFile),
    '2>', escapeshellarg($stderrFile),
    '& echo $!',
]);

$output = []; $returnCode = 0;
exec($command, $output, $returnCode);

$pid = null;
if (isset($output[0])) {
    $pidRaw = trim((string) $output[0]);
    if ($pidRaw !== '' && ctype_digit($pidRaw)) { $pid = (int) $pidRaw; }
}

if ($returnCode !== 0 || $pid === null || $pid < 1) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Unable to start process', 'return_code' => $returnCode]);
    exit;
}

@file_put_contents($pidFile, (string) $pid);

$meta = [
    'pid' => $pid, 'status' => 'running', 'started_at' => date('Y-m-d H:i:s'),
    'opening_prompt' => $openingPrompt, 'orchestrator_name' => $orchestratorName,
    'profile_file' => $profileFile, 'stdout_file' => $stdoutFile, 'stderr_file' => $stderrFile,
    'output_dir' => $outputDir,
];
@file_put_contents($metaFile, json_encode($meta, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

http_response_code(200);
echo json_encode(['ok' => true, 'message' => 'Run started', 'pid' => $pid,
    'started_at' => $meta['started_at'], 'orchestrator_name' => $orchestratorName]);
```
---
#### ``public/api/run-status.php``

Polled by the frontend every 5 seconds. Checks process liveness in `/proc`, reads the latest transcript from the most recent `run-ab-*` directory, and transitions the status machine (`running` → `completed` / `failed` / `stopped`). Returns the full transcript entries and log tails.

Checks `/proc/<PID>` for liveness. Reads `transcript.json` from the latest `run-ab-*` directory. Updates the meta file with the current state (`running`, `completed`, `stopped`, `failed`). Returns status, transcript entries, and stdout/stderr tails.

```php
<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

function readJsonFileSafe(string $path): ?array
{
    if (!is_file($path) || !is_readable($path)) { return null; }
    $raw = @file_get_contents($path);
    if ($raw === false || trim($raw) === '') { return null; }
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : null;
}

function writeJsonFileSafe(string $path, array $data): void
{
    @file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

function tailFileSafe(string $path, int $maxLines = 20): array
{
    if (!is_file($path) || !is_readable($path)) { return []; }
    $lines = @file($path, FILE_IGNORE_NEW_LINES);
    return !is_array($lines) ? [] : array_slice($lines, -$maxLines);
}

function findLatestRun(string $runsDir): ?array
{
    if (!is_dir($runsDir)) { return null; }
    $entries = scandir($runsDir);
    if (!is_array($entries)) { return null; }
    $dirs = [];
    foreach ($entries as $entry) {
        if ($entry === '.' || $entry === '..') { continue; }
        $fullPath = $runsDir . '/' . $entry;
        if (is_dir($fullPath) && str_starts_with($entry, 'run-ab-')) {
            $dirs[] = ['name' => $entry, 'path' => $fullPath, 'mtime' => @filemtime($fullPath) ?: 0];
        }
    }
    if ($dirs === []) { return null; }
    usort($dirs, static fn(array $a, array $b): int => $b['mtime'] <=> $a['mtime']);
    return $dirs[0];
}

function readTranscriptEntries(string $runDir): array
{
    $decoded = readJsonFileSafe($runDir . '/transcript.json');
    if (!is_array($decoded)) { return []; }
    $entries = [];
    foreach ($decoded as $item) {
        if (!is_array($item)) { continue; }
        $entries[] = [
            'turn' => isset($item['turn']) ? (int) $item['turn'] : 0,
            'speaker' => (string) ($item['speaker'] ?? ''),
            'content' => (string) ($item['content'] ?? ''),
            'timestamp' => (string) ($item['timestamp'] ?? ''),
        ];
    }
    return $entries;
}

$pidFile  = $config['orchestrator']['pid_file'];
$metaFile = $config['orchestrator']['meta_file'];
$runsDir  = $config['orchestrator']['output_dir'];

$meta = readJsonFileSafe($metaFile);
$latestRun = findLatestRun($runsDir);

$pid = null;
if (is_file($pidFile)) {
    $rawPid = trim((string) @file_get_contents($pidFile));
    if ($rawPid !== '' && ctype_digit($rawPid)) { $pid = (int) $rawPid; }
}

$isRunning = $pid !== null && $pid > 0 && is_dir('/proc/' . $pid);
$transcript = [];
$latestRunInfo = null;

if ($latestRun !== null) {
    $transcript = readTranscriptEntries($latestRun['path']);
    $latestRunInfo = [
        'name' => $latestRun['name'], 'path' => $latestRun['path'],
        'mtime' => date('Y-m-d H:i:s', (int) $latestRun['mtime']),
        'transcript_json' => is_file($latestRun['path'] . '/transcript.json') ? $latestRun['path'] . '/transcript.json' : null,
        'transcript_md'   => is_file($latestRun['path'] . '/transcript.md')   ? $latestRun['path'] . '/transcript.md'   : null,
    ];
}

$stdoutTail = []; $stderrTail = [];
if ($meta !== null) {
    $stdoutTail = tailFileSafe((string) ($meta['stdout_file'] ?? ''), 30);
    $stderrTail = tailFileSafe((string) ($meta['stderr_file'] ?? ''), 30);
}

// Determine state
if ($isRunning) {
    $status = 'running'; $note = 'A Duo run is currently in progress.';
    if ($meta !== null && ($meta['status'] ?? '') !== 'running') {
        $meta['status'] = 'running'; writeJsonFileSafe($metaFile, $meta);
    }
} elseif ($meta !== null && $latestRunInfo !== null && count($transcript) > 0) {
    $status = 'completed'; $note = 'The last Duo run completed successfully.';
    @unlink($pidFile);
    $meta['status'] = 'completed';
    if (!isset($meta['completed_at'])) { $meta['completed_at'] = date('Y-m-d H:i:s'); }
    $meta['latest_run'] = $latestRunInfo['name']; writeJsonFileSafe($metaFile, $meta);
} elseif ($meta !== null && (($meta['status'] ?? '') === 'stopped')) {
    $status = 'stopped'; $note = 'The last Duo run was stopped manually.';
    @unlink($pidFile); writeJsonFileSafe($metaFile, $meta);
} elseif ($meta !== null && $stderrTail !== []) {
    $status = 'failed'; $note = 'The last run ended with an error.';
    @unlink($pidFile);
    $meta['status'] = 'failed';
    if (!isset($meta['completed_at'])) { $meta['completed_at'] = date('Y-m-d H:i:s'); }
    writeJsonFileSafe($metaFile, $meta);
} else {
    $status = 'idle'; $note = 'No run launched yet.';
}

http_response_code(200);
echo json_encode([
    'ok' => true, 'status' => $status, 'note' => $note, 'active' => $meta,
    'is_running' => $isRunning, 'pid' => $isRunning ? $pid : null,
    'latest_run' => $latestRunInfo, 'transcript' => $transcript,
    'stdout_tail' => $stdoutTail, 'stderr_tail' => $stderrTail,
    'timestamp' => date('Y-m-d H:i:s'),
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
```
---

#### ``public/api/run-stop.php``

Sends `SIGTERM` to the active PID and waits 300 ms. If the process is still alive, sends `SIGKILL`. Cleans up the PID file and updates the meta file with a `stopped` status and stop timestamp.

Sends `SIGTERM` to the PID. Waits 300 ms. If still alive, sends `SIGKILL`. Removes PID file and writes `stopped` status to meta file.

```php
<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

$pidFile  = $config['orchestrator']['pid_file'];
$metaFile = $config['orchestrator']['meta_file'];

$pid = null;
if (is_file($pidFile)) {
    $rawPid = trim((string) @file_get_contents($pidFile));
    if ($rawPid !== '' && ctype_digit($rawPid)) { $pid = (int) $rawPid; }
}

if ($pid === null || $pid < 1) {
    http_response_code(200);
    echo json_encode(['ok' => true, 'message' => 'No active run']);
    exit;
}

if (!is_dir('/proc/' . $pid)) {
    @unlink($pidFile);
    http_response_code(200);
    echo json_encode(['ok' => true, 'message' => 'Run already finished', 'pid' => $pid]);
    exit;
}

exec('kill ' . escapeshellarg((string) $pid), $output, $returnCode);
usleep(300000);
$stillRunning = is_dir('/proc/' . $pid);

if ($stillRunning) {
    exec('kill -9 ' . escapeshellarg((string) $pid));
    usleep(200000);
    $stillRunning = is_dir('/proc/' . $pid);
}

if ($stillRunning) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Unable to stop process', 'pid' => $pid]);
    exit;
}

@unlink($pidFile);

$meta = [];
if (is_file($metaFile) && is_readable($metaFile)) {
    $decoded = json_decode((string) @file_get_contents($metaFile), true);
    if (is_array($decoded)) { $meta = $decoded; }
}

$meta['status'] = 'stopped';
$meta['stopped_at'] = date('Y-m-d H:i:s');
$meta['stopped_pid'] = $pid;
@file_put_contents($metaFile, json_encode($meta, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

http_response_code(200);
echo json_encode(['ok' => true, 'message' => 'Run stopped', 'pid' => $pid]);
```
---
#### ``public/api/orchestrators-list.php``

Scans `storage/orchestrators/` for `.json` files and returns a sorted list of profile names, slugs, descriptions, and last-modified dates. Used by the frontend to populate the profile selector.

Scans the `storage/orchestrators/` directory for `.json` files. Returns name, slug, description, and last modified date for each profile, sorted alphabetically.

```php
<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

$profilesDir = $config['orchestrator']['profiles_dir'];

if (!is_dir($profilesDir)) { @mkdir($profilesDir, 0775, true); }

$items = [];
$files = glob($profilesDir . '/*.json') ?: [];

foreach ($files as $file) {
    $slug = basename($file, '.json');
    $raw = @file_get_contents($file);
    $decoded = is_string($raw) ? json_decode($raw, true) : null;
    $items[] = [
        'slug' => $slug,
        'name' => is_array($decoded) && isset($decoded['name']) ? (string) $decoded['name'] : $slug,
        'description' => is_array($decoded) && isset($decoded['description']) ? (string) $decoded['description'] : '',
        'updated_at' => date('Y-m-d H:i:s', (int) (@filemtime($file) ?: time())),
    ];
}

usort($items, static fn(array $a, array $b): int => strcasecmp($a['name'], $b['name']));

echo json_encode(['ok' => true, 'items' => $items, 'count' => count($items)],
    JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
```
---

#### ``public/api/orchestrator-read.php``

Loads a single orchestrator profile by slug from `storage/orchestrators/`. All fields are normalized and clamped to valid ranges before being returned. Returns 404 if the slug does not match any file.

Reads a profile JSON file by slug from `storage/orchestrators/`. Normalizes and validates all fields before returning. Returns 404 if not found.

```php
<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

function sanitizeSlug(string $value): string
{
    $value = strtolower(trim($value));
    $value = preg_replace('/[^a-z0-9._-]+/', '-', $value) ?? '';
    return trim($value, '-._');
}

function normalizeProfile(array $profile, string $slug): array
{
    return [
        'slug' => $slug,
        'name' => trim((string) ($profile['name'] ?? $slug)) !== '' ? trim((string) ($profile['name'] ?? $slug)) : $slug,
        'description' => trim((string) ($profile['description'] ?? '')),
        'run' => [
            'turns'         => max(1,  min(40,   (int)   ($profile['run']['turns']         ?? 6))),
            'max_lines'     => max(1,  min(20,   (int)   ($profile['run']['max_lines']     ?? 5))),
            'max_chars'     => max(50, min(4000, (int)   ($profile['run']['max_chars']     ?? 500))),
            'history_depth' => max(0,  min(20,   (int)   ($profile['run']['history_depth'] ?? 3))),
            'max_sentences' => max(1,  min(12,   (int)   ($profile['run']['max_sentences'] ?? 4))),
        ],
        'kuzai' => [
            'label'           => 'KUZAI',
            'system_prompt'   => (string) ($profile['kuzai']['system_prompt']   ?? 'You are KUZAI. Reply clearly and stay concise.'),
            'temperature'     => (float)  ($profile['kuzai']['temperature']     ?? 0.35),
            'top_p'           => (float)  ($profile['kuzai']['top_p']           ?? 0.95),
            'top_k'           => (int)    ($profile['kuzai']['top_k']           ?? 40),
            'max_tokens'      => (int)    ($profile['kuzai']['max_tokens']      ?? 300),
            'repeat_penalty'  => (float)  ($profile['kuzai']['repeat_penalty']  ?? 1.05),
        ],
        'darkai' => [
            'label'           => 'DARKAI',
            'system_prompt'   => (string) ($profile['darkai']['system_prompt']   ?? 'You are DARKAI. Reply clearly and stay concise.'),
            'temperature'     => (float)  ($profile['darkai']['temperature']     ?? 0.35),
            'top_p'           => (float)  ($profile['darkai']['top_p']           ?? 0.95),
            'top_k'           => (int)    ($profile['darkai']['top_k']           ?? 40),
            'max_tokens'      => (int)    ($profile['darkai']['max_tokens']      ?? 300),
            'repeat_penalty'  => (float)  ($profile['darkai']['repeat_penalty']  ?? 1.05),
        ],
    ];
}

$slug = sanitizeSlug((string) ($_GET['name'] ?? ''));

if ($slug === '') {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Missing orchestrator name']);
    exit;
}

$file = $config['orchestrator']['profiles_dir'] . '/' . $slug . '.json';

if (!is_file($file) || !is_readable($file)) {
    http_response_code(404);
    echo json_encode(['ok' => false, 'error' => 'Orchestrator not found']);
    exit;
}

$raw = @file_get_contents($file);
$decoded = is_string($raw) ? json_decode($raw, true) : null;

if (!is_array($decoded)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Invalid orchestrator file']);
    exit;
}

echo json_encode(['ok' => true, 'profile' => normalizeProfile($decoded, $slug)],
    JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
```
---

#### ``public/api/orchestrator-save.php``

Writes or overwrites an orchestrator profile JSON file in `storage/orchestrators/`. The slug is derived from the profile name by sanitization. All numeric fields are clamped to defined min/max ranges on write.

Accepts a POST with a `profile` JSON object. Sanitizes the slug, normalizes all fields (clamped ranges), writes the profile to `storage/orchestrators/<slug>.json`.

```php
<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

function sanitizeSlug(string $value): string
{
    $value = strtolower(trim($value));
    $value = preg_replace('/[^a-z0-9._-]+/', '-', $value) ?? '';
    return trim($value, '-._');
}

function normalizeProfile(array $profile, string $slug): array
{
    return [
        'slug' => $slug,
        'name' => trim((string) ($profile['name'] ?? $slug)) !== '' ? trim((string) ($profile['name'] ?? $slug)) : $slug,
        'description' => trim((string) ($profile['description'] ?? '')),
        'run' => [
            'turns'         => max(1,  min(40,   (int)   ($profile['run']['turns']         ?? 6))),
            'max_lines'     => max(1,  min(20,   (int)   ($profile['run']['max_lines']     ?? 5))),
            'max_chars'     => max(50, min(4000, (int)   ($profile['run']['max_chars']     ?? 500))),
            'history_depth' => max(0,  min(20,   (int)   ($profile['run']['history_depth'] ?? 3))),
            'max_sentences' => max(1,  min(12,   (int)   ($profile['run']['max_sentences'] ?? 4))),
        ],
        'kuzai' => [
            'label'          => 'KUZAI',
            'system_prompt'  => (string) ($profile['kuzai']['system_prompt']  ?? 'You are KUZAI. Reply clearly and stay concise.'),
            'temperature'    => (float)  ($profile['kuzai']['temperature']    ?? 0.35),
            'top_p'          => (float)  ($profile['kuzai']['top_p']          ?? 0.95),
            'top_k'          => (int)    ($profile['kuzai']['top_k']          ?? 40),
            'max_tokens'     => (int)    ($profile['kuzai']['max_tokens']     ?? 300),
            'repeat_penalty' => (float)  ($profile['kuzai']['repeat_penalty'] ?? 1.05),
        ],
        'darkai' => [
            'label'          => 'DARKAI',
            'system_prompt'  => (string) ($profile['darkai']['system_prompt']  ?? 'You are DARKAI. Reply clearly and stay concise.'),
            'temperature'    => (float)  ($profile['darkai']['temperature']    ?? 0.35),
            'top_p'          => (float)  ($profile['darkai']['top_p']          ?? 0.95),
            'top_k'          => (int)    ($profile['darkai']['top_k']          ?? 40),
            'max_tokens'     => (int)    ($profile['darkai']['max_tokens']     ?? 300),
            'repeat_penalty' => (float)  ($profile['darkai']['repeat_penalty'] ?? 1.05),
        ],
    ];
}

$raw = file_get_contents('php://input');
$data = json_decode($raw ?: '', true);

if (!is_array($data) || !isset($data['profile']) || !is_array($data['profile'])) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid JSON body']);
    exit;
}

$requestedName = (string) ($data['save_as_name'] ?? $data['profile']['slug'] ?? $data['profile']['name'] ?? '');
$slug = sanitizeSlug($requestedName);

if ($slug === '') {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Invalid orchestrator name']);
    exit;
}

$profilesDir = $config['orchestrator']['profiles_dir'];
if (!is_dir($profilesDir) && !@mkdir($profilesDir, 0775, true)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Unable to create orchestrator directory']);
    exit;
}

$profile = normalizeProfile($data['profile'], $slug);
$file = $profilesDir . '/' . $slug . '.json';
$written = @file_put_contents($file, json_encode($profile, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n");

if ($written === false) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Unable to write orchestrator file']);
    exit;
}

echo json_encode(['ok' => true, 'message' => 'Orchestrator saved', 'slug' => $slug, 'profile' => $profile],
    JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
```
---

#### ``public/assets/js/app.js``

Self-contained IIFE, no framework. Initializes on page load, binds all button events, and starts a polling loop calling `status.php` and `run-status.php` every 5 seconds. Handles the full profile load/save/save-as cycle and renders transcript entries into the live panel.

Frontend controller — IIFE, no framework. Polls `status.php` and `run-status.php` every 5 seconds. Handles load/save/save-as for orchestrator profiles. Manages start/stop/reset run buttons. Renders transcript entries and system messages into `#transcript-live`.

```javascript
(function () {
    "use strict";

    const cfg = window.KUZCHAT_CONFIG || {
        pollIntervalMs: 5000,
        statusUrl: "/api/status.php",
        runStartUrl: "/api/run-start.php",
        runStatusUrl: "/api/run-status.php",
        runStopUrl: "/api/run-stop.php",
        orchestratorListUrl: "/api/orchestrators-list.php",
        orchestratorReadUrl: "/api/orchestrator-read.php",
        orchestratorSaveUrl: "/api/orchestrator-save.php"
    };

    let currentOrchestratorSlug = null;
    let runInterfaceReset = false;

    function byId(id) { return document.getElementById(id); }
    function setText(id, value) { const el = byId(id); if (el) el.textContent = value; }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
    }

    function setBadge(id, ok) {
        const el = byId(id);
        if (!el) return;
        el.textContent = ok ? "ONLINE" : "OFFLINE";
        el.classList.remove("node-badge--ok", "node-badge--down");
        el.classList.add(ok ? "node-badge--ok" : "node-badge--down");
    }

    function setGlobalStatus(allOk) {
        const text = byId("global-status-text");
        const pill = byId("global-status-pill");
        if (!text || !pill) return;
        text.textContent = allOk ? "READY" : "DEGRADED";
        pill.classList.remove("status-pill--ok", "status-pill--down");
        pill.classList.add(allOk ? "status-pill--ok" : "status-pill--down");
    }

    function applyRunState(state, labelOverride = null) {
        const stateText = byId("run-state");
        const statePill = byId("run-state-pill");
        if (!stateText || !statePill) return;
        const normalized = String(state || "idle").toLowerCase();
        const labels = {
            ready: "READY", idle: "IDLE", running: "RUNNING", completed: "COMPLETED",
            stopped: "STOPPED", error: "ERROR", starting: "STARTING", stopping: "STOPPING",
            reset: "READY FOR NEW RUN", finished: "FINISHED", failed: "FAILED"
        };
        const cssClass = {
            ready: "state-ready", idle: "state-idle", running: "state-running",
            completed: "state-completed", stopped: "state-stopped", error: "state-error",
            starting: "state-running", stopping: "state-stopped", reset: "state-ready",
            finished: "state-completed", failed: "state-error"
        };
        const finalLabel = labelOverride || labels[normalized] || normalized.toUpperCase();
        stateText.textContent = finalLabel;
        statePill.textContent = finalLabel;
        statePill.className = "run-state-pill";
        statePill.classList.add(cssClass[normalized] || "state-idle");
    }

    function renderSystemTranscript(message) {
        const container = byId("transcript-live");
        if (!container) return;
        container.innerHTML = `
            <div class="message-card message-card--kuzai">
                <div class="message-card__meta"><span class="message-card__speaker">SYSTEM</span></div>
                <div class="message-card__body">${escapeHtml(message)}</div>
            </div>`;
    }

    function renderTranscript(entries, stdoutTail, status, note) {
        const container = byId("transcript-live");
        if (!container) return;
        if (entries.length === 0 && stdoutTail.length === 0) {
            const msg = (status === 'running')
                ? 'Run in progress. Waiting for first response...'
                : (note || 'No transcript available yet.');
            renderSystemTranscript(msg);
            return;
        }
        const html = entries.map(entry => {
            const isKuzai = String(entry.speaker).toUpperCase().includes('KUZAI');
            const cssClass = isKuzai ? 'message-card--kuzai' : 'message-card--darkai';
            return `
                <div class="message-card ${cssClass}">
                    <div class="message-card__meta">
                        <span class="message-card__speaker">${escapeHtml(entry.speaker)}</span>
                        <span class="message-card__time">${escapeHtml(entry.timestamp)}</span>
                    </div>
                    <div class="message-card__body">${escapeHtml(entry.content)}</div>
                </div>`;
        }).join('');
        container.innerHTML = html || '';
    }

    function updateRunButtons(isRunning, isStarting, isStopping) {
        const startBtn = byId("start-run-btn");
        const stopBtn  = byId("stop-run-btn");
        const resetBtn = byId("reset-run-btn");
        if (startBtn) {
            startBtn.disabled = isRunning || isStarting || isStopping;
            startBtn.textContent = isStarting ? "STARTING..." : "START RUN";
        }
        if (stopBtn) {
            stopBtn.disabled = !isRunning || isStarting || isStopping;
            stopBtn.textContent = isStopping ? "STOPPING..." : "STOP";
        }
        if (resetBtn) {
            resetBtn.disabled = isRunning || isStarting || isStopping;
            resetBtn.textContent = "RELOAD";
        }
    }

    function syncSelectedOrchestratorDisplay(value) {
        const finalValue = value || currentOrchestratorSlug || "--";
        setText("run-orchestrator", finalValue);
        setText("run-orchestrator-inline", finalValue);
    }

    function resetRunInterface() {
        runInterfaceReset = true;
        updateRunButtons(false, false, false);
        applyRunState("reset");
        setText("run-pid", "--");
        setText("run-started", "--");
        syncSelectedOrchestratorDisplay(byId("orchestrator_select")?.value || currentOrchestratorSlug || "--");
        setText("run-note", "Interface reset. Ready for a new run.");
        renderSystemTranscript("Interface reset. Ready for a new run.");
    }

    function fillProfileForm(profile) {
        currentOrchestratorSlug = profile.slug || null;
        const select = byId("orchestrator_select");
        if (select && profile.slug) select.value = profile.slug;
        byId("profile_name").value        = profile.name        || profile.slug || "";
        byId("profile_slug").value        = profile.slug        || "";
        byId("profile_description").value = profile.description || "";
        byId("profile_turns").value        = profile.run?.turns         ?? 6;
        byId("profile_max_lines").value    = profile.run?.max_lines     ?? 5;
        byId("profile_max_chars").value    = profile.run?.max_chars     ?? 500;
        byId("profile_history_depth").value= profile.run?.history_depth ?? 3;
        byId("kuzai_system_prompt").value  = profile.kuzai?.system_prompt  ?? "";
        byId("kuzai_temperature").value    = profile.kuzai?.temperature    ?? 0.35;
        byId("kuzai_top_p").value          = profile.kuzai?.top_p          ?? 0.95;
        byId("kuzai_top_k").value          = profile.kuzai?.top_k          ?? 40;
        byId("kuzai_max_tokens").value     = profile.kuzai?.max_tokens     ?? 300;
        byId("kuzai_repeat_penalty").value = profile.kuzai?.repeat_penalty ?? 1.05;
        byId("darkai_system_prompt").value  = profile.darkai?.system_prompt  ?? "";
        byId("darkai_temperature").value    = profile.darkai?.temperature    ?? 0.35;
        byId("darkai_top_p").value          = profile.darkai?.top_p          ?? 0.95;
        byId("darkai_top_k").value          = profile.darkai?.top_k          ?? 40;
        byId("darkai_max_tokens").value     = profile.darkai?.max_tokens     ?? 300;
        byId("darkai_repeat_penalty").value = profile.darkai?.repeat_penalty ?? 1.05;
        if (runInterfaceReset) syncSelectedOrchestratorDisplay(profile.slug || "--");
    }

    async function loadStatus() {
        try {
            const response = await fetch(cfg.statusUrl, { cache: "no-store" });
            const data = await response.json();
            const checks = data.checks || {};
            const allOk = checks.kuzai_models_api && checks.darkai_models_api;
            setGlobalStatus(allOk);
            setBadge("badge-kuzai",  Boolean(checks.kuzai_models_api));
            setBadge("badge-darkai", Boolean(checks.darkai_models_api));
            setText("kuzai-model",   data.nodes?.kuzai?.model_name  || "--");
            setText("darkai-model",  data.nodes?.darkai?.model_name || "--");
            setText("kuzai-http",    String(data.nodes?.kuzai?.http_code  ?? "--"));
            setText("darkai-http",   String(data.nodes?.darkai?.http_code ?? "--"));
            setText("kuzai-latency",  (data.nodes?.kuzai?.latency_ms  != null) ? data.nodes.kuzai.latency_ms  + " ms" : "--");
            setText("darkai-latency", (data.nodes?.darkai?.latency_ms != null) ? data.nodes.darkai.latency_ms + " ms" : "--");
            setText("engine-status", allOk ? "ONLINE" : "DEGRADED");
            setText("web-status",    "ONLINE");
            setText("last-update",   data.app?.timestamp || "--");
        } catch (error) {
            setGlobalStatus(false);
            setBadge("badge-kuzai",  false);
            setBadge("badge-darkai", false);
            setText("engine-status", "ERROR");
        }
    }

    async function loadOrchestratorList() {
        try {
            const response = await fetch(cfg.orchestratorListUrl, { cache: "no-store" });
            const data = await response.json();
            if (!data.ok || !Array.isArray(data.items)) return [];
            const select = byId("orchestrator_select");
            if (select) {
                select.innerHTML = data.items.map(item =>
                    `<option value="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</option>`
                ).join('');
            }
            return data.items;
        } catch { return []; }
    }

    async function loadOrchestrator(slug) {
        try {
            const response = await fetch(cfg.orchestratorReadUrl + '?name=' + encodeURIComponent(slug), { cache: "no-store" });
            const data = await response.json();
            if (!data.ok || !data.profile) throw new Error(data.error || "Load failed");
            fillProfileForm(data.profile);
            setText("profile-note", "Orchestrator '" + data.profile.name + "' loaded.");
        } catch (error) {
            setText("profile-note", "Load failed: " + error.message);
        }
    }

    async function saveOrchestrator(saveAs = false) {
        const profile = {
            slug: byId("profile_slug")?.value?.trim() || "",
            name: byId("profile_name")?.value?.trim() || "Default",
            description: byId("profile_description")?.value?.trim() || "",
            run: {
                turns:         parseInt(byId("profile_turns")?.value) || 6,
                max_lines:     parseInt(byId("profile_max_lines")?.value) || 5,
                max_chars:     parseInt(byId("profile_max_chars")?.value) || 500,
                history_depth: parseInt(byId("profile_history_depth")?.value) || 3,
            },
            kuzai: {
                system_prompt:  byId("kuzai_system_prompt")?.value  || "",
                temperature:    parseFloat(byId("kuzai_temperature")?.value)    || 0.35,
                top_p:          parseFloat(byId("kuzai_top_p")?.value)          || 0.95,
                top_k:          parseInt(byId("kuzai_top_k")?.value)            || 40,
                max_tokens:     parseInt(byId("kuzai_max_tokens")?.value)       || 300,
                repeat_penalty: parseFloat(byId("kuzai_repeat_penalty")?.value) || 1.05,
            },
            darkai: {
                system_prompt:  byId("darkai_system_prompt")?.value  || "",
                temperature:    parseFloat(byId("darkai_temperature")?.value)    || 0.35,
                top_p:          parseFloat(byId("darkai_top_p")?.value)          || 0.95,
                top_k:          parseInt(byId("darkai_top_k")?.value)            || 40,
                max_tokens:     parseInt(byId("darkai_max_tokens")?.value)       || 300,
                repeat_penalty: parseFloat(byId("darkai_repeat_penalty")?.value) || 1.05,
            },
        };

        let saveAsName = profile.slug;
        if (saveAs) {
            const input = prompt("Save as (slug name):", profile.slug || "");
            if (!input) return null;
            saveAsName = input.trim();
        }

        const response = await fetch(cfg.orchestratorSaveUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ profile, save_as_name: saveAsName })
        });

        const data = await response.json();
        if (!data.ok) throw new Error(data.error || "Save failed");

        currentOrchestratorSlug = data.slug;
        await loadOrchestratorList();
        const select = byId("orchestrator_select");
        if (select && data.slug) select.value = data.slug;
        setText("profile-note", "Saved as '" + data.slug + "'.");
        return data.profile || { slug: data.slug };
    }

    async function loadRunStatus() {
        try {
            const response = await fetch(cfg.runStatusUrl, { cache: "no-store" });
            const data = await response.json();
            const isRunning = Boolean(data.is_running);
            if (isRunning) runInterfaceReset = false;
            if (!isRunning && runInterfaceReset) {
                updateRunButtons(false, false, false);
                applyRunState("reset");
                return;
            }
            updateRunButtons(isRunning, false, false);
            applyRunState(data.status || "idle");
            setText("run-pid",     data.pid ? String(data.pid) : "--");
            setText("run-started", data.active?.started_at || "--");
            syncSelectedOrchestratorDisplay(data.active?.orchestrator_name || byId("orchestrator_select")?.value || "--");
            setText("run-note", data.note || "No run status available.");
            renderTranscript(data.transcript || [], data.stdout_tail || [], data.status || "idle", data.note || "");
        } catch (error) {
            updateRunButtons(false, false, false);
            applyRunState("error");
            setText("run-note", "Run status error: " + error.message);
            renderSystemTranscript("Run status error: " + error.message);
        }
    }

    async function startRun() {
        const openingPrompt = byId("opening_prompt")?.value?.trim() || "";
        if (!openingPrompt) { setText("run-note", "Opening prompt is required."); return; }
        runInterfaceReset = false;
        updateRunButtons(false, true, false);
        applyRunState("starting");
        setText("run-note", "Saving orchestrator and starting run...");
        renderSystemTranscript("Starting new run...");
        try {
            const savedProfile = await saveOrchestrator(false);
            if (!savedProfile || !savedProfile.slug) throw new Error("Unable to save orchestrator.");
            const response = await fetch(cfg.runStartUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ opening_prompt: openingPrompt, orchestrator_name: savedProfile.slug })
            });
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.error || "HTTP " + response.status);
            syncSelectedOrchestratorDisplay(data.orchestrator_name || savedProfile.slug);
            setText("run-note", "Run started — PID " + data.pid + ".");
            await loadRunStatus();
        } catch (error) {
            updateRunButtons(false, false, false);
            applyRunState("error");
            setText("run-note", "Start failed: " + error.message);
            renderSystemTranscript("Start failed: " + error.message);
        }
    }

    async function stopRun() {
        updateRunButtons(true, false, true);
        applyRunState("stopping");
        setText("run-note", "Stopping run...");
        try {
            const response = await fetch(cfg.runStopUrl, { method: "POST" });
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.error || "HTTP " + response.status);
            setText("run-note", data.message || "Run stopped.");
            await loadRunStatus();
        } catch (error) {
            updateRunButtons(false, false, false);
            applyRunState("error");
            setText("run-note", "Stop failed: " + error.message);
        }
    }

    function initEvents() {
        const loadBtn   = byId("orchestrator_load_btn");
        const saveBtn   = byId("orchestrator_save_btn");
        const saveAsBtn = byId("orchestrator_save_as_btn");
        const startBtn  = byId("start-run-btn");
        const stopBtn   = byId("stop-run-btn");
        const resetBtn  = byId("reset-run-btn");
        const select    = byId("orchestrator_select");

        if (loadBtn)   loadBtn.addEventListener("click",  async () => { const slug = byId("orchestrator_select")?.value; if (slug) await loadOrchestrator(slug); });
        if (saveBtn)   saveBtn.addEventListener("click",  async () => { await saveOrchestrator(false); });
        if (saveAsBtn) saveAsBtn.addEventListener("click",async () => { await saveOrchestrator(true);  });
        if (startBtn)  startBtn.addEventListener("click", startRun);
        if (stopBtn)   stopBtn.addEventListener("click",  stopRun);
        if (resetBtn)  resetBtn.addEventListener("click", resetRunInterface);
        if (select) {
            select.addEventListener("change", async () => {
                const slug = select.value;
                if (slug) { await loadOrchestrator(slug); syncSelectedOrchestratorDisplay(slug); }
            });
        }
    }

    async function init() {
        initEvents();
        const items = await loadOrchestratorList();
        if (items.length > 0) { await loadOrchestrator(items[0].slug); syncSelectedOrchestratorDisplay(items[0].slug); }
        else { setText("profile-note", "No orchestrator profile found. Save the current editor as a new profile."); }
        await loadStatus();
        await loadRunStatus();
        window.setInterval(() => { loadStatus(); loadRunStatus(); }, cfg.pollIntervalMs);
    }

    init().catch((error) => {
        setText("profile-note", "Initialization failed: " + error.message);
        setText("run-note",     "Initialization failed: " + error.message);
        applyRunState("error");
    });
})();
```
---

#### ``public/assets/css/style.css``

Dark neon-blue theme built entirely with CSS custom properties. No framework dependency.  
Color ramps, border styles, and component states are all defined on `:root` and applied consistently across node cards, run state badges, and transcript message cards.

Dark neon-blue theme. CSS custom properties on `:root`. No framework dependency.

```css
:root {
    --bg-1: #06162c;
    --bg-2: #0c2344;
    --bg-3: #12325f;
    --card-bg: rgba(17, 39, 74, 0.88);
    --card-bg-2: rgba(12, 30, 58, 0.94);
    --text-main: #ffffff;
    --text-soft: #eaf4ff;
    --text-dim: #b8d3f6;
    --neon-cyan: #7bf2ff;
    --neon-blue: #8fc4ff;
    --neon-violet: #c19cff;
    --neon-white: #fbfdff;
    --success: #67f3ba;
    --danger: #ff7b9d;
    --warning: #ffd97c;
    --info: #9fd6ff;
    --border-main: rgba(159, 214, 255, 0.26);
    --border-strong: rgba(123, 242, 255, 0.42);
    --shadow-main: 0 18px 50px rgba(0, 0, 0, 0.28);
    --shadow-neon: 0 0 18px rgba(123, 242, 255, 0.16);
    --radius-xl: 22px;
    --radius-lg: 16px;
    --radius-md: 12px;
}

/* ... full stylesheet — see public/assets/css/style.css */

html, body { margin: 0; padding: 0; min-height: 100%;
    font-family: "Segoe UI", "Inter", "Arial", sans-serif;
    background: radial-gradient(circle at top left, rgba(110, 180, 255, 0.24), transparent 28%),
        radial-gradient(circle at top right, rgba(165, 115, 255, 0.18), transparent 24%),
        linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 46%, var(--bg-3) 100%);
    color: var(--text-main); }

.app-shell { width: min(1680px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 40px; }

.topbar { display: flex; justify-content: space-between; align-items: center; gap: 24px;
    margin-bottom: 24px; padding: 18px 22px;
    border: 1px solid rgba(159, 214, 255, 0.24); border-radius: var(--radius-xl);
    background: rgba(10, 29, 58, 0.9); box-shadow: var(--shadow-main); backdrop-filter: blur(14px); }

.status-pill { display: inline-flex; align-items: center; gap: 10px; padding: 12px 16px;
    border-radius: 999px; border: 1px solid rgba(103, 243, 186, 0.38);
    background: rgba(16, 64, 53, 0.34); color: #e2fff5; font-weight: 700; }

.status-pill--down { border-color: rgba(255, 123, 157, 0.38); background: rgba(82, 18, 38, 0.34); color: #ffe7ee; }

.node-card, .panel, .editor-box { border: 1px solid var(--border-main); border-radius: var(--radius-xl);
    background: var(--card-bg); box-shadow: var(--shadow-main); backdrop-filter: blur(12px); padding: 22px; }

.node-card--kuzai  { border-color: rgba(123, 242, 255, 0.28); }
.node-card--darkai { border-color: rgba(193, 156, 255, 0.28); }

.node-badge--ok   { border-color: rgba(103, 243, 186, 0.36); color: #dffdf2; background: rgba(16, 64, 53, 0.32); }
.node-badge--down { border-color: rgba(255, 123, 157, 0.36); color: #ffe7ee; background: rgba(82, 18, 38, 0.32); }

.run-state-badge--running   { border-color: rgba(159, 214, 255, 0.36); background: rgba(26, 56, 92, 0.36); }
.run-state-badge--completed { border-color: rgba(103, 243, 186, 0.36); background: rgba(16, 64, 53, 0.32); }
.run-state-badge--stopped   { border-color: rgba(255, 217, 124, 0.38); background: rgba(83, 61, 13, 0.34); }
.run-state-badge--error     { border-color: rgba(255, 123, 157, 0.38); background: rgba(82, 18, 38, 0.34); }

.message-card--kuzai  { border-color: rgba(123, 242, 255, 0.24); }
.message-card--darkai { border-color: rgba(193, 156, 255, 0.24); }

.message-card__speaker { color: var(--neon-cyan); font-weight: 800; }
.message-card--darkai .message-card__speaker { color: var(--neon-violet); }

.btn--primary { background: linear-gradient(135deg, var(--neon-cyan), var(--neon-blue));
    color: #031124; box-shadow: 0 10px 28px rgba(123, 242, 255, 0.2); }
.btn:hover { transform: translateY(-1px); }
.btn:disabled { opacity: 0.55; cursor: not-allowed; transform: none; }

@media (max-width: 780px) {
    .topbar { flex-direction: column; }
    .two-col-grid, .hero-stats, .node-metrics { grid-template-columns: 1fr; }
    .btn { width: 100%; }
}
```

---

#### ``SYSTEM DIRECTORY LAYOUT``

Complete reference of all paths used by the project across both nodes.  
Covers llama.cpp binaries, model files, orchestrator scripts, web application files, persistent storage, systemd services, and CUDA installation.


```
/opt/src/llama.cpp/                               llama.cpp source tree
/opt/src/llama.cpp/build/bin/llama-server         inference server binary
/opt/src/llama.cpp/build/bin/llama-cli            CLI test binary

/opt/llm/models/                                  GGUF model files
/opt/llm/orchestrator/                            Python scripts
/opt/llm/orchestrator/venv/                       Python virtualenv
/opt/llm/orchestrator/runs/run-ab-YYYYMMDD/       session transcripts
/opt/llm/orchestrator/runs/run-ab-YYYYMMDD/transcript.json
/opt/llm/orchestrator/runs/run-ab-YYYYMMDD/transcript.md

/var/www/html/KUZCHAT-LLM-DUO/public/             PHP web application
/var/www/html/KUZCHAT-LLM-DUO/public/api/         PHP API endpoints
/var/www/html/KUZCHAT-LLM-DUO/public/assets/css/  style.css
/var/www/html/KUZCHAT-LLM-DUO/public/assets/js/   app.js
/var/www/html/KUZCHAT-LLM-DUO/app/config.php      central config
/var/www/html/KUZCHAT-LLM-DUO/storage/orchestrators/  profiles JSON
/var/www/html/KUZCHAT-LLM-DUO/storage/runs/       run transcripts
/var/www/html/KUZCHAT-LLM-DUO/storage/launcher/   PID + meta files

/var/log/llm-duo/                                 service logs

/etc/systemd/system/llama-server-a.service        KUZAI service (fhc2)
/etc/systemd/system/llama-server-b.service        DARKAI service (fhc)

/usr/local/cuda/                                  CUDA toolkit
/etc/profile.d/cuda.sh                            PATH + LD_LIBRARY_PATH exports
```

---
#### ``DEPLOYED MODEL``

Two distinct models are deployed, one per node.  
The model choice on each node is constrained by available VRAM. Both use Q4_K_M quantization which offers a good balance between inference speed and output quality on consumer-grade GPUs.


| Parameter | Value |
|---|---|
| Name | `bartowski_Mistral-7B-Instruct-v0.3-GGUF_Mistral-7B-Instruct-v0.3-Q4_K_M.gguf` |
| Family | Mistral 7B Instruct |
| Quantization | Q4_K_M |
| Prompt perf. | - |
| Generation perf. | - |
| Node | fhc2 (KUZAI) - RTX 5060 8 GB VRAM |

| Parameter | Value |
|---|---|
| Name | `bartowski/granite-3.1-3b-a800m-instruct-Q4_K_M.gguf` |
| Family | IBM Granite 3.1 - 3B parameters |
| Quantization | Q4_K_M |
| Prompt perf. | 307 t/s |
| Generation perf. | 136 t/s |
| Node | fhc (DARKAI) - RTX 3050 4 GB VRAM |

---
#### ``REPOSITORY DIRECTORY``

Complete list of all files and directories in the repository. Each entry maps directly to a component of the deployed system.


| File | Description |
|---|---|
| `ORCHESTRATOR-01.py` | Generic orchestrator - all URLs required via CLI |
| `ORCHESTRATOR-02.py` | Production orchestrator - fhc/fhc2 IPs hardcoded as defaults |
| `kuzchat-llm-duo.conf` | Apache VirtualHost config |
| `MONITOR-FHC.sh` | Full Node B audit |
| `MONITOR-FHC2.sh` | Full Node A audit + Python venv check |
| `VERIF-CON-KUZAI-DARKAI.sh` | Inter-node connectivity and API test |
| `LLM-DUO-RUN-AWAY-#02.md` | Deployment journal phase 2 |
| `LLM-DUO-RUN-AWAY-#03.md` | Deployment journal phase 3 - full Node B setup |
| `app/config.php` | Central application configuration |
| `public/index.php` | Main HTML shell |
| `public/api/status.php` | System + node health endpoint |
| `public/api/run-start.php` | Launch orchestrator process |
| `public/api/run-status.php` | Poll run state + transcript |
| `public/api/run-stop.php` | Stop running process |
| `public/api/orchestrators-list.php` | List saved profiles |
| `public/api/orchestrator-read.php` | Read profile by slug |
| `public/api/orchestrator-save.php` | Create or update profile |
| `public/assets/css/style.css` | Dark neon-blue theme |
| `public/assets/js/app.js` | Frontend controller |
| `storage/` | PHP persistent data |

---

##### ``KUSANAGI8200 - THE KUZ NETWORK - @2026``
