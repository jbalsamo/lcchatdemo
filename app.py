# Import necessary libraries
from flask import Flask, request, jsonify
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from dotenv import load_dotenv
import os
import uuid  # For generating unique session IDs
import httpx
import time
import threading
import functools
from langchain_core.globals import set_llm_cache
from langchain_community.cache import InMemoryCache, SQLiteCache
from concurrent.futures import ThreadPoolExecutor

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Use SQLite cache for persistent caching across restarts
# This provides better performance for repeated queries
sqlite_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'langchain_cache.db')
set_llm_cache(SQLiteCache(database_path=sqlite_cache_path))

# Create a persistent httpx client for connection pooling
# This will be shared across all requests to maintain connection pooling
persistent_client = httpx.Client(
    limits=httpx.Limits(
        max_keepalive_connections=100,  # Further increased connections to keep alive
        max_connections=300,            # Further increased maximum connections
        keepalive_expiry=3600          # Keep connections alive for 1 hour
    ),
    timeout=60.0,                      # Set timeout to 60 seconds
    follow_redirects=True,             # Follow redirects automatically
    http2=True,                        # Enable HTTP/2 for better performance
    transport=httpx.HTTPTransport(retries=3)  # Add automatic retries
)

# Create a thread pool executor for background tasks
thread_pool = ThreadPoolExecutor(max_workers=10)

# Track connection statistics
connection_stats = {
    "total_requests": 0,
    "connection_reuse_count": 0,
    "last_request_time": None,
    "avg_response_time": 0
}

# Section 1: Configure and Validate Azure OpenAI Environment Variables
required_vars = {
    "AZURE_OPENAI_API_KEY": "API key",
    "AZURE_OPENAI_ENDPOINT": "endpoint",
    "AZURE_OPENAI_API_VERSION": "API version",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "deployment name"
}
for var, desc in required_vars.items():
    if not os.getenv(var):
        raise ValueError(f"Missing {desc} in environment variables. Check your .env file.")

# Section 2: Initialize the Azure OpenAI Model with LangChain
try:
    llm = AzureChatOpenAI(
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        temperature=0.7,
        max_tokens=500,
        http_client=persistent_client,  # Use our persistent httpx client
        request_timeout=60,            # Set a timeout to prevent hanging requests
        cache=True,                    # Enable caching for repeated queries
        streaming=False,               # Disable streaming for faster responses
        max_retries=3                  # Add retries for resilience
    )
except Exception as e:
    raise RuntimeError(f"Failed to initialize AzureChatOpenAI: {str(e)}")

# Section 3: Set Up a Dictionary to Store Session Memories
session_memories = {}  # Key: session_id, Value: ConversationBufferWindowMemory

# Section 4: Define a Prompt Template with Chat History
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant providing concise and accurate answers."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

# Section 5: Create a Chain
chain = prompt_template | llm

# Helper function to get or create a memory instance for a session
def get_session_memory(session_id):
    if session_id not in session_memories:
        session_memories[session_id] = ConversationBufferWindowMemory(
            k=10, return_messages=True
        )
    return session_memories[session_id]

# Function to warm up the connection
def warm_up_connection():
    """
    Send a simple request to warm up the model and establish connection.
    This keeps the connection alive for subsequent requests.
    """
    try:
        # Make a real but simple query to warm up the connection
        print("Warming up connection...")
        start_time = time.time()
        warm_up_chain = prompt_template | llm
        
        # Send multiple warm-up requests in parallel to establish multiple connections
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):  # Create 5 parallel connections
                futures.append(executor.submit(
                    warm_up_chain.invoke, 
                    {"question": f"Hello {i}", "history": []}
                ))
            
            # Wait for all futures to complete
            for future in futures:
                future.result()
        
        duration = time.time() - start_time
        print(f"Connection warm-up complete in {duration:.2f} seconds (5 parallel connections established)")
        
        # Initialize connection stats
        connection_stats["last_request_time"] = time.time()
        connection_stats["avg_response_time"] = duration / 5  # Average per connection
        return True
    except Exception as e:
        print(f"Connection warm-up failed: {str(e)}")
        return False

