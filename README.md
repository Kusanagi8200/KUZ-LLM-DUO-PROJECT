
LLM DUO - RUN AWAY - #01

INTRODUCTION

Within the KUZ NETWORK laboratory, a new experiment will soon be set up around the local execution of open-source language models. This project, called Local LLM Duo, will consist of running two distinct models on two different machines and then automating their exchanges through a central orchestrator.

The goal will not be to produce a simple demonstration effect. The project will primarily serve as a working platform to study how several open-source components can be assembled into a coherent local environment --> Linux system, GPU drivers, inference engine, LLM models, network API, and orchestration logic.

The real interest of the lab will lie in this integration layer, meaning the way multiple technical components will be connected cleanly in order to create a continuous inference loop between two model instances.

The installation has not started yet. This document therefore presents the planned architecture, the tools that will be used, and the way the lab will be built from a technical perspective.
OVERALL ARCHITECTURE

The lab will rely on a simple distributed architecture built around two physical nodes connected over the local network.

The first machine will act as the main node. It will host the orchestrator, the first language model, and the control interface for the experiment. This machine will be used to start sessions, monitor exchanges, and store technical logs.

The second machine will run another language model. It will not control the session itself, but will expose an inference endpoint over the network so that the orchestrator can send requests to it and retrieve its responses.

The planned workflow will be as follows --> an initial topic will be injected into the first model, the generated answer will be captured by the orchestrator, then forwarded to the second model.

The second model’s reply will then be sent back to the first one, and the loop will continue according to the parameters defined when the session starts.

The system will therefore rely on a chain of requests controlled by the orchestrator, with preservation of the conversational context and management of turn order.
HARDWARE INFRASTRUCTURE

Machine A will be the main workstation of the lab. It will be equipped with an Intel i9 processor, 32 GB RAM, and an NVIDIA RTX 5060 8G VRAM. This machine will have a dual role: it will run the first model and also host the entire control logic of the experiment.

Machine B will serve as the second inference node. It will be based on an Intel i5, 32 GB of RAM, and an NVIDIA RTX 3050 4G VRAM. It will host the second model and answer requests sent from the main machine.

This hardware separation will make it possible to test a real distributed setup, with two independent execution environments, two separate GPU workloads, and actual inter-machine communication.

This matters because the experiment will not only focus on the responses produced by the models, but also on the way a lightweight multi-node system will be built around them.
OPENS-SOURCE TOOLS AND COMPONENTS

The lab will rely on a set of relatively lightweight open-source tools suited to this type of experimentation.

The system foundation will most likely be built on Linux, using a base such as Debian, in order to provide a stable environment, straightforward administration, and compatibility with the GPU tooling required for local inference.

For the model execution layer, the planned choice will be Ollama. This tool will make it possible to run language models locally, manage them as services, and, most importantly, expose a simple HTTP API that can easily be used from a Python script.

This point will be central to the project, since the orchestrator will rely on this API to manage the exchanges between the two machines.

As for the models themselves, several open-source families may be tested depending on the available resources and the results sought. The lab will probably begin with models from the Open-Source Models family, then possibly compare their behavior with other models available in the Ollama ecosystem.

The goal will not be to lock the project immediately to a single model, but rather to create a flexible technical base that will make it easy to switch engines or models over time.

The overall design will therefore rely on four clearly separated layers: the Linux system, the NVIDIA GPU stack, the local inference engine, and the orchestration program.
TECHNICAL DEPLOYMENT

The lab deployment will begin with the preparation of both machines. The operating system will first need to be installed, the base updates applied, the local network configured, and communication between both nodes verified.

This stage will include address resolution, connectivity testing, and basic validation of network exchanges between the main machine and the second node.

Once the system base is ready, the priority will be the GPU layer setup. NVIDIA drivers will be installed on both machines, and the CUDA stack compatible with the selected environment will be verified.

At this stage, the goal will not yet be to run the models, but to confirm that the GPUs will be correctly recognized by the system and usable by the inference services.

The first checks will therefore focus on hardware detection, driver versions, and the general stability of the compute environment.

After that phase, the lab will move on to installing the inference engine. Ollama will be deployed on each machine and started locally as a service. It will then be necessary to verify that each node can correctly answer local API requests. This stage will confirm that a simple prompt can be sent to the model and that a structured response can be retrieved without service-side errors.

