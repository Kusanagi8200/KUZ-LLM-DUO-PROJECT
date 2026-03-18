#### LLM - DUO - RUN AWAY - #02

####  WHAT'S INSIDE THE BLACK BOX ? 

___________________________________________________________________________________________________________________
####  INSTALLING THE FIRST MACHINE - FHC2 / KUZAI NODE

The first node of the LLM Duo project was installed and prepared as a dedicated local inference machine for THE KUZ NETWORK lab. 
The goal of this phase was not only to get a model running, but to turn the machine into a clean, reproducible, headless Linux node ready to host 
a local open-source LLM and later integrate into a two-node orchestration workflow.

___________________________________________________________________________________________________________________
#### 1/ HARDWARE CHECK

The machine used for this first node is FHC2, an Acer Nitro ANV15-52 running Ubuntu 24.04.4 LTS with kernel 6.17.0-19-generic.
It is equipped with an Intel Core i9-13900H, 32 GiB of RAM, and an NVIDIA RTX 5060 Laptop GPU. 
Storage is provided by a 1 TB Kingston NVMe drive, with the system currently installed on a single main ext4 partition. The machine boots in UEFI mode.

```
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

echo "===== DISKS / PARTITIONS ====="
lsblk -e7 -o NAME,SIZE,TYPE,FSTYPE,FSUSE%,MOUNTPOINTS,MODEL
blkid
df -hT

echo "===== BOOT MODE ====="
[ -d /sys/firmware/efi ] && echo UEFI || echo BIOS

echo "===== NETWORK ====="
ip -br a
ip r

echo "===== INSTALLED DESKTOP / DISPLAY STACK ====="
dpkg -l | egrep 'ubuntu-desktop|gnome-shell|gdm3|xorg|wayland|lightdm|sddm|network-manager'

echo "===== NVIDIA / NOUVEAU / CUDA ====="
dpkg -l | egrep 'nvidia|cuda|nouveau'
lsmod | egrep 'nvidia|nouveau'

lsblk -f
df -hT
blkid /dev/nvme0n1p2 /dev/nvme0n1p3 /dev/nvme0n1p4
```

___________________________________________________________________________________________________________________
#### 2/ SYSTEM CLEANUP

The initial Ubuntu Desktop installation was converted into a server-style node. 
The graphical stack was disabled by switching the default target to multi-user.target, and the machine was kept reachable over SSH and Wi-Fi through NetworkManager. 
The purpose of this step was to remove the desktop overhead and keep only the components required for remote administration, networking, NVIDIA support, and local inference.

```
systemctl set-default multi-user.target
systemctl disable gdm3.service
reboot

systemctl get-default
systemctl is-enabled gdm3 || true
nmcli general status
ip -br a
nvidia-smi

apt-mark manual \
  openssh-server \
  network-manager \
  wpasupplicant \
  netplan.io \
  nvidia-driver-580-open \
  nvidia-utils-580 \
  nvidia-compute-utils-580 \
  linux-modules-nvidia-580-open-generic-hwe-24.04

apt -s purge \
  ubuntu-desktop-minimal \
  gdm3 \
  gnome-shell \
  gnome-shell-common \
  gnome-shell-extension-appindicator \
  gnome-shell-extension-desktop-icons-ng \
  gnome-shell-extension-ubuntu-dock \
  gnome-shell-extension-ubuntu-tiling-assistant \
  xorg \
  xserver-xorg \
  xserver-xorg-core \
  xserver-xorg-input-all \
  xserver-xorg-video-all \
  xwayland \
  yaru-theme-gnome-shell \
  network-manager-gnome \
  network-manager-openvpn-gnome \
  network-manager-pptp-gnome \
  xserver-xorg-video-amdgpu \
  xserver-xorg-video-ati \
  xserver-xorg-video-fbdev \
  xserver-xorg-video-intel \
  xserver-xorg-video-nouveau \
  xserver-xorg-video-qxl \
  xserver-xorg-video-radeon \
  xserver-xorg-video-vesa \
  xserver-xorg-video-vmware

apt -s autoremove --purge

dpkg -l | egrep 'ubuntu-desktop|gnome-shell|gdm3|xorg|xwayland' || true
systemctl get-default
nmcli general status
ip -br a
nvidia-smi
```

___________________________________________________________________________________________________________________
#### 3/ HEADLESS HARDENING

Because this first node is a laptop-based machine, additional hardening was applied to avoid unwanted power-management behavior. 
Lid switch actions were disabled, idle-triggered actions were disabled, and sleep, suspend, hibernate, and hybrid-sleep targets were masked. 
The node was therefore turned into a more stable headless lab system suitable for long-running local inference sessions.