# Function to maintain connection pool
def maintain_connection_pool():
    """
    Periodically sends a keep-alive request to maintain the connection pool.
    This should be called in a separate thread or process.
    """
    try:
        # Only send a keep-alive if it's been more than 2 minutes since the last request
        current_time = time.time()
        if connection_stats["last_request_time"] and \
           (current_time - connection_stats["last_request_time"]) > 120:  # 2 minutes
            print("Sending keep-alive request to maintain connection pool...")
            # Use a lightweight keep-alive request
            thread_pool.submit(warm_up_connection)
            print("Connection pool maintenance initiated")
        return True
    except Exception as e:
        print(f"Connection pool maintenance failed: {str(e)}")
        return False

# Start a background thread to periodically maintain the connection pool
def start_connection_maintenance():
    """Start a background thread to maintain the connection pool"""
    def maintenance_worker():
        while True:
            maintain_connection_pool()
            time.sleep(60)  # Check every minute
    
    maintenance_thread = threading.Thread(target=maintenance_worker, daemon=True)
    maintenance_thread.start()
    print("Connection maintenance thread started")

# Warm up the connection when the application starts
warm_up_connection()

# Start the connection maintenance thread
start_connection_maintenance()

# Create a request cache for common queries
query_cache = {}

# Function to cache responses for identical queries
def get_cached_response(question, session_id=None):
    """Get a cached response for a question if available"""
    cache_key = f"{question}_{session_id if session_id else 'no_session'}"
    if cache_key in query_cache:
        print(f"Cache hit for question: {question}")
        return query_cache[cache_key]
    return None

def cache_response(question, response, session_id=None):
    """Cache a response for future use"""
    cache_key = f"{question}_{session_id if session_id else 'no_session'}"
    query_cache[cache_key] = response
    # Limit cache size to prevent memory issues
    if len(query_cache) > 1000:  # Limit to 1000 entries
        # Remove oldest entry
        oldest_key = next(iter(query_cache))
        del query_cache[oldest_key]

# Decorator for timing API calls
def timing_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Function {func.__name__} took {end_time - start_time:.2f} seconds to execute")
        return result
    return wrapper

