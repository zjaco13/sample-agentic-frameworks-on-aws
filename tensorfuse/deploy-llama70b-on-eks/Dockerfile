# vllm base image
FROM tensorfuse/vllm-openai:v0.8.4-patched

# Enable HF Hub Transfer
ENV HF_HUB_ENABLE_HF_TRANSFER 1

# Expose port 80
EXPOSE 80

# Entrypoint with API key
ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server", \
            # name of the model
           "--model", "meta-llama/Llama-3.3-70B-Instruct", \
           # set the data type to float 16 - requires 140GB of GPU memory
           "--dtype", "bfloat16", \
           # below runs the model on 4 GPUs
           "--tensor-parallel-size","4", \
           # Maximum number of tokens, this can lead to OOM errors if overestimated
           "--max-model-len", "4096", \
           # Port on which to run the vLLM server
           "--port", "80", \
           # API key for authentication to the server stored in tensorfuse secrets
           "--api-key", "${VLLM_API_KEY}"]