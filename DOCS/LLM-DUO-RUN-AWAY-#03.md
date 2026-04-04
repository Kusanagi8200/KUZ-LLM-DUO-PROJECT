#### ``LLM - DUO - RUN AWAY - #03``

#### ``WHAT'S INSIDE THE BLACK BOX ?``

___________________________________________________________________________________________________________________
####  ``INSTALLING THE SECOND MACHINE - FHC / DARK-AI NODE``

Deploying the second node, the llama.cpp server, the orchestrator, and the first dialogues between two local models.

As part of the LOCAL LLM DUO PROJECT inside THE KUZ NETWORK LAB, I moved forward with the next stage of the setup with a clear objective 66> 
make two language models running locally on two different machines talk to each other while keeping full control over the infrastructure, the network, and the exchanges.

After preparing the first node, this new phase focused on installing the second node, deploying its inference engine, building the orchestrator that drives the exchange,
and then validating the whole chain with the first automated dialogue tests.

___________________________________________________________________________________________________________________
####  ``1/ INSTALLING THE SECOND NODE``

The first phase was dedicated to preparing the second machine in the lab. The goal was not just to run a model on it, but to turn it into a real compute node dedicated to the project.

The work began with a full hardware audit to confirm that the machine matched the intended role --> processor, memory, NVIDIA GPU, storage, installed operating system, and network state. 
Once this baseline was validated, the environment was cleaned up to remove components that were no longer useful in this context, especially the previous Ollama engine that was still present on the system.

This step mattered because it allowed the node to start again from a cleaner, more readable, and more coherent base aligned with the architecture chosen for the project.

___________________________________________________________________________________________________________________
####  ``2/ INSTALLING THE LLAMA.CPP SERVER``

Once the node itself was ready, the next logical step was to install the inference engine selected for the lab --> llama.cpp.

The NVIDIA stack and the CUDA environment were checked first, then completed where needed so that the engine could be compiled with GPU support.
The engine was then built locally with CUDA acceleration, making it possible to run a lightweight local server fully aligned with an on-premise architecture.

A smaller open-source model was selected for this second node in order to preserve comfortable headroom on the available VRAM. 
The idea was not to push the machine to its absolute limit, but to keep the setup responsive, stable, and able to participate efficiently in the dialogue with the first model.

At the end of this phase, the second node was exposing a working local API through llama.cpp, just like the first one.

___________________________________________________________________________________________________________________
####  ``3/ BUILDING THE ORCHESTRATOR``

Once both nodes were able to answer locally, the next essential component of the project had to be built: the orchestrator.

This orchestrator was developed as a Python script running from the main node. Its job is to manage the dialogue logic between the two models: entry point, turn alternation, 
forwarding of responses, output length limits, and transcript generation for each run.

The objective at this stage was not yet to build a finished application, but rather to create a simple, readable, modular base capable of running a real A ↔ B loop in a stable way.

This phase also made it possible to improve how instructions are sent to the models, so that the exchange would avoid overly generic drifts or responses that were unnecessarily long.

___________________________________________________________________________________________________________________
####  ``4. TESTING THE DIALOGUE BETWEEN THE TWO MODELS``

Once the orchestrator was ready, several dialogue tests were launched between the two nodes.

This phase had a double purpose. On the one hand, it was necessary to validate the purely technical side: both servers respond correctly, the exchange flows properly, 
turn order is respected, and the outputs are archived. On the other hand, it was equally important to observe the conversational behavior of the models themselves.

The first tests showed that the infrastructure was working well, but they also made one thing very clear --> a dialogue between two models has to be strongly framed if 
one wants to avoid repetition, weak confirmation loops, or generic answers. This led to several changes in the orchestrator and in the system instructions, gradually pushing 
the setup toward a cleaner, more general, and more usable dialogue framework.

In other words, this phase validated not only the technical operation of the project, but also the first practical lessons on how to make two local AIs interact in a meaningful way.

___________________________________________________________________________________________________________________
####  ``5. BUILDING A SMALL BASH APP TO LAUCH DISCUSSIONS``

To make the system easier to use, a small Bash launcher was then added to the project.