# Section 6: Define the REST API Endpoint
@app.route('/ask', methods=['POST'])
@timing_decorator
def ask_question():
    """
    REST API endpoint to ask a question to GPT-4o with chat history.
    Expects a JSON payload with 'question' and optional 'session_id' and 'new_conversation' fields.
    Returns the model's response, updated chat history, and session_id as JSON.
    """
    try:
        # Start timing the request
        start_time = time.time()
        
        # Update connection stats
        connection_stats["total_requests"] += 1
        
        # Get JSON data from the request
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Missing 'question' in request body"}), 400

        # Extract fields from the request
        question = data['question']
        session_id = data.get('session_id', str(uuid.uuid4()))  # Generate new session_id if not provided
        new_conversation = data.get('new_conversation', False)  # Default to False
        bypass_cache = data.get('bypass_cache', False)  # Option to bypass cache

        # Check for cached response first (if not bypassing cache)
        if not bypass_cache and not new_conversation:
            cached_response = get_cached_response(question, session_id)
            if cached_response:
                # Update timing for cached response
                total_time = time.time() - start_time
                cached_response["performance"]["total_time"] = round(total_time, 2)
                cached_response["performance"]["from_cache"] = True
                print(f"Returning cached response for question: {question}")
                return jsonify(cached_response), 200

        # Get or create the memory for this session
        memory = get_session_memory(session_id)

        # If new_conversation is True, clear the memory
        if new_conversation:
            memory.clear()
            print(f"Cleared history for session_id: {session_id}")

        # Load the current chat history from memory
        memory_vars = memory.load_memory_variables({})
        chat_history = memory_vars.get("history", [])
        print(f"Chat History before invoke (session {session_id}):", chat_history)

        # Ensure chat_history is a list
        if not isinstance(chat_history, list):
            chat_history = []
            
        # Record API call start time
        api_call_start = time.time()
        
        # Check if we're reusing a connection
        is_connection_reuse = connection_stats["last_request_time"] is not None and \
                            (time.time() - connection_stats["last_request_time"]) < 600  # 10 minutes
        
        if is_connection_reuse:
            connection_stats["connection_reuse_count"] += 1
            print("Reusing existing connection")

        # Invoke the chain with the user's question and chat history
        # Use a shorter timeout for faster response
        response = chain.invoke({
            "question": question,
            "history": chat_history
        })
        
        # Calculate API call time
        api_call_time = time.time() - api_call_start
        
        # Update connection stats
        connection_stats["last_request_time"] = time.time()
        # Update rolling average of response time
        connection_stats["avg_response_time"] = (connection_stats["avg_response_time"] * 
                                             (connection_stats["total_requests"] - 1) + 
                                             api_call_time) / connection_stats["total_requests"]
        
        print(f"Response (session {session_id}):", response.content)
        print(f"API call time: {api_call_time:.2f} seconds")
        print(f"Connection reuse: {is_connection_reuse}")

        # Save the question and answer to memory
        memory.save_context(
            {"input": question},
            {"output": response.content}
        )

        # Fetch the updated chat history
        updated_history = memory.load_memory_variables({}).get("history", [])
        print(f"Updated Chat History (session {session_id}):", updated_history)

        # Calculate total processing time
        total_time = time.time() - start_time
        
        # Prepare the response object
        response_obj = {
            "answer": response.content,
            "chat_history": [
                {"role": msg.type, "content": msg.content}
                for msg in updated_history
            ],
            "session_id": session_id,  # Return session_id for client to reuse
            "status": "success",
            "performance": {
                "api_call_time": round(api_call_time, 2),
                "total_time": round(total_time, 2),
                "connection_reused": is_connection_reuse,
                "from_cache": False,
                "connection_stats": {
                    "total_requests": connection_stats["total_requests"],
                    "connection_reuse_count": connection_stats["connection_reuse_count"],
                    "reuse_percentage": round(connection_stats["connection_reuse_count"] / 
                                           max(1, connection_stats["total_requests"] - 1) * 100, 2),
                    "avg_response_time": round(connection_stats["avg_response_time"], 2)
                }
            }
        }
        
        # Cache the response for future use (in the background)
        thread_pool.submit(cache_response, question, response_obj, session_id)
        
        # Schedule a background task to maintain the connection pool
        thread_pool.submit(maintain_connection_pool)
        
        return jsonify(response_obj), 200

    except KeyError as e:
        return jsonify({"error": f"KeyError: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {type(e).__name__}: {str(e)}"}), 500

# Route to get connection pool statistics
@app.route('/stats', methods=['GET'])
def get_stats():
    """Return statistics about the connection pool"""
    return jsonify({
        "total_requests": connection_stats["total_requests"],
        "connection_reuse_count": connection_stats["connection_reuse_count"],
        "reuse_percentage": round(connection_stats["connection_reuse_count"] / 
                               max(1, connection_stats["total_requests"] - 1) * 100, 2),
        "avg_response_time": round(connection_stats["avg_response_time"], 2),
        "last_request_time": connection_stats["last_request_time"],
        "time_since_last_request": round(time.time() - (connection_stats["last_request_time"] or time.time()), 2) if connection_stats["last_request_time"] else None
    })

# Preload common questions to warm up the cache
def preload_common_questions():
    """Preload common questions into the cache"""
    common_questions = [
        "What is the capital of France?",
        "Hello",
        "How are you?"
    ]
    
    print("Preloading common questions into cache...")
    for question in common_questions:
        try:
            # Use a separate thread to avoid blocking startup
            thread_pool.submit(
                lambda q: chain.invoke({"question": q, "history": []}),
                question
            )
        except Exception as e:
            print(f"Error preloading question '{question}': {str(e)}")
    print("Preloading initiated in background")

# Section 7: Run the Flask Application
if __name__ == '__main__':
    # Configure Flask for optimal performance
    app.config['JSON_SORT_KEYS'] = False  # Preserve JSON order for faster serialization
    app.config['PROPAGATE_EXCEPTIONS'] = True  # Better error handling
    
    # Preload common questions in the background
    preload_common_questions()
    
    # Start the Flask server on port 3000 with threaded=True for better concurrency
    # The threaded option allows the server to handle multiple requests simultaneously
    # which works well with our connection pooling implementation
    app.run(
        host='0.0.0.0', 
        port=3001, 
        debug=True, 
        threaded=True,
        use_reloader=False  # Disable reloader for better performance
    )