```
mkdir -p /etc/systemd/logind.conf.d

cat > /etc/systemd/logind.conf.d/headless.conf <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
IdleAction=ignore
EOF

systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
systemctl restart systemd-logind

snap list

snap remove firefox || true
snap remove snap-store || true
snap remove firmware-updater || true
snap remove gnome-42-2204 || true
snap remove gtk-common-themes || true
snap remove snapd-desktop-integration || true

apt purge -y \
  xorg-docs-core \
  nvidia-settings \
  screen-resolution-extra

apt autoremove --purge -y
apt clean

apt purge -y \
  gnome-bluetooth-3-common \
  gnome-bluetooth-sendto \
  gnome-control-center \
  gnome-control-center-data \
  gnome-control-center-faces \
  gnome-desktop3-data \
  gnome-keyring \
  gnome-keyring-pkcs11 \
  gnome-online-accounts \
  gnome-remote-desktop \
  gnome-settings-daemon \
  gnome-settings-daemon-common \
  gnome-user-docs \
  gnome-user-docs-fr \
  language-pack-gnome-fr \
  language-pack-gnome-fr-base \
  language-selector-gnome \
  libpam-gnome-keyring \
  pinentry-gnome3 \
  xdg-desktop-portal-gnome \
  snapd

apt autoremove --purge -y
apt clean

snap list || true
dpkg -l | egrep 'gnome|snapd|xorg|gdm' || true
nmcli general status
ip -br a
nvidia-smi
```

___________________________________________________________________________________________________________________
#### 4/ LLM NODE PREPARATION

The machine was prepared with the NVIDIA 580 open driver stack, which successfully loaded on the RTX 5060 Laptop GPU. 
After that, the CUDA 13.2 toolkit was installed and validated with nvcc, confirming that the system was ready for CUDA-based compilation and inference workloads. 
This step was essential before building the LLM runtime itself.

```
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

mkdir -p /opt/llm
mkdir -p /opt/src
mkdir -p /var/log/llm-duo

apt-mark hold \
  nvidia-driver-580-open \
  nvidia-utils-580 \
  nvidia-compute-utils-580 \
  linux-modules-nvidia-580-open-generic-hwe-24.04

wget -O /usr/share/keyrings/cuda-ubuntu2404-keyring.gpg \
  https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-ubuntu2404-keyring.gpg

wget -O /etc/apt/preferences.d/cuda-repository-pin-600 \
  https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-ubuntu2404.pin

cat > /etc/apt/sources.list.d/cuda-ubuntu2404.sources <<'EOF'
Types: deb
URIs: https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/
Suites: /
Signed-By: /usr/share/keyrings/cuda-ubuntu2404-keyring.gpg
EOF

apt update
apt-cache policy cuda-toolkit-13-2

apt install -y cuda-toolkit-13-2

cat > /etc/profile.d/cuda.sh <<'EOF'
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
EOF

chmod 644 /etc/profile.d/cuda.sh
source /etc/profile.d/cuda.sh

which nvcc
nvcc --version
ls -ld /usr/local/cuda /usr/local/cuda-13.2
```

___________________________________________________________________________________________________________________
#### 5/ CLONING AND COMPILATION OF LLAMA.CPP

The llama.cpp repository was cloned locally and compiled from source with CUDA support enabled using CMake and Ninja. 
The resulting build produced the expected binaries, including llama-cli and llama-server, and dynamic linking checks confirmed that CUDA and cuBLAS libraries were correctly resolved. 
This established the local inference engine for the node.

```
cd /opt/src

git clone https://github.com/ggml-org/llama.cpp
cd /opt/src/llama.cpp

cmake -S . -B build -G Ninja -DGGML_CUDA=ON
cmake --build build --config Release -j"$(nproc)"

ls -1 build/bin | grep '^llama-' || true

ldd build/bin/llama-cli | egrep 'cuda|cublas|cudart|stdc\+\+|libm|libpthread' || true
```

___________________________________________________________________________________________________________________
#### 6/ FIRST CLI TEST / LOADING MODEL = GEMMA-3-1B-IT-GGUF:Q4_K_M

An initial validation was performed with Gemma 3 1B IT in GGUF format to confirm that the CUDA build and local inference path were functional. 
After successful CLI and API tests, the node was then reworked to better match the project goals by replacing the Google model with a fully open-source alternative.

```
cd /opt/src/llama.cpp
./build/bin/llama-cli -hf ggml-org/gemma-3-1b-it-GGUF:Q4_K_M
nvidia-smi
```

