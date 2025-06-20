# Deploy Llama-3.3-70B-Instruct on Serverless GPUs

Built with developer experience in mind, Tensorfuse simplifies the process of deploying serverless GPU apps. In this guide, we will walk you through the process of deploying Llama 3.3 70B Instruct model using Tensorfuse on your cloud account.

We will be using `L40S` GPUs as each L40S GPU has about 40GB of GPU memory and we need around 140GB of GPU memory to run the model in `float16`. Therefore we will be running
Llama 3.3 on `4` L40S GPUs.

We will also add **token based authentication** to our service which is compatible with OpenAI client libraries.

> **Info:**
> vLLM server is essentially a FastAPI app and it can be extended to support middlewares and other features of FastAPI. In this guide,
> we will see how we can support authentication using a Bearer token. If you need more information on how to add more features
> to vLLM, feel free to ask us in our [Slack Community](https://join.slack.com/t/tensorfusecommunity/shared_invite/zt-30r6ik3dz-Rf7nS76vWKOu6DoKh5Cs5w)

## Prerequisites

Before you begin, ensure you have configured Tensorkube on your AWS account. If you haven't done that yet, follow the [Getting Started](https://tensorfuse.io/docs/concepts/getting_started_tensorkube) guide.

## Deploying Llama-3.3-70B-Instruct with Tensorfuse

Each tensorkube deployment requires three things - your code, your environment (as a Dockerfile) and a deployment configuration.

We also need to provide `huggingface-token` to download the model from the huggingface hub and also an `authentication-token` that our vLLM service
will use to authenticate incoming requests. vLLM provides a straightforward way to add authentication to your service via their `--api-key` flag.

We need to store both these tokens as [Tensorfuse secrets](https://tensorfuse.io/docs/concepts/secrets).

### Step 1: Setting up the secrets

#### 1. Access to Llama 3.3
- Llama-3.3 requires a license agreement. Visit the [Llama 3.3 huggingface repo](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) to ensure that you have signed the agreement and have access to the model.

#### 2. Set huggingface token
- Get a `READ` token from your [huggingface profile](https://huggingface.co/settings/tokens) and store it as a secret in Tensorfuse using the command below.

```bash
  tensorkube secret create hugging-face-secret HUGGING_FACE_HUB_TOKEN=hf_EkXXrzzZsuoZubXhDQ --env default
```

- Ensure that the key for your secret is `HUGGING_FACE_HUB_TOKEN` as vLLM assumes the same.

#### 3. Set your API authentication token
- Generate a random string that will be used as your API authentication token. Store it as a secret in Tensorfuse using the command below.
  For the purpose of this demo, we will be using `vllm-key` as your api-key.

```bash
  tensorkube secret create vllm-token VLLM_API_KEY=vllm-key --env default
```

- Ensure that in production you use a randomly generated token. You can quickly generate one using `openssl rand -base64 32` and remember to keep it safe as tensorfuse secrets are opaque.

### Step 2 : Prepare the Dockerfile

We will use the propritery vLLM image maintained by Tensorfuse. This image is patched by our team for security and performance issues and comes with all the necessary dependencies to run vLLM.

```dockerfile
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
```

We have used a lot of CLI flags in order to align the vLLM server for our usecase. All the other [vLLM flags are listed here.](https://docs.vllm.ai/en/v0.4.0.post1/serving/openai_compatible_server.html#command-line-arguments-for-the-server)
If you are confused on what flags to use for your production deployment, please ask your query in the [Tensorfuse Community](https://join.slack.com/t/tensorfusecommunity/shared_invite/zt-30r6ik3dz-Rf7nS76vWKOu6DoKh5Cs5w).

### Step 3: Deployment config

Although you can deploy tensorfuse apps [using command line](/reference/cli_reference/tensorkube_deploy), it is always recommended to have a config file so
that you can follow a [GitOps approach](https://about.gitlab.com/topics/gitops/) to deployment.

We set up the basic infra configuration such as the number of gpus and the type of gpu in `deployment.yaml`. You can go through all the configurable options
in the [config file guide](https://tensorfuse.io/docs/concepts/configuration).

```yaml
gpus: 4
gpu_type: l40s
secret:
  - hugging-face-secret
  - vllm-token
readiness:
  httpGet:
    path: /health
    port: 80
```

> **Warning:**
> If no `readiness` endpoint is configured, Tensorfuse tries the `/readiness` path on port 80 by default which can cause issues if your app is not listening on that path.

We are now all set to deploy Llama 3.3 70B Instruct on serverless GPUs using Tensorfuse. Run the below command to start the build and wait for your deployment to get ready.

```bash
tensorkube deploy --config-file ./deployment.yaml
```

### Step 4: Accessing the deployed app

🚀 Voila! Your **autoscaling** production LLM service is ready. Only authenticated requests will be served by your endpoint.

You can list your deployments using the below command

```bash
tensorkube deployment list
```

And that's it! You have successfully deployed the quantized llama-3.1-70b-instruct on serverless GPUs using Tensorkube. 🚀

> **Note:**
> Remember to configure a TLS endpoint with a [custom domain](https://tensorfuse.io/docs/concepts/custom_domains_with_tls) before going to production.

To test it out you can run the following command by replacing the URL with the one provided in the output:

```bash
curl --request POST \
  --url <YOUR_APP_URL>/v1/completions \
  --header  'Content-Type: application/json' \
  --header 'Authorization: Bearer vllm-key' \
  --data '{
    "model": "meta-llama/Llama-3.3-70B-Instruct",
    "prompt": "Earth to Robotland. Who is this?",
    "max_tokens": 500
}'
```

Since vLLM is compatible with the OpenAI API you can query the other endpoints [present here](https://platform.openai.com/docs/api-reference/completions/create).

You can also use the OpenAI Python SDK to query your deployment as shown below:

```python
from openai import OpenAI

BASE_URL = <YOUR_APP_URL>/v1 # replace with your API endpoint and remember to add v1 at the end
API_KEY = 'vllm-key' # replace with your API key

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY
)

response = client.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct",
    prompt="Earth to Robotland. Who is this?"
)

print(response)
```

> **Tip:**
> You can also use the readiness endpoint to wake up your models in case you are expecting incoming traffic

In this case you need to hit the `/health` url.

```bash
curl <YOUR_APP_URL_HERE>/health
```
