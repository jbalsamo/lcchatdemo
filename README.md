# Optimized Flask API with LangChain and Azure OpenAI

This is a high-performance REST API built with Flask and LangChain to interact with the GPT-4o model hosted in Azure AI Foundry. It supports chat history with up to 10 interactions per session, allows starting new conversations, and handles multiple users via session IDs. The API is optimized for performance with connection pooling, caching, and detailed performance metrics.

## Prerequisites

- **Python**: Version 3.11 (recommended) or 3.9+.
- **Dependencies**: Install required packages from `requirements.txt`.
- **Azure OpenAI**: An Azure OpenAI resource with GPT-4o deployed.
- **SQLite**: Used for caching responses (included in Python standard library).

## Setup Instructions

### 1. Install Dependencies

Clone the repository or save the script as `app.py`, then install the required Python packages:

```bash
pip install -r requirements.txt
```

Contents of requirements.txt:

```text
flask==3.0.3
langchain>=0.3.20
langchain-openai==0.2.0
langchain-community==0.3.19
python-dotenv==1.0.1
httpx[http2]==0.28.1
h2==4.2.0
matplotlib==3.10.1
```

### 2. Create a .env File

The API uses environment variables for Azure OpenAI credentials. Create a .env file in the same directory as app.py with the following content:

```text
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-05-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your-deployment-name
```

- AZURE_OPENAI_API_KEY: Your Azure OpenAI API key (found in Azure Portal).
- AZURE_OPENAI_ENDPOINT: The endpoint URL for your Azure OpenAI resource.
- AZURE_OPENAI_API_VERSION: The API version (e.g., 2024-05-01-preview).
- AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: The name of your GPT-4o deployment.

Note: Do not commit the .env file to version control. Add it to .gitignore.

### 3. Run the API

Start the Flask server on port 3001:

```bash
python app.py
```

The API will be available at http://localhost:3001/ask.

## API Endpoint

- URL: /ask
- Method: POST
- Content-Type: application/json

## Performance Features

This API includes several optimizations to enhance performance:

1. **Connection Pooling**: Uses a persistent `httpx.Client` with HTTP/2 support to maintain connections to the Azure OpenAI API, reducing connection establishment overhead.

2. **Caching System**: Implements a SQLite-based caching mechanism to store responses for repeated queries, significantly reducing response times for previously asked questions.

3. **Session Management**: Enhanced session tracking with the ability to maintain conversation context across multiple requests.

4. **Performance Metrics**: Each response includes detailed performance data such as API call time, cache status, and connection reuse statistics.

5. **Background Processing**: Uses a thread pool for non-blocking background tasks like connection maintenance and cache updates.

### Request Parameters

The API expects a JSON payload with the following fields:

| Parameter        | Type    | Required | Description                                                                            |
| ---------------- | ------- | -------- | -------------------------------------------------------------------------------------- |
| question         | String  | Yes      | The question to ask GPT-4o.                                                            |
| session_id       | String  | No       | A unique identifier for the user's session. If omitted, a new one is generated.        |
| new_conversation | Boolean | No       | Set to true to clear the chat history and start a new conversation. Defaults to false. |

### Response Format

The API returns a JSON object with:

- answer: The response from GPT-4o.
- chat_history: An array of past interactions (up to 10) with role (human or ai) and content.
- session_id: The session ID used or generated for this request.
- status: "success" or an error message.
- performance_metrics: Detailed timing and connection information including:
  - api_call_time: Time spent calling the Azure OpenAI API (in seconds).
  - total_time: Total processing time (in seconds).
  - from_cache: Boolean indicating if the response was served from cache.
  - connection_reused: Boolean indicating if an existing connection was reused.
  - connection_stats: Statistics about connection pool usage.

Example response:

```json
{
  "answer": "The capital of France is Paris.",
  "chat_history": [
    {"role": "human", "content": "What is the capital of France?"},
    {"role": "ai", "content": "The capital of France is Paris."}
  ],
  "session_id": "user1",
  "status": "success",
  "performance_metrics": {
    "api_call_time": 0.62,
    "total_time": 0.65,
    "from_cache": false,
    "connection_reused": true,
    "connection_stats": {
      "avg_response_time": 0.58,
      "connection_reuse_count": 5,
      "reuse_percentage": 83.3,
      "total_requests": 6
    }
  }
}
```

### Testing with curl

1. Ask a Question (New Session)

   Start a new session without specifying a session_id:

```bash
curl -X POST http://localhost:3001/ask -H "Content-Type: application/json" -d '{"question": "What is the capital of France?"}'
```

Expected Response:

A new session_id will be generated (e.g., a UUID like "550e8400-e29b-41d4-a716-446655440000").

2. Continue a Conversation (Same User)

Reuse the session_id from the previous response to continue the conversation:

```bash
curl -X POST http://localhost:3001/ask -H "Content-Type: application/json" -d '{"question": "What about Spain?", "session_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

Expected Response:

```json
{
"answer": "The capital of Spain is Madrid.",
"chat_history": [
{"role": "human", "content": "What is the capital of France?"},
{"role": "ai", "content": "The capital of France is Paris."},
{"role": "human", "content": "What about Spain?"},
{"role": "ai", "content": "The capital of Spain is Madrid."}
],
"session_id": "550e8400-e29b-41d4-a716-446655440000",
"status": "success"
}
```

3. Start a New Conversation (Same User)

Clear the chat history for an existing session by setting new_conversation to true:

```bash
curl -X POST http://localhost:3001/ask -H "Content-Type: application/json" -d '{"question": "Hi there", "session_id": "550e8400-e29b-41d4-a716-446655440000", "new_conversation": true}'
```

Expected Response:

```json
{
"answer": "Hello!",
"chat_history": [
{"role": "human", "content": "Hi there"},
{"role": "ai", "content": "Hello!"}
],
"session_id": "550e8400-e29b-41d4-a716-446655440000",
"status": "success"
}
```

4. Multiple Users Example

Simulate two users with different session_ids:

User 1:

```bash
curl -X POST http://localhost:3001/ask -H "Content-Type: application/json" -d '{"question": "What is 2+2?", "session_id": "user1"}'
```

Response:

```json
{
"answer": "2 + 2 is 4.",
"chat_history": [
{"role": "human", "content": "What is 2+2?"},
{"role": "ai", "content": "2 + 2 is 4."}
],
"session_id": "user1",
"status": "success"
}
```

User 2:

```bash
curl -X POST http://localhost:3001/ask -H "Content-Type: application/json" -d '{"question": "What's the weather like?", "session_id": "user2"}'
```

Response:

```json
{
"answer": "I don't have real-time weather data, but can you tell me a specific location?",
"chat_history": [
{"role": "human", "content": "What's the weather like?"},
{"role": "ai", "content": "I don't have real-time weather data, but can you tell me a specific location?"}
],
"session_id": "user2",
"status": "success"
}
```

User 1 Continues:

```bash
curl -X POST http://localhost:3001/ask -H "Content-Type: application/json" -d '{"question": "What is 3+3?", "session_id": "user1"}'
```

## Performance Testing

The repository includes a test script (`test_api.py`) to evaluate the API's performance:

```bash
python test_api.py --requests 10 --delay 1 --test-cache
```

Options:
- `--requests`: Number of requests to send (default: 5)
- `--delay`: Delay between requests in seconds (default: 1)
- `--test-cache`: Test cache performance by sending identical requests
- `--test-session`: Test session performance by using the same session ID
- `--question`: Custom question to ask (default: about capital of France)

The script generates a performance plot (`performance_results.png`) and provides detailed statistics on request performance, including cache hit rates and response times.
