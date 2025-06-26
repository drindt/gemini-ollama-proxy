# Ollama-Gemini-Gateway

An intelligent, self-hosted API gateway that translates [Ollama](https://ollama.com/) API requests to the
[Google Gemini API](https://ai.google.dev/gemini-api). Use powerful Gemini models like Gemini 1.5 Pro directly in your
favorite Ollama-compatible clients and IDEs.

## 🌟 Overview

Many modern development tools and IDEs (like JetBrains AI Assistant) offer fantastic integration with local language
models through the Ollama API. However, running large, high-performance models locally requires significant hardware
resources.

The Ollama-Gemini-Gateway provides the best of both worlds. It acts as a lightweight bridge, emulating the Ollama API
locally while forwarding all requests to be processed by Google's powerful Gemini models in the cloud. This allows you
to leverage the newest AI without needing a high-end GPU.

## ✨ Features

* **Ollama API Emulation**: Perfectly mimics the required Ollama endpoints (`/`, `/api/tags`, `/api/chat`) for seamless
  client compatibility.
* **Dynamic Model Listing**: Fetches the list of available models directly from the Gemini API, so you always have
  access to the latest versions.
* **Streaming Support**: Full support for ndjson streaming, providing real-time, token-by-token responses in your
  client.
* **IDE Patch Support**: Intelligently handles special "Code Patching" system prompts from IDEs to apply code changes
  correctly.
* **Containerized**: Comes with a Containerfile and `compose.yaml` for easy, reproducible deployment with Podman or
  Docker.
* **Health Monitoring**: Built-in container health checks ensure the service is running properly and can automatically
  restart if needed.
* **Configurable**: Easily configure the host, port, and default model via environment variables.

## 🚀 Getting Started

### Prerequisites

* [Podman](https://podman.io/) or [Docker](https://www.docker.com/) installed.
* `podman-compose` or `docker-compose` installed.
* A Google AI API Key. You can get one from the [Google AI Studio](https://aistudio.google.com/app/apikey).

### Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/drindt/ollama-gemini-gateway.git
   cd ollama-gemini-gateway
   ```
   *This step is necessary to get the required `compose.yaml` and `.env.example` files.*

2. **Create Environment File**
    ```bash
    cp .env.example .env
    ```
   Then, edit the `.env` file and add your Google AI API key:
    ```dotenv
    # .env
    GENAI_API_KEY="YOUR_GOOGLE_AI_API_KEY_HERE"
    # Optional: Customize the port
    PORT=11434
    LOG_LEVEL="WARN"
    ```

3. **Run the Container**

   You have two options: running the pre-built image or building it from the source.

   #### Option A: Run the Pre-built Image (Recommended)

   This is the quickest way to get started.

    ```bash
    # Pull the latest image from the registry and start the service
    podman-compose up -d
    ```

   *Note: The command will automatically pull the image `drindt/gemini-ollama-proxy:latest` if it's not available
   locally.*

   #### Option B: Build from Source

   Use this option if you want to modify the code or build the image yourself.

    ```bash
    # Build the image locally and start the service in the background
    podman-compose up --build -d
    ```

4. **Stop the Service**
    ```bash
    # To stop the running containers
    podman-compose down
    ```

## 🛠️ Usage

Once the gateway is running, you can connect your Ollama-compatible client to it.

### Example: JetBrains IDE (IntelliJ, PyCharm, etc.)

1. Go to **Settings / Preferences > Tools > AI Assistant**.
2. Under **Third-party AI providers**, select and enable **Ollama**.
3. Set the **URL** to the address of your running container, which is typically `http://localhost:11434` (or the port
   you configured).
4. Click "**Test Connection**." It should show "Connected."
5. The gateway will now proxy requests from the AI Assistant to the Gemini API.

## ⚙️ Configuration

The application can be configured using the following environment variables in the `.env` file:

| Variable        | Description                                                                         | Default   |
|:----------------|:------------------------------------------------------------------------------------|:----------|
| `GENAI_API_KEY` | **Required**. Your API key for the Google Gemini service.                           | `None`    |
| `HOST`          | The host address the server will bind to. Should be `0.0.0.0` inside the container. | `0.0.0.0` |
| `PORT`          | The port the server will listen on.                                                 | `11434`   |
| `LOG_LEVEL`     | The logging level for the application.                                              | `INFO`    |

## 🌐 API Documentation

This project uses FastAPI and automatically provides interactive API documentation. After starting the
container, you can access the following URLs to explore and test the API endpoints:

* **Swagger UI:** [http://localhost:11434/docs](http://localhost:11434/docs)
* **ReDoc:** [http://localhost:11434/redoc](http://localhost:11434/redoc)

The documentation is generated directly from the code and is therefore always up to date.

## 🧠 Controlling AI Creativity

This gateway acts as a true proxy, allowing you to pass generation parameters from your Ollama-compatible client
directly to the Gemini API. This gives you fine-grained control over the model's responses.

Most Ollama clients (including the JetBrains AI Assistant) allow you to configure these parameters. The gateway forwards
the following settings:

* **`temperature`**: (Default: `0.5`) Controls the randomness of the output. A lower value (e.g., `0.1`) makes the
  model more deterministic and focused, while a higher value (e.g., `0.9`) makes it more creative and diverse.
* **`top_p`**: (Default: `1.0`) Controls the nucleus sampling. The model considers only the tokens with the highest
  probability mass that add up to `top_p`. A lower value (e.g., `0.7`) can lead to more focused and less random
  outputs.
* **`seed`**: (Default: `None`) If you set a specific number (e.g., `42`), the model will try to produce the same
  output for the same input and seed. This is useful for reproducibility.
* **`stop`**: (Default: `None`) A list of text sequences (e.g., `["\n", "###"]`) where the API should stop generating
  tokens.

If your client does not send these parameters, the defaults specified above will be used to ensure a balanced and
creative response.

## 🔄 Building a New Image Version

When you want to create a new container image version of the gateway, you can use the following commands. These add
important metadata to your image that helps with versioning and traceability.

```bash
# Build a new image with creation timestamp and version tags
# Uncomment to include git revision in build arguments:
export VERSION="0.1.0"
podman-compose build \
               --build-arg REVISION=$(git rev-parse --short HEAD) \
               --build-arg CREATED=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
               --build-arg VERSION=$VERSION

# Verify the container labels after building
podman inspect gemini-ollama-proxy | jq '.[].Labels'
```

Tag and push to a container registry

```bash
podman tag gemini-ollama-proxy gemini-ollama-proxy:$VERSION
podman push registry.example.com/$USER/my-gemini-ollama-proxy:$VERSION
```

This ensures your container image is properly versioned and includes relevant metadata like creation timestamp, making
it easier to manage in production environments.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.md) file for details.

## 🙏 Acknowledgements

This project is powered by excellent Python libraries, including:

* [FastAPI](https://fastapi.tiangolo.com/)
* [Pydantic](https://docs.pydantic.dev/)
* [Uvicorn](https://www.uvicorn.org/)
* [google-genai](https://github.com/google/generative-ai-python)
