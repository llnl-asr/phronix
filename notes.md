litellm + individual llamacpp servers
[5:31 PM]use 8bit
marathe1  [5:31 PM]
Models:
https://huggingface.co/ggml-org/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF
https://huggingface.co/unsloth/Muse-Glimmer-30B-GGUF
https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-GGUF(edited)
huggingface.coornith-ai/Ornith-1.5-35B-A3B-GGUF · Hugging FaceWe’re on a journey to advance and democratize artificial intelligence through open source and open science.[5:33 PM]llama.cpp path:
/usr/WS2/dldl/LLM/llama-cpp-turboquant/build-h100/bin/llama-server[5:33 PM]Refer to launch.sh
[5:33 PM]model:
/usr/workspace/dldl/LLM/models/nemotron[5:36 PM]Include keywords in building llama.cpp: turboquant, MTP, ROCM APU MI300A build,
https://github.com/TheTom/llama-cpp-turboquant.git

focus on tokens_in, tokens_out on y2 as lines and capability_new (skills + mcp) created and reused stacked on y1.

after this run the same pipeline without dftracer-agents or phronix by just giving instructions on what needs to be done with claude and sonnet as base case I want to compare the metrics for eval5 we care about between these two runs. X axis are teh different stages of the pipeline and how successful or failed they were with a timelimit on tasks if they fail a lot.