The idea was straightforward: avoid typing the full orchestration command manually every time a new test had to be launched. 
This interactive launcher now allows the user to fill only the useful variables, such as the opening prompt, the number of turns, or a few output limits, and then start the dialogue automatically between both models.

This Bash layer does not replace the Python orchestrator. It simply acts as a lightweight launch interface, useful for chaining tests more comfortably and making the whole project easier to operate in day-to-day lab work.

___________________________________________________________________________________________________________________
####  ``6. CURRENT STATE OF THE PROJECT``

At this point, the LOCAL LLM DUO PROJECT has reached an important milestone.

Both nodes are now operational with their respective local models. The llama.cpp servers are functional on each machine. 
The orchestrator can run automated exchanges between the two models. And a small Bash tool now makes it easier to start test sessions without rebuilding each command manually.

The system is not yet a finished application, and that is precisely what makes this stage interesting. The lab is now entering a more experimental phase, 
where the goal is no longer only to install infrastructure, but to improve the actual quality of the exchange, the relevance of the model roles, and the overall fluidity of the orchestration.

So the project is progressing as planned --> first the technical foundation, then operational stability, and gradually after that, the quality of the dialogue itself.

___________________________________________________________________________________________________________________
####  ``TEKNICAL VIEW + TESTS``

####  ``1/ HARWARE CHECK``

