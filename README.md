# Flask API with LangChain and Azure OpenAI

This is a REST API built with Flask and LangChain to interact with the GPT-4o model hosted in Azure AI Foundry. It supports chat history with up to 10 interactions per session, allows starting new conversations, and handles multiple users via session IDs.

## Prerequisites

- **Python**: Version 3.11 (recommended) or 3.9+.
- **Dependencies**: Install required packages from `requirements.txt`.
- **Azure OpenAI**: An Azure OpenAI resource with GPT-4o deployed.

## Setup Instructions

### 1. Install Dependencies

Clone the repository or save the script as `app.py`, then install the required Python packages:

```bash
pip install -r requirements.txt
```

Contents of requirements.txt:

```text
flask==3.0.3
langchain==0.3.0
langchain-openai==0.2.0
python-dotenv==1.0.1
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

Start the Flask server on port 3000:

```bash
python app.py
```

The API will be available at http://localhost:3000/ask.

## API Endpoint

- URL: /ask
- Method: POST
- Content-Type: application/json

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

Example response:

```json
{
  "answer": "The capital of France is Paris.",
  "chat_history": [
    {"role": "human", "content": "What is the capital of France?"},
    {"role": "ai", "content": "The capital of France is Paris."}
  ],
  "session_id": "user1",
  "status": "success"
}
```

### Testing with curl

1. Ask a Question (New Session)

   Start a new session without specifying a session_id:

```bash
curl -X POST http://localhost:3000/ask -H "Content-Type: application/json" -d '{"question": "What is the capital of France?"}'
```

Expected Response:

A new session_id will be generated (e.g., a UUID like "550e8400-e29b-41d4-a716-446655440000").

2. Continue a Conversation (Same User)

Reuse the session_id from the previous response to continue the conversation:

```bash
curl -X POST http://localhost:3000/ask -H "Content-Type: application/json" -d '{"question": "What about Spain?", "session_id": "550e8400-e29b-41d4-a716-446655440000"}'
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
curl -X POST http://localhost:3000/ask -H "Content-Type: application/json" -d '{"question": "Hi there", "session_id": "550e8400-e29b-41d4-a716-446655440000", "new_conversation": true}'
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
curl -X POST http://localhost:3000/ask -H "Content-Type: application/json" -d '{"question": "What is 2+2?", "session_id": "user1"}'
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
curl -X POST http://localhost:3000/ask -H "Content-Type: application/json" -d '{"question": "What’s the weather like?", "session_id": "user2"}'
```

Response:

```json
{
"answer": "I don’t have real-time weather data, but can you tell me a specific location?",
"chat_history": [
{"role": "human", "content": "What’s the weather like?"},
{"role": "ai", "content": "I don’t have real-time weather data, but can you tell me a specific location?"}
],
"session_id": "user2",
"status": "success"
}
```

User 1 Continues:

```bash
curl -X POST http://localhost:3000/ask -H "Content-Type: application/json" -d '{"question": "What is 3+3?", "session_id": "user1"}'
```

Response:

```json
{
  "answer": "3 + 3 is 6.",
  "chat_history": [
    {"role": "human", "content": "What is 2+2?"},
    {"role": "ai", "content": "2 + 2 is 4."},
    {"role": "human", "content": "What is 3+3?"},
    {"role": "ai", "content": "3 + 3 is 6."}
  ],
  "session_id": "user1",
  "status": "success"
}
```

### Notes

- Port: The API runs on port 3000. Ensure this port is free on your machine.

- Session Persistence: Chat history is stored in memory and resets when the app restarts. For production, consider using a database or Redis.

- Error Handling: If a request fails (e.g., missing question), the API returns a 400 or 500 status with an error message.

### Troubleshooting

- API Not Responding: Check the console for errors (e.g., invalid Azure credentials).

- History Not Updating: Verify the session_id is consistent across requests.

- Port Conflict: Use netstat -tuln | grep 3000 (Linux/Mac) or netstat -aon | findstr 3000 (Windows) to ensure port 3000 is available.

Enjoy using the API!
