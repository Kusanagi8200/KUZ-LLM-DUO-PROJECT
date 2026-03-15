#### WHAT'S INSIDE THE BLACK BOX ?

DISCUSSION BETWEEN LLM IZ ON

    KUZAI-LLM: Hello, I'm KUZAI-LLM. I'm here to help with your questions and conversations. 

    DARK-AI-LLM: Greetings, I'm DARK-AI-LLM, here to provide concise responses. My purpose is to assist with your queries efficiently. 

INSTALLING THE SECOND MACHINE - FHC / DARK-AI NODE

Deploying the second node, the llama.cpp server, the orchestrator, and the first dialogues between two local models.

As part of the LOCAL LLM DUO PROJECT inside THE KUZ NETWORK LAB, I moved forward with the next stage of the setup with a clear objective: make two language models running locally on two different machines talk to each other while keeping full control over the infrastructure, the network, and the exchanges.

After preparing the first node, this new phase focused on installing the second node, deploying its inference engine, building the orchestrator that drives the exchange, and then validating the whole chain with the first automated dialogue tests.
1/ INSTALLING THE SECOND NODE

The first phase was dedicated to preparing the second machine in the lab. The goal was not just to run a model on it, but to turn it into a real compute node dedicated to the project.

The work began with a full hardware audit to confirm that the machine matched the intended role --> processor, memory, NVIDIA GPU, storage, installed operating system, and network state. Once this baseline was validated, the environment was cleaned up to remove components that were no longer useful in this context, especially the previous Ollama engine that was still present on the system.

This step mattered because it allowed the node to start again from a cleaner, more readable, and more coherent base aligned with the architecture chosen for the project.
2/ INSTALLING THE LLAMA.CPP SERVER

Once the node itself was ready, the next logical step was to install the inference engine selected for the lab: llama.cpp.

The NVIDIA stack and the CUDA environment were checked first, then completed where needed so that the engine could be compiled with GPU support. The engine was then built locally with CUDA acceleration, making it possible to run a lightweight local server fully aligned with an on-premise architecture.

A smaller open-source model was selected for this second node in order to preserve comfortable headroom on the available VRAM. The idea was not to push the machine to its absolute limit, but to keep the setup responsive, stable, and able to participate efficiently in the dialogue with the first model.

At the end of this phase, the second node was exposing a working local API through llama.cpp, just like the first one.
3/ BUILDING THE ORCHESTRATOR

Once both nodes were able to answer locally, the next essential component of the project had to be built: the orchestrator.

This orchestrator was developed as a Python script running from the main node. Its job is to manage the dialogue logic between the two models: entry point, turn alternation, forwarding of responses, output length limits, and transcript generation for each run.

The objective at this stage was not yet to build a finished application, but rather to create a simple, readable, modular base capable of running a real A ↔ B loop in a stable way.

This phase also made it possible to improve how instructions are sent to the models, so that the exchange would avoid overly generic drifts or responses that were unnecessarily long.
4. TESTING THE DIALOGUE BETWEEN THE TWO MODELS

Once the orchestrator was ready, several dialogue tests were launched between the two nodes.

This phase had a double purpose. On the one hand, it was necessary to validate the purely technical side: both servers respond correctly, the exchange flows properly, turn order is respected, and the outputs are archived. On the other hand, it was equally important to observe the conversational behavior of the models themselves.

The first tests showed that the infrastructure was working well, but they also made one thing very clear --> a dialogue between two models has to be strongly framed if one wants to avoid repetition, weak confirmation loops, or generic answers. This led to several changes in the orchestrator and in the system instructions, gradually pushing the setup toward a cleaner, more general, and more usable dialogue framework.

In other words, this phase validated not only the technical operation of the project, but also the first practical lessons on how to make two local AIs interact in a meaningful way.
5. BUILDING A SMALL BASH APP TO LAUCH DISCUSSIONS

To make the system easier to use, a small Bash launcher was then added to the project.

The idea was straightforward: avoid typing the full orchestration command manually every time a new test had to be launched. This interactive launcher now allows the user to fill only the useful variables, such as the opening prompt, the number of turns, or a few output limits, and then start the dialogue automatically between both models.

This Bash layer does not replace the Python orchestrator. It simply acts as a lightweight launch interface, useful for chaining tests more comfortably and making the whole project easier to operate in day-to-day lab work.
6. CURRENT STATE OF THE PROJECT

At this point, the LOCAL LLM DUO PROJECT has reached an important milestone.

Both nodes are now operational with their respective local models. The llama.cpp servers are functional on each machine. The orchestrator can run automated exchanges between the two models. And a small Bash tool now makes it easier to start test sessions without rebuilding each command manually.

The system is not yet a finished application, and that is precisely what makes this stage interesting. The lab is now entering a more experimental phase, where the goal is no longer only to install infrastructure, but to improve the actual quality of the exchange, the relevance of the model roles, and the overall fluidity of the orchestration.

So the project is progressing as planned --> first the technical foundation, then operational stability, and gradually after that, the quality of the dialogue itself.
CONCLUSION

What I find particularly interesting in this experiment is not only the fact that two local models can run side by side, but that a complete framework can be built around them to observe their interaction, adjust the dialogue rules, and understand how a simple exchange loop can become a real exploration tool.

For now, THE LOCAL LLM DUO PROJECT remains a technical lab experiment, but it is already beginning to show in practical terms what a fully local architecture for dialogue between open-source models can become: controlled end to end, simple in principle, and rich in future possibilities. 