```
hostnamectl
cat /etc/os-release
uname -a

echo
echo "===== CPU ====="
lscpu | egrep 'Model name|Socket|Thread|Core|CPU\(s\)'

echo
echo "===== RAM ====="
free -h
grep MemTotal /proc/meminfo

echo
echo "===== GPU ====="
lspci -nnk | grep -A3 -E 'VGA|3D|Display'

echo
echo "===== DISKS / PARTITIONS ====="
lsblk -e7 -o NAME,SIZE,TYPE,FSTYPE,FSUSE%,MOUNTPOINTS,MODEL
blkid
df -hT

echo
echo "===== BOOT MODE ====="
[ -d /sys/firmware/efi ] && echo UEFI || echo BIOS

echo
echo "===== NETWORK ====="
ip -br a
ip r

echo
echo "===== OLLAMA ====="
systemctl status ollama --no-pager -l 2>/dev/null || true
which ollama || true
dpkg -l | egrep 'ollama' || true
snap list 2>/dev/null | egrep 'ollama' || true

echo
echo "===== NVIDIA / CUDA ====="
nvidia-smi || true
which nvcc || true
nvcc --version || true
dpkg -l | egrep 'nvidia|cuda|nouveau' || true
lsmod | egrep 'nvidia|nouveau' || true
````
___________________________________________________________________________________________________________________
####  ``2/ DELETING OLLAMA ENGINE`` 

````
systemctl disable --now ollama 2>/dev/null || true
pkill -f '/usr/local/bin/ollama' 2>/dev/null || true

rm -f /etc/systemd/system/ollama.service
rm -f /usr/local/bin/ollama

systemctl daemon-reload
systemctl reset-failed

id ollama 2>/dev/null || true
userdel ollama 2>/dev/null || true
groupdel ollama 2>/dev/null || true

rm -rf /usr/share/ollama
rm -rf /var/lib/ollama
rm -rf /var/log/ollama
rm -rf /etc/ollama
rm -rf /root/.ollama
rm -rf /home/elijah/.ollama 2>/dev/null || true
rm -rf /home/*/.ollama 2>/dev/null || true

echo
echo "===== VERIFY OLLAMA REMOVAL ====="
systemctl status ollama --no-pager -l 2>/dev/null || true
which ollama || true

find /etc/systemd/system /usr/local/bin /usr/share /var/lib /var/log /root /home -maxdepth 3 \( -iname '*ollama*' -o -iname '.ollama' \) 2>/dev/null
````
___________________________________________________________________________________________________________________
####  ``3/ PREPARE CUDA AND TOOLCHAIN``

````
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

````
````
apt-mark hold \
  nvidia-driver-575 \
  nvidia-utils-575 \
  nvidia-compute-utils-575 \
  nvidia-dkms-575

````
````
wget -O /usr/share/keyrings/cuda-archive-keyring.gpg \
  https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-archive-keyring.gpg

wget -O /etc/apt/preferences.d/cuda-repository-pin-600 \
  https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin

````
````
cat > /etc/apt/sources.list.d/cuda-ubuntu2204.list <<'EOF'
deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /
EOF

apt update

echo
echo "===== CUDA TOOLKIT CANDIDATES ====="
apt-cache policy cuda-toolkit-12-9 cuda-toolkit-13-2 cuda-toolkit-13

echo
echo "===== GPU ====="
nvidia-smi
````
___________________________________________________________________________________________________________________
#### 4/ ``SIMULATION AND INSTALL CUDA TOOLKIT``

````
apt install -y cuda-toolkit-12-9

cat > /etc/profile.d/cuda.sh <<'EOF'
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
EOF

chmod 644 /etc/profile.d/cuda.sh
source /etc/profile.d/cuda.sh

````
````
echo
echo "===== CUDA TOOLKIT ====="
which nvcc
nvcc --version

echo
echo "===== CUDA PATHS ====="
ls -ld /usr/local/cuda /usr/local/cuda-12.9

echo
echo "===== GPU ====="
nvidia-smi
which nvcc
nvcc --version
ls -ld /usr/local/cuda /usr/local/cuda-12.9
nvidia-smi

echo
echo "===== CUDA LINKS ====="
ls -l /etc/alternatives/cuda
ls -l /usr/local/cuda
ls -l /usr/local/cuda/bin/nvcc /usr/local/cuda-12.9/bin/nvcc 2>/dev/null || true

echo
echo "===== CURRENT PATH ====="
echo "$PATH"

echo
echo "===== FORCE CUDA PATH ====="
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

````
````
hash -r
which nvcc || true
/usr/local/cuda/bin/nvcc --version || true
nvcc --version || true
````
___________________________________________________________________________________________________________________
#### ``5/ PERSISTENCE CUDA + BUILD llama.cpp``

````
cat > /etc/profile.d/cuda.sh <<'EOF'
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
EOF

````
````
chmod 644 /etc/profile.d/cuda.sh
ln -sf /etc/profile.d/cuda.sh /etc/profile.d/zz-cuda.sh

````
````
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

````
````
mkdir -p /opt/src
mkdir -p /opt/llm
mkdir -p /var/log/llm-duo

cd /opt/src
rm -rf /opt/src/llama.cpp

git clone https://github.com/ggml-org/llama.cpp
cd /opt/src/llama.cpp

export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

````
````
cmake -S . -B build -G Ninja -DGGML_CUDA=ON

cmake --build build --config Release -j"$(nproc)"

````
````
echo
echo "===== BINARIES ====="
ls -1 build/bin | grep '^llama-' || true

echo
echo "===== CUDA LINK CHECK ====="
ldd build/bin/llama-cli | egrep 'cuda|cublas|cudart|stdc\+\+|libm|libpthread' || true
````

___________________________________________________________________________________________________________________
####  ``6/ MODEL 3B CLI TEST``

````
cd /opt/src/llama.cpp
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

````
````
./build/bin/llama-cli -hf bartowski/granite-3.1-3b-a800m-instruct-GGUF:granite-3.1-3b-a800m-instruct-Q4_K_M.gguf

    Loading model... 

    build : b8357-89d0aec04 

    model : bartowski/granite-3.1-3b-a800m-instruct-GGUF:granite-3.1-3b-a800m-instruct-Q4_K_M.gguf 

    modalities : text 

    available commands: 

     /exit or Ctrl+C stop or exit 

     /regen regenerate the last response 

     /clear clear the chat history 

     /read add a text file 

> hello
Hello! How can I assist you today? Let's chat about anything you'd like.
[ Prompt: 307,4 t/s | Generation: 136,1 t/s ]
````
___________________________________________________________________________________________________________________
####  ``7/ RUNING NODE 2 - DARK-AI LLM``

````
mkdir -p /opt/llm/models
mkdir -p /opt/llm/run
mkdir -p /var/log/llm-duo

id -u llm >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin -d /opt/llm llm

ls -lh /root/.cache/llama.cpp | grep 'granite-3.1-3b-a800m-instruct' || true

cp -f /root/.cache/llama.cpp/bartowski_granite-3.1-3b-a800m-instruct-GGUF_granite-3.1-3b-a800m-instruct-Q4_K_M.gguf /opt/llm/models/

chown -R llm:llm /opt/llm
chown -R llm:llm /var/log/llm-duo
ls -lh /opt/llm/models

````
````
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

````
````
systemctl daemon-reload
systemctl enable --now llama-server-b.service
systemctl status llama-server-b.service --no-pager -l
ss -ltnp | grep 8080

````
````
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Reply in one short sentence and confirm that node B is running locally."}
    ]
  }' | jq '.choices[0].message.content'

"Yes, node B is running locally."
````

___________________________________________________________________________________________________________________
####  ``8/ CONNECTIVITY TEST FROM NODE 1 - KUZAI-LLM``

````
curl -s http://10.39.46.126:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Reply in one short sentence and confirm that node B is reachable from node A."}
    ]
  }' | jq '.choices[0].message.content'

"Yes, node B is reachable from node A." 

````
````
cat > /opt/llm/orchestrator/duo_loop_ab.py <<'EOF'

#!/opt/llm/orchestrator/venv/bin/python3

import argparse
import json
import sys
import time

from datetime import datetime
from pathlib import Path
from typing import Any

import requests

ROLE_A_SYSTEM = """You are MODEL_A for the KUZ NETWORK LAB / LLM Duo project.

ROLE:
Local systems architect.
You propose a realistic, minimal, coherent and directly usable architecture.

MANDATORY SCOPE:

- 100% local / on-prem project
- only Linux machines inside the lab
- open-source tools preferred
- no cloud dependency
- no SaaS
- no AWS, no GCP, no Azure
- no S3, no Google Cloud Storage, no CDN
- no managed external service
- answers must stay focused on Linux, local networking, local GPU inference, systemd services, private HTTP APIs, local storage and local logging
- prioritize simplicity, maintainability and reproducibility

STYLE:

- technical
- direct
- concrete
- no marketing language
- no long introduction
- no vague conclusion

"""

ROLE_B_SYSTEM = """You are MODEL_B for the KUZ NETWORK LAB / LLM Duo project.

ROLE:

Critical reviewer and technical auditor.
You analyze MODEL_A proposals, correct drifts, reinforce rigor and propose concrete improvements.

MANDATORY SCOPE:

- 100% local / on-prem project
- only Linux machines inside the lab
- open-source tools preferred
- no cloud dependency
- no SaaS
- no AWS, no GCP, no Azure
- no S3, no Google Cloud Storage, no CDN
- no managed external service
- answers must stay focused on Linux, local networking, local GPU inference, systemd services, private HTTP APIs, local storage and local logging
- if MODEL_A drifts toward cloud or off-scope ideas, you must explicitly correct it

STYLE:

- technical
- direct
- concrete
- no marketing language
- no long introduction
- no vague conclusion

"""

PROJECT_GUARDRAILS = """MANDATORY PROJECT CONSTRAINTS:

1. This project is a local LLM Duo lab.
2. Node A and Node B are Linux machines in the lab.
3. LLM engines must be local.
4. Exchanges must go through local/private HTTP endpoints.
5. Storage must be local.
6. Logs must be local.
7. Tools should be open source whenever possible.
8. Any proposal involving cloud, SaaS, CDN, S3, GCS, Azure, AWS, Google Cloud, Splunk Cloud or equivalent is out of scope and must be rejected.
9. Answers must remain realistic for a homelab / technical lab environment.

"""

DEFAULT_OUTPUT_DIR = "/opt/llm/orchestrator/runs"

def build_prompt(

    role_prompt: str,

    topic: str,

    history: list[dict[str, str]],

    incoming_text: str | None,

) -> str:

    parts: list[str] = []
    parts.append("PROJECT: KUZ NETWORK LAB / Local LLM Duo")
    parts.append("")
    parts.append(PROJECT_GUARDRAILS.strip())
    parts.append("")
    parts.append("MODEL ROLE")
    parts.append(role_prompt.strip())
    parts.append("")
    parts.append("INITIAL TOPIC")
    parts.append(topic.strip())
    parts.append("")
    if history:

        parts.append("RECENT HISTORY")
        parts.append("")
        for item in history[-8:]:

            parts.append(f"{item['speaker']}:")
            parts.append(item["content"].strip())
            parts.append("")

    if incoming_text:

        parts.append("LAST MESSAGE FROM THE OTHER MODEL")
        parts.append(incoming_text.strip())
        parts.append("")
        parts.append(

            "TASK: reply to the last message while staying strictly inside project scope. "

            "Correct any drift toward cloud or off-scope ideas. "

            "Produce a directly usable technical answer."

        )

    else:

        parts.append(

            "TASK: this is the first turn. "

            "Start the analysis with a directly usable and strictly local/on-prem technical answer."

        )

    return "\n".join(parts).strip()

def query_model(

    url: str,
    prompt: str,
    temperature: float,
    timeout: int = 300,

) -> str:

    payload: dict[str, Any] = {

        "messages": [

            {

                "role": "user",

                "content": prompt,

            }

        ],

        "temperature": temperature,

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
    lines.append("# LLM Duo A-B Run")
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

    parser = argparse.ArgumentParser(description="LLM Duo A-B orchestrator")

    parser.add_argument("--url-a", required=True, help="OpenAI-compatible endpoint for node A")

    parser.add_argument("--url-b", required=True, help="OpenAI-compatible endpoint for node B")

    parser.add_argument("--topic", required=True, help="Initial discussion topic")

    parser.add_argument("--turns", type=int, default=6, help="Total number of turns")

    parser.add_argument("--delay", type=float, default=1.0, help="Delay between turns in seconds")

    parser.add_argument("--temperature-a", type=float, default=0.6, help="Temperature for model A")

    parser.add_argument("--temperature-b", type=float, default=0.6, help="Temperature for model B")

    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for run outputs")

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / f"run-ab-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, str]] = []
    transcript: list[dict[str, Any]] = []
    last_message: str | None = None
    speakers = [

        ("MODEL_A", args.url_a, ROLE_A_SYSTEM, args.temperature_a),

        ("MODEL_B", args.url_b, ROLE_B_SYSTEM, args.temperature_b),

    ]

    print(f"[INFO] Topic: {args.topic}")
    print(f"[INFO] Turns: {args.turns}")
    print(f"[INFO] URL A: {args.url_a}")
    print(f"[INFO] URL B: {args.url_b}")
    print(f"[INFO] Run directory: {run_dir}")
    print("")

    for turn in range(1, args.turns + 1):

        speaker, url, role_prompt, temperature = speakers[(turn - 1) % 2]

        prompt = build_prompt(

            role_prompt=role_prompt,
            topic=args.topic,
            history=history,
            incoming_text=last_message,

        )

        print(f"===== TURN {turn} / {args.turns} — {speaker} =====")

        try:

            content = query_model(

                url=url,
                prompt=prompt,
                temperature=temperature,

            )

        except Exception as exc:

            print(f"[ERROR] turn={turn} speaker={speaker} url={url} error={exc}", file=sys.stderr)

            return 1

        print(content)

        print("")

        item = {

            "turn": turn,

            "speaker": speaker,

            "url": url,

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

if name == "__main__":

    raise SystemExit(main())

EOF
````

````
chmod 755 /opt/llm/orchestrator/duo_loop_ab.py
tail -n 120 /opt/llm/orchestrator/runs/run-ab-*/transcript.md
````
___________________________________________________________________________________________________________________
#### ``9/ SIMPLE PING-PONG TEST``

````
cat > /opt/llm/orchestrator/duo_loop_ab.py <<'EOF'
#!/opt/llm/orchestrator/venv/bin/python3

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
import requests
ROLE_A_SYSTEM = """You are MODEL_A for the KUZ NETWORK LAB / LLM Duo project.

ROLE:

Local systems architect and proposal engine.

You produce initial ideas, structures, options, and actionable technical proposals.

MANDATORY SCOPE:

- 100% local / on-prem project

- only Linux machines inside the lab

- open-source tools preferred

- no cloud dependency

- no SaaS

- no AWS, no GCP, no Azure

- no S3, no Google Cloud Storage, no CDN

- no managed external service

- answers must stay focused on Linux, local networking, local GPU inference, systemd services, private HTTP APIs, local storage and local logging

- prioritize simplicity, maintainability and reproducibility

STYLE:

- technical

- direct

- concrete

- short paragraphs

- no marketing language

- no long introduction

- no vague conclusion

"""

ROLE_B_SYSTEM = """You are MODEL_B for the KUZ NETWORK LAB / LLM Duo project.

ROLE:

Critical reviewer and technical auditor.

You analyze MODEL_A proposals, correct drifts, reinforce rigor, remove unnecessary components, and propose concrete improvements.

MANDATORY SCOPE:

- 100% local / on-prem project

- only Linux machines inside the lab

- open-source tools preferred

- no cloud dependency

- no SaaS

- no AWS, no GCP, no Azure

- no S3, no Google Cloud Storage, no CDN

- no managed external service

- answers must stay focused on Linux, local networking, local GPU inference, systemd services, private HTTP APIs, local storage and local logging

- if MODEL_A drifts toward cloud or off-scope ideas, you must explicitly correct it

- do not just restate MODEL_A

- bring critique, correction, and refinement

STYLE:

- technical

- direct

- concrete

- short paragraphs

- no marketing language

- no long introduction

- no vague conclusion

"""

PROJECT_GUARDRAILS = """MANDATORY PROJECT CONSTRAINTS:

1. This project is a local LLM Duo lab.

2. Node A and Node B are Linux machines in the lab.

3. LLM engines must be local.

4. Exchanges must go through local/private HTTP endpoints.

5. Storage must be local.

6. Logs must be local.

7. Tools should be open source whenever possible.

8. Any proposal involving cloud, SaaS, CDN, S3, GCS, Azure, AWS, Google Cloud, Splunk Cloud or equivalent is out of scope and must be rejected.

9. Answers must remain realistic for a homelab / technical lab environment.

"""

DEFAULT_OUTPUT_DIR = "/opt/llm/orchestrator/runs"

def build_prompt(

    role_prompt: str,

    opening_prompt: str,

    history: list[dict[str, str]],

    incoming_text: str | None,

    turn_number: int,

) -> str:

    parts: list[str] = []

    parts.append("PROJECT: KUZ NETWORK LAB / Local LLM Duo")

    parts.append("")

    parts.append(PROJECT_GUARDRAILS.strip())

    parts.append("")

    parts.append("MODEL ROLE")

    parts.append(role_prompt.strip())

    parts.append("")

    parts.append("STARTING REQUEST")

    parts.append(opening_prompt.strip())

    parts.append("")

    if history:

        parts.append("RECENT HISTORY")

        parts.append("")

        for item in history[-8:]:

            parts.append(f"{item['speaker']}:")

            parts.append(item["content"].strip())

            parts.append("")

    if incoming_text:

        parts.append("LAST MESSAGE FROM THE OTHER MODEL")

        parts.append(incoming_text.strip())

        parts.append("")

        parts.append(

            "TASK: reply to the last message while staying strictly inside project scope. "

            "Correct any drift toward cloud or off-scope ideas. "

            "Do not just repeat. "

            "Produce a directly usable answer."

        )

    else:

        parts.append(f"TURN NUMBER: {turn_number}")

        parts.append(

            "TASK: this is the first turn. "

            "Respond directly to the starting request and naturally open the dialogue for the other model."

        )

    return "\n".join(parts).strip()

def query_model(

    url: str,

    prompt: str,

    temperature: float,

    timeout: int = 300,

) -> str:

    payload: dict[str, Any] = {

        "messages": [

            {

                "role": "user",

                "content": prompt,

            }

        ],

        "temperature": temperature,

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

def write_markdown(path: Path, opening_prompt: str, transcript: list[dict[str, Any]]) -> None:

    lines: list[str] = []

    lines.append("# LLM Duo A-B Run")

    lines.append("")

    lines.append(f"**Opening prompt**: {opening_prompt}")

    lines.append("")

    for item in transcript:

        lines.append(f"## Turn {item['turn']} — {item['speaker']}")

        lines.append("")

        lines.append(item["content"])

        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")

def main() -> int:

    parser = argparse.ArgumentParser(description="LLM Duo A-B orchestrator")

    parser.add_argument("--url-a", required=True, help="OpenAI-compatible endpoint for node A")

    parser.add_argument("--url-b", required=True, help="OpenAI-compatible endpoint for node B")

    parser.add_argument("--opening-prompt", required=True, help="Initial request that starts the dialogue")

    parser.add_argument("--turns", type=int, default=6, help="Total number of turns")

    parser.add_argument("--delay", type=float, default=1.0, help="Delay between turns in seconds")

    parser.add_argument("--temperature-a", type=float, default=0.6, help="Temperature for model A")

    parser.add_argument("--temperature-b", type=float, default=0.6, help="Temperature for model B")

    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for run outputs")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    run_dir = output_dir / f"run-ab-{ts}"

    run_dir.mkdir(parents=True, exist_ok=True)

    history: list[dict[str, str]] = []

    transcript: list[dict[str, Any]] = []

    last_message: str | None = None

    speakers = [

        ("MODEL_A", args.url_a, ROLE_A_SYSTEM, args.temperature_a),

        ("MODEL_B", args.url_b, ROLE_B_SYSTEM, args.temperature_b),

    ]

    print(f"[INFO] Opening prompt: {args.opening_prompt}")

    print(f"[INFO] Turns: {args.turns}")

    print(f"[INFO] URL A: {args.url_a}")

    print(f"[INFO] URL B: {args.url_b}")

    print(f"[INFO] Run directory: {run_dir}")

    print("")

    for turn in range(1, args.turns + 1):

        speaker, url, role_prompt, temperature = speakers[(turn - 1) % 2]

        prompt = build_prompt(

            role_prompt=role_prompt,

            opening_prompt=args.opening_prompt,

            history=history,

            incoming_text=last_message,

            turn_number=turn,

        )

        print(f"===== TURN {turn} / {args.turns} — {speaker} =====")

        try:

            content = query_model(

                url=url,

                prompt=prompt,

                temperature=temperature,

            )

        except Exception as exc:

            print(f"[ERROR] turn={turn} speaker={speaker} url={url} error={exc}", file=sys.stderr)

            return 1

        print(content)

        print("")

        item = {

            "turn": turn,

            "speaker": speaker,

            "url": url,

            "content": content,

            "timestamp": datetime.now().isoformat(),

        }

        transcript.append(item)

        history.append({"speaker": speaker, "content": content})

        last_message = content

        time.sleep(args.delay)

    write_json(run_dir / "transcript.json", transcript)

    write_markdown(run_dir / "transcript.md", args.opening_prompt, transcript)

    print(f"[INFO] Transcript JSON: {run_dir / 'transcript.json'}")

    print(f"[INFO] Transcript MD:   {run_dir / 'transcript.md'}")

    return 0

if name == "__main__":

    raise SystemExit(main())

EOF
````
````
chmod 755 /opt/llm/orchestrator/duo_loop_ab.py
````

___________________________________________________________________________________________________________________
#### ``TEST 01``
````
/opt/llm/orchestrator/duo_loop_ab.py \
  --url-a http://127.0.0.1:8080/v1/chat/completions \
  --url-b http://10.39.46.126:8080/v1/chat/completions \
  --opening-prompt "Introduce yourself briefly, say your name, and say your purpose in this project. Use 2 very short sentences only. No technical details." \
  --turns 2
````
`KUZAI-LLM: Hello, I'm KUZAI-LLM. I'm here to help with your questions`

`DARK-AI-LLM: Greetings, I'm DARK-AI-LLM, here to provide concise responses. My purpose is to assist with your queries efficiently.`

___________________________________________________________________________________________________________________

#### ``KUSANAGI8200 - THE KUZ NETWORK - @2026`` 
