# Command-Line Interface with LangChain and Azure OpenAI

This is a command-line tool built with LangChain to interact with the GPT-4o model hosted in Azure AI Foundry. It allows you to ask questions directly from the terminal and receive answers from the AI model.

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

### 3. Run the Command-Line Tool

Use the script with a question as an argument:

```bash
python app.py "What is the capital of France?"
```

The answer will be displayed in the console.

## Command-Line Usage

### Arguments

The command-line tool accepts the following arguments:

| Argument  | Type   | Required | Description                  |
| --------- | ------ | -------- | ---------------------------- |
| question  | String | Yes      | The question to ask GPT-4o.  |

### Output Format

The tool will print both the question and the answer to the console:

```
Question: What is the capital of France?
Answer: The capital of France is Paris.
```

### Examples

1. Ask a Simple Question

```bash
python app.py "What is the capital of France?"
```

Output:
```
Question: What is the capital of France?
Answer: The capital of France is Paris.
```

2. Ask a More Complex Question

```bash
python app.py "What are the main differences between Python and JavaScript?"
```

Output:
```
Question: What are the main differences between Python and JavaScript?
Answer: Python and JavaScript have several key differences:

1. Use cases: Python is primarily used for backend development, data analysis, AI, and scientific computing, while JavaScript was originally designed for web browsers but now also runs on servers (Node.js).

2. Typing: Python uses dynamic typing but is strongly typed, while JavaScript is both dynamically and weakly typed.

3. Syntax: Python uses indentation for code blocks and emphasizes readability, while JavaScript uses curly braces and semicolons.

4. Execution: Python is typically compiled to bytecode and then interpreted, while JavaScript is interpreted directly by browsers or Node.js.

5. Concurrency: JavaScript uses an event-driven, non-blocking I/O model with a single thread and asynchronous callbacks, while Python traditionally uses threads or processes for concurrency (though it also supports async/await).

6. Libraries: Python has extensive libraries for scientific computing and data analysis, while JavaScript has a vast ecosystem for web development.
```

3. Ask for Code Examples

```bash
python app.py "How do I read a file in Python?"
```

Output:
```
Question: How do I read a file in Python?
Answer: Here's how to read a file in Python:

```python
# Method 1: Read entire file as a string
with open('filename.txt', 'r') as file:
    content = file.read()
    print(content)

# Method 2: Read line by line
with open('filename.txt', 'r') as file:
    for line in file:
        print(line.strip())

# Method 3: Read all lines into a list
with open('filename.txt', 'r') as file:
    lines = file.readlines()
    for line in lines:
        print(line.strip())
```

The `with` statement ensures the file is properly closed after reading. The 'r' parameter indicates read mode.
```