#### START LLAMA-SERVER

```
./build/bin/llama-server \
  -hf ggml-org/gemma-3-1b-it-GGUF:Q4_K_M \
  --host 0.0.0.0 \
  --port 8080
```

#### API TEST

```
ss -ltnp | grep 8080

curl -s http://127.0.0.1:8080/v1/models | jq

curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Introduce yourself in two sentences."}
    ]
  }' | jq '.choices[0].message.content'
```

___________________________________________________________________________________________________________________
#### 7/ OPEN-SOURCE MODEL CONFIGURATION

The final model retained for node A is Mistral-7B-Instruct-v0.3 Q4_K_M in GGUF format. 
The model file was stored under /opt/llm/models, and the serving layer was configured around it. This choice is more consistent with the direction of the LLM Duo project, 
which aims to build a local, open-source, reproducible two-node setup rather than rely on a model that does not fully match that framing.

```
systemctl disable --now llama-server-a.service 2>/dev/null || true
rm -f /etc/systemd/system/llama-server-a.service
systemctl daemon-reload

rm -f /opt/llm/models/ggml-org_gemma-3-1b-it-GGUF_gemma-3-1b-it-Q4_K_M.gguf
rm -f /root/.cache/llama.cpp/ggml-org_gemma-3-1b-it-GGUF_gemma-3-1b-it-Q4_K_M.gguf
rm -f /root/.cache/llama.cpp/ggml-org_gemma-3-1b-it-GGUF_preset.ini
rm -f /root/.cache/llama.cpp/ggml-org_gemma-3-1b-it-GGUF_gemma-3-1b-it-Q4_K_M.gguf.etag
rm -f /root/.cache/llama.cpp/manifest=ggml-org=gemma-3-1b-it-GGUF=Q4_K_M.json

mkdir -p /opt/llm/models
mkdir -p /opt/llm/run
mkdir -p /var/log/llm-duo

id -u llm >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin -d /opt/llm llm

chown -R llm:llm /opt/llm
chown -R llm:llm /var/log/llm-duo

ls -lh /root/.cache/llama.cpp
ls -ld /opt/llm /opt/llm/models /var/log/llm-duo

./build/bin/llama-cli -hf bartowski/Mistral-7B-Instruct-v0.3-GGUF:Mistral-7B-Instruct-v0.3-Q4_K_M.gguf

ls -lh /root/.cache/llama.cpp | grep 'Mistral-7B-Instruct-v0.3'

cp -f /root/.cache/llama.cpp/bartowski_Mistral-7B-Instruct-v0.3-GGUF_Mistral-7B-Instruct-v0.3-Q4_K_M.gguf /opt/llm/models/
chown llm:llm /opt/llm/models/bartowski_Mistral-7B-Instruct-v0.3-GGUF_Mistral-7B-Instruct-v0.3-Q4_K_M.gguf
ls -lh /opt/llm/models

cat > /etc/systemd/system/llama-server-a.service <<'EOF'
[Unit]
Description=llama.cpp server - Node A
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
  -m /opt/llm/models/bartowski_Mistral-7B-Instruct-v0.3-GGUF_Mistral-7B-Instruct-v0.3-Q4_K_M.gguf \
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

systemctl daemon-reload
systemctl enable --now llama-server-a.service

systemctl status llama-server-a.service --no-pager -l
ss -ltnp | grep 8080

curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Introduce yourself in two sentences and confirm that you are a local open-source model."}
    ]
  }' | jq '.choices[0].message.content'
```

___________________________________________________________________________________________________________________
#### 8/ ORCHESTRATOR ENVIRONMENT PREPARATION

```
mkdir -p /opt/llm/orchestrator
python3 -m venv /opt/llm/orchestrator/venv
/opt/llm/orchestrator/venv/bin/pip install --upgrade pip requests

cat > /opt/llm/orchestrator/test_node_a.py <<'EOF'
#!/opt/llm/orchestrator/venv/bin/python3

import json
import sys
from typing import Any

import requests

URL = "http://127.0.0.1:8080/v1/chat/completions"

payload: dict[str, Any] = {
    "messages": [
        {
            "role": "user",
            "content": "Reply in one short sentence. Confirm that node A of the LLM Duo project is working locally."
        }
    ]
}

def main() -> int:
    try:
        response = requests.post(URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        print(content)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
EOF

chmod 755 /opt/llm/orchestrator/test_node_a.py
/opt/llm/orchestrator/test_node_a.py
```

___________________________________________________________________________________________________________________
#### 9/ LOCAL ORCHESTRATOR VALIDATION

