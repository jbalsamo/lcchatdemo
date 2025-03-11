#!/usr/bin/env python
import requests
import time
import json
import argparse
import statistics
import uuid
import matplotlib.pyplot as plt

def test_api(num_requests=5, delay_between_requests=1, test_cache=False, test_session=False, question=None):
    """
    Test the API performance by sending multiple requests.

    Args:
        num_requests: Number of requests to send
        delay_between_requests: Delay between requests in seconds
        test_cache: Whether to test cache performance by sending identical requests
        test_session: Whether to test session performance by using the same session ID
        question: Custom question to ask (default: about capital of France)
    """
    url = "http://localhost:3001/ask"
    
    # Use a fixed session ID if testing session performance
    session_id = str(uuid.uuid4()) if test_session else None
    
    # Default question if none provided
    if not question:
        question = "What is the capital of France?"
    
    # Store performance metrics
    api_call_times = []
    total_times = []
    client_times = []
    from_cache = []
    connection_reused = []
    
    for i in range(num_requests):
        print(f"\nRequest {i+1}/{num_requests}")

        # Prepare the request payload
        payload = {
            "question": question
        }

        # Add session_id if testing session performance
        if session_id:
            payload["session_id"] = session_id
            print(f"Using session ID: {session_id}")
            
        # Option to bypass cache for specific tests
        if i == 0 and test_cache:
            payload["bypass_cache"] = True
            print("First request bypassing cache to establish baseline")

        # Send the request and measure time
        client_start = time.time()
        response = requests.post(url, json=payload)
        client_time = time.time() - client_start

        # Process the response
        if response.status_code == 200:
            data = response.json()
            if not session_id:
                session_id = data.get("session_id")

            # Extract timing and performance information
            performance = data.get("performance", {})
            api_call_time = performance.get("api_call_time", 0)
            total_time = performance.get("total_time", 0)
            is_from_cache = performance.get("from_cache", False)
            is_connection_reused = performance.get("connection_reused", False)
            
            # Store metrics
            api_call_times.append(api_call_time)
            total_times.append(total_time)
            client_times.append(client_time)
            from_cache.append(is_from_cache)
            connection_reused.append(is_connection_reused)

            print(f"Answer: {data.get('answer')}")
            print(f"API call time: {api_call_time:.2f} seconds")
            print(f"Total time: {total_time:.2f} seconds")
            print(f"Request time (measured client-side): {client_time:.2f} seconds")
            print(f"From cache: {is_from_cache}")
            print(f"Connection reused: {is_connection_reused}")
            
            # Display connection stats if available
            if 'connection_stats' in performance:
                conn_stats = performance['connection_stats']
                print(f"Connection stats: {json.dumps(conn_stats, indent=2)}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

        # Wait before the next request
        if i < num_requests - 1:
            print(f"Waiting {delay_between_requests} seconds before next request...")
            time.sleep(delay_between_requests)

    # Print summary statistics
    if api_call_times:
        print("\n===== Performance Summary =====")
        print(f"Number of requests: {num_requests}")
        print(f"Testing cache: {test_cache}")
        print(f"Testing session: {test_session}")
        print(f"Question: {question}")
        print()
        
        # Calculate cache hits and connection reuses
        cache_hits = sum(from_cache)
        connection_reuses = sum(connection_reused)
        
        print(f"Cache hits: {cache_hits}/{num_requests} ({cache_hits/num_requests*100:.2f}%)")
        print(f"Connection reuses: {connection_reuses}/{num_requests} ({connection_reuses/num_requests*100:.2f}%)")
        print()

        # First request time (cold start)
        print(f"First request:")
        print(f"  API call time: {api_call_times[0]:.2f} seconds")
        print(f"  Total time: {total_times[0]:.2f} seconds")
        print(f"  Client time: {client_times[0]:.2f} seconds")
        print()
        
        # Separate cached and non-cached responses for analysis
        cached_times = [t for i, t in enumerate(total_times) if from_cache[i]]
        non_cached_times = [t for i, t in enumerate(total_times) if not from_cache[i]]
        
        # Analyze cached responses
        print("Cached responses:")
        if cached_times:
            print(f"  Count: {len(cached_times)}")
            print(f"  Average time: {statistics.mean(cached_times):.2f} seconds")
            print(f"  Min time: {min(cached_times):.2f} seconds")
            print(f"  Max time: {max(cached_times):.2f} seconds")
        else:
            print("  No cached responses")
        
        # Analyze non-cached responses
        print("\nNon-cached responses:")
        if len(non_cached_times) > 1:  # Skip first request for comparison
            subsequent_non_cached = non_cached_times[1:] if non_cached_times[0] == total_times[0] else non_cached_times
            if subsequent_non_cached:
                # Get API call times for non-cached subsequent requests
                subsequent_api_times = [t for i, t in enumerate(api_call_times[1:]) if not from_cache[i+1]]
                
                if subsequent_api_times:
                    avg_api_call_time = statistics.mean(subsequent_api_times)
                    avg_total_time = statistics.mean(subsequent_non_cached)
                    min_total_time = min(subsequent_non_cached)
                    max_total_time = max(subsequent_non_cached)
                    
                    print(f"  Average API call time: {avg_api_call_time:.2f} seconds")
                    print(f"  Average total time: {avg_total_time:.2f} seconds")
                    print(f"  Min time: {min_total_time:.2f} seconds")
                    print(f"  Max time: {max_total_time:.2f} seconds")
                    
                    # Calculate performance improvement
                    if api_call_times[0] > 0:
                        improvement = ((api_call_times[0] - avg_api_call_time) / api_call_times[0]) * 100
                        print(f"\nPerformance improvement: {improvement:.2f}% faster API call time compared to first request")
            else:
                print("  No subsequent non-cached responses")
        else:
            print("  Not enough non-cached responses for analysis")
        
        # Generate performance plot
        try:
            plt.figure(figsize=(12, 8))
            
            # Plot 1: Response times
            plt.subplot(2, 2, 1)
            x = range(1, len(total_times) + 1)
            plt.plot(x, api_call_times, 'b-', label='API Call Time')
            plt.plot(x, total_times, 'r-', label='Total Time')
            plt.plot(x, client_times, 'g-', label='Client Time')
            plt.xlabel('Request Number')
            plt.ylabel('Time (seconds)')
            plt.title('Response Times')
            plt.legend()
            plt.grid(True)
            
            # Plot 2: Cache vs Non-cache comparison
            plt.subplot(2, 2, 2)
            labels = ['Cached', 'Non-cached']
            counts = [cache_hits, num_requests - cache_hits]
            plt.bar(labels, counts, color=['green', 'blue'])
            plt.ylabel('Count')
            plt.title('Cache Hits vs Misses')
            
            # Plot 3: Connection reuse
            plt.subplot(2, 2, 3)
            labels = ['Reused', 'New Connection']
            counts = [connection_reuses, num_requests - connection_reuses]
            plt.bar(labels, counts, color=['purple', 'orange'])
            plt.ylabel('Count')
            plt.title('Connection Reuse')
            
            # Plot 4: Performance comparison
            plt.subplot(2, 2, 4)
            categories = ['First Request', 'Subsequent (Avg)', 'Cached (Avg)', 'Min Time', 'Max Time']
            values = [
                api_call_times[0],
                statistics.mean(api_call_times[1:]) if len(api_call_times) > 1 else 0,
                statistics.mean(cached_times) if cached_times else 0,
                min(api_call_times) if api_call_times else 0,
                max(api_call_times) if api_call_times else 0
            ]
            plt.bar(categories, values, color=['red', 'blue', 'green', 'cyan', 'magenta'])
            plt.ylabel('Time (seconds)')
            plt.title('Performance Comparison')
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            plt.savefig('performance_results.png')
            print("\nPerformance plot saved to 'performance_results.png'")
        except Exception as e:
            print(f"Could not generate performance plot: {str(e)}")

def parse_args():
    parser = argparse.ArgumentParser(description='Test the API performance')
    parser.add_argument('--requests', type=int, default=5, help='Number of requests to send')
    parser.add_argument('--delay', type=float, default=1, help='Delay between requests in seconds')
    parser.add_argument('--test-cache', action='store_true', help='Test cache performance by sending identical requests')
    parser.add_argument('--test-session', action='store_true', help='Test session performance by using the same session ID')
    parser.add_argument('--question', type=str, help='Custom question to ask')
    parser.add_argument('--plot', action='store_true', help='Generate performance plots')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    test_api(
        num_requests=args.requests, 
        delay_between_requests=args.delay,
        test_cache=args.test_cache,
        test_session=args.test_session,
        question=args.question
    )
