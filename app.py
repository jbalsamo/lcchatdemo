# Import necessary libraries
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os
import argparse
import sys
import time
import concurrent.futures
from typing import Dict, Tuple, Any
import httpx
from langchain_core.globals import set_llm_cache
from langchain_community.cache import InMemoryCache

# Load environment variables from .env file
load_dotenv()

# Enable LangChain caching to reuse responses
set_llm_cache(InMemoryCache())

# Create a persistent httpx client for connection reuse
# This will keep connections alive between requests
persistent_client = httpx.Client(
    limits=httpx.Limits(
        max_keepalive_connections=10,  # Number of connections to keep alive
        max_connections=100,           # Maximum number of connections
        keepalive_expiry=300          # Keep connections alive for 5 minutes
    ),
    timeout=30.0,                     # Set timeout to 30 seconds
    follow_redirects=True             # Follow redirects automatically
)

# Section 1: Configure and Validate Azure OpenAI Environment Variables
required_vars = {
    "AZURE_OPENAI_API_KEY": "API key",
    "AZURE_OPENAI_ENDPOINT": "endpoint",
    "AZURE_OPENAI_API_VERSION": "API version",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "deployment name"
}
for var, desc in required_vars.items():
    if not os.getenv(var):
        print(f"Error: Missing {desc} in environment variables. Check your .env file.")
        sys.exit(1)

# Section 2: Initialize the Azure OpenAI Model with LangChain
try:
    llm = AzureChatOpenAI(
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        temperature=0.7,
        max_tokens=500,
        streaming=True,
        request_timeout=30,  # Set a timeout to prevent hanging requests
        http_client=persistent_client,  # Use our persistent httpx client
        cache=True  # Enable caching for repeated queries
    )
except Exception as e:
    print(f"Error: Failed to initialize AzureChatOpenAI: {str(e)}")
    sys.exit(1)

# Section 3: Define a Simple Prompt Template
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant providing concise and accurate answers."),
    ("human", "{question}")
])

# Section 4: Create a Chain
chain = prompt_template | llm | StrOutputParser()

# Section 5: Define timing functions and performance metrics
class TimingStats:
    def __init__(self):
        self.api_call_time = 0.0
        self.processing_time = 0.0
        self.total_time = 0.0
        self.token_count = 0
        self.tokens_per_second = 0.0

# Function to preload the model (warm-up)
def warm_up_model():
    """
    Send a simple request to warm up the model and establish connection.
    This keeps the connection alive for subsequent requests.
    """
    try:
        # Make a real but simple query to warm up the connection
        print("Warming up connection...", end="", flush=True)
        warm_up_chain = prompt_template | llm | StrOutputParser()
        # Use a very simple query that should be fast to process
        _ = warm_up_chain.invoke({"question": "Hello"})
        print(" Done", flush=True)
        return True
    except Exception as e:
        print(f" Failed: {str(e)}")
        return False

# Define the function to ask a question
def ask_question(question, stream_delay=0.0):
    """
    Function to ask a question to GPT-4o.
    Args:
        question: The question to ask
        stream_delay: Delay between chunks for streaming visibility (set to 0 for max performance)
    Streams:
        The model's response as it's generated
    Returns:
        Tuple of (full_response, timing_stats)
    """
    timing_stats = TimingStats()

    try:
        # Start the total timer
        total_start_time = time.time()

        # Print a cursor to indicate streaming is starting
        print("Answer: ", end="", flush=True)

        # Start the API call timer
        api_call_start = time.time()

        # Stream the response
        full_response = ""
        chunk_count = 0

        # Use a separate thread for processing to avoid blocking
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: list(chain.stream({"question": question})))

            # Get the first chunk to measure initial response time
            try:
                chunks = future.result(timeout=30)  # Set a timeout to prevent hanging
                timing_stats.api_call_time = time.time() - api_call_start

                # Process all chunks
                for chunk in chunks:
                    print(chunk, end="", flush=True)
                    full_response += chunk
                    chunk_count += 1

                    # Optional delay for visibility (set to 0 for max performance)
                    if stream_delay > 0:
                        time.sleep(stream_delay)
            except concurrent.futures.TimeoutError:
                print("\nError: Request timed out. Please try again.")
                sys.exit(1)

        # Calculate processing time (time after first chunk received)
        timing_stats.processing_time = time.time() - (api_call_start + timing_stats.api_call_time)

        # Calculate total time
        timing_stats.total_time = time.time() - total_start_time

        # Estimate token count (rough approximation: 4 chars ≈ 1 token)
        timing_stats.token_count = len(full_response) // 4

        # Calculate tokens per second if processing time > 0
        if timing_stats.processing_time > 0:
            timing_stats.tokens_per_second = timing_stats.token_count / timing_stats.processing_time

        # Return the full response and timing statistics
        return full_response, timing_stats
    except Exception as e:
        print(f"\nError: Unexpected error: {type(e).__name__}: {str(e)}")
        sys.exit(1)

# Section 6: Parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='Ask a question to GPT-4o')
    parser.add_argument('question', type=str, help='The question to ask')
    return parser.parse_args()

# Section 7: Main function
def main():
    args = parse_args()

    # Always warm-up the connection to reduce latency
    # This establishes and keeps the connection alive
    warm_up_model()

    print(f"Question: {args.question}")

    # The answer is printed in the ask_question function as it streams
    # Set stream_delay to 0 for maximum performance
    _, timing_stats = ask_question(args.question, stream_delay=0.0)

    # Add a newline and display detailed timing information
    print(f"\n\nPerformance Metrics:")
    print(f"  Initial response time: {timing_stats.api_call_time:.2f} seconds")
    print(f"  Content generation time: {timing_stats.processing_time:.2f} seconds")
    print(f"  Total time: {timing_stats.total_time:.2f} seconds")
    print(f"  Estimated tokens: {timing_stats.token_count}")
    print(f"  Generation speed: {timing_stats.tokens_per_second:.2f} tokens/second")

    # Note: Connection is kept alive for future API calls
    # The persistent_session will maintain the connection pool

if __name__ == '__main__':
    main()