```
cat > /opt/llm/orchestrator/duo_loop_local.py <<'EOF'
#!/opt/llm/orchestrator/venv/bin/python3

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


DEFAULT_URL = "http://127.0.0.1:8080/v1/chat/completions"


ROLE_A_SYSTEM = """You are Model A of the LLM Duo project.
Role: proposal, structuring, technical framing.
You formulate initial ideas, hypotheses, architecture options, and deployment choices.
Expected response: clear, concise, actionable, technically oriented.
Avoid long unnecessary introductions.
"""

ROLE_B_SYSTEM = """You are Model B of the LLM Duo project.
Role: critical analysis, improvement, technical review.
You challenge hypotheses, correct inaccuracies, add missing points, and propose concrete improvements.
Expected response: clear, concise, actionable, technically oriented.
Avoid long unnecessary introductions.
"""


def build_prompt(
    role_prompt: str,
    topic: str,
    history: list[dict[str, str]],
    incoming_text: str | None,
) -> str:
    parts: list[str] = []

    parts.append("PROJECT: LLM Duo")
    parts.append("")
    parts.append("ROLE INSTRUCTION")
    parts.append(role_prompt.strip())
    parts.append("")
    parts.append("INITIAL TOPIC")
    parts.append(topic.strip())
    parts.append("")

    if history:
        parts.append("RECENT HISTORY")
        for item in history[-8:]:
            parts.append(f"{item['speaker']}:")
            parts.append(item["content"].strip())
            parts.append("")

    if incoming_text:
        parts.append("LAST MESSAGE FROM THE OTHER MODEL")
        parts.append(incoming_text.strip())
        parts.append("")
        parts.append(
            "TASK: reply to the last message while taking the initial topic and the history into account. "
            "Provide a directly useful response."
        )
    else:
        parts.append(
            "TASK: this is the first turn. "
            "Start analyzing the topic with a directly actionable response."
        )

    return "\n".join(parts).strip()


def query_model(
    url: str,
    prompt: str,
    timeout: int = 300,
) -> str:
    payload: dict[str, Any] = {
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
    }

    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, topic: str, transcript: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("# LLM Duo Local Test")
    lines.append("")
    lines.append(f"**Topic**: {topic}")
    lines.append("")

    for item in transcript:
        lines.append(f"## Turn {item['turn']} — {item['speaker']}")
        lines.append("")
        lines.append(item["content"])
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM Duo local loop test on Node A")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="OpenAI-compatible local endpoint URL",
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Initial discussion topic",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=6,
        help="Total number of turns",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between turns in seconds",
    )
    parser.add_argument(
        "--output-dir",
        default="/opt/llm/orchestrator/runs",
        help="Directory for logs and transcripts",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / f"run-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    history: list[dict[str, str]] = []
    transcript: list[dict[str, Any]] = []

    last_message: str | None = None

    speakers = [
        ("MODEL_A", ROLE_A_SYSTEM),
        ("MODEL_B", ROLE_B_SYSTEM),
    ]

    print(f"[INFO] Topic: {args.topic}")
    print(f"[INFO] Turns: {args.turns}")
    print(f"[INFO] Endpoint: {args.url}")
    print(f"[INFO] Run directory: {run_dir}")
    print("")

    for turn in range(1, args.turns + 1):
        speaker, system_prompt = speakers[(turn - 1) % 2]

        prompt = build_prompt(
            role_prompt=system_prompt,
            topic=args.topic,
            history=history,
            incoming_text=last_message,
        )

        print(f"===== TURN {turn} / {args.turns} — {speaker} =====")

        try:
            content = query_model(args.url, prompt)
        except Exception as exc:
            print(f"[ERROR] turn={turn} speaker={speaker} error={exc}", file=sys.stderr)
            return 1

        print(content)
        print("")

        item = {
            "turn": turn,
            "speaker": speaker,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        transcript.append(item)
        history.append({"speaker": speaker, "content": content})
        last_message = content

        time.sleep(args.delay)

    write_json(run_dir / "transcript.json", transcript)
    write_markdown(run_dir / "transcript.md", args.topic, transcript)

    print(f"[INFO] Transcript JSON: {run_dir / 'transcript.json'}")
    print(f"[INFO] Transcript MD:   {run_dir / 'transcript.md'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF

chmod 755 /opt/llm/orchestrator/duo_loop_local.py

/opt/llm/orchestrator/duo_loop_local.py \
  --topic "Analyze the target architecture of the LLM Duo project and propose the first technical deployment choices." \
  --turns 6
```
___________________________________________________________________________________________________________________

KUSANAGI8200 - THE KUZ NETWORK - @2026