Once Ollama is operational, the first models will be downloaded and loaded onto each machine. This is where the lab will begin testing compatibility between the size of the chosen models, the available memory, and the actual GPU performance.

It will probably be necessary to adjust the initial choices depending on memory usage, observed inference speed, and response stability. The lab will therefore be built progressively, prioritizing reliable operation before any advanced optimization.

When both machines are able to answer inference calls independently, the next step will be to connect both services within the same application logic.
ORCHESTRATOR DESIGN

The orchestrator will be the software core of the project. It will not be a simple test script, but a lightweight control layer responsible for message routing, context construction, and global session management.

The natural choice will be Python, since this language will make it possible to build clear, modular logic that can easily evolve over time. The orchestrator will most likely use a standard HTTP library to communicate with the Ollama APIs running on both machines.

It will also include an internal data structure responsible for storing the conversation history, along with a prompt-formatting layer so that each model receives usable context.

The program will begin by loading a configuration defining the essential parameters --> IP addresses or DNS names of both nodes, ports used by the Ollama services, model names, inference settings, maximum number of turns, and possibly dedicated system instructions for each role.

This configuration phase will be important because it will make it possible to keep the application logic clearly separated from the experiment parameters.

Once initialized, the orchestrator will inject a starting topic into model A. The response will be stored, formatted, and then forwarded to model B as a new context element. Model B will generate its own reply, which will in turn be recorded and sent back to model A.

This loop will repeat until a predefined stop condition is reached, such as a fixed number of iterations, a manual stop, or a context-length threshold.

A key technical point will be conversation context management. Since the models do not have persistent memory, the orchestrator will have to rebuild at each turn a prompt containing at least the initial topic, the latest exchanged messages, and, when required, a condensed version of the older parts. This means that the program will not merely pass text between two APIs: it will also perform actual contextual reconstruction.

As the discussion grows longer, the orchestrator will also have to handle another standard issue --> the maximum context size supported by the models. The planned design will therefore eventually include a context-reduction strategy.

This reduction may rely on partial truncation of older messages or on the generation of an intermediate summary that preserves the essential points of the exchange. This mechanism will be crucial in order to maintain long sessions without saturating the model’s context window.

At the same time, the orchestrator will have to produce usable traceability. Each session should ideally be logged into a text or Markdown file with timestamps, identification of the speaking model, message content, and possibly technical metadata about each generation turn. This logging layer will be useful both for functional tracking and for debugging the environment.

In the longer term, the program may also include complementary features such as improved console rendering, separation between system prompts and user messages, or a configuration mode based on YAML or JSON files.

At first, however, the priority will remain the creation of a stable, readable, and reproducible loop between the two nodes.
SOFTWARE DEPLOYMENT SEQUENCE

The lab will probably be built in successive stages. The first phase will consist in validating each machine independently. stable system, detected GPU, functional Ollama service, loaded model, and correct response to a local call. Until this base is fully under control, moving on to inter-machine orchestration will not be relevant.

The second phase will consist in validating remote communication. From the main machine, it will be necessary to confirm that an HTTP call to Machine B can successfully retrieve a response from the remote model. This step will help isolate network, firewall, service, or request-format issues before the full dialogue logic is introduced.

The third phase will be the development of the first functional orchestrator. It will initially remain deliberately simple. Sending a starting topic, alternating responses, displaying the exchange in the console, and storing a minimal history. Once this base is validated, the code will be extended with better context handling, cleaner logs, adjustable parameters, and more robust behavior in case of request errors or empty responses.

The lab will therefore not be built as a monolithic block, but as a set of technical building blocks validated one by one. This method will make it possible to keep a clear understanding of the system, identify friction points quickly, and evolve the project cleanly.
PROJECT PURPOSE

Through Local LLM Duo, the KUZ NETWORK laboratory will set up an experimental environment focused on local open-source LLMs, GPU-based inference, and their orchestration within a lightweight distributed architecture.

The interest of the project will lie as much in the models themselves as in the technical setup built around them. The real subject of the lab will be the construction of a coherent, reproducible, and fully controlled small-scale system capable of making two model instances interact using only open-source tools and local infrastructure.

In that sense, Local LLM Duo will be less a simple demonstration than a practical testbed for exploring the behavior of open-source models, context management, the stability of a local inference engine, and the orchestration logic required to coordinate multiple nodes inside the same application loop.

THE KUZ NETWORK - @2026
