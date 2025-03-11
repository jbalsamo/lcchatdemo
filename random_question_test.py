#!/usr/bin/env python
import requests
import time
import random
import uuid
import argparse
from datetime import datetime

def test_api_with_random_questions(num_requests=10, delay_between_requests=1):
    """
    Test the API with random questions across multiple session IDs.
    
    Args:
        num_requests: Number of total API calls to make
        delay_between_requests: Delay between requests in seconds
    """
    url = "http://localhost:3001/ask"
    
    # Create 5 session IDs for different users
    session_ids = {
        f"user{i+1}": str(uuid.uuid4()) for i in range(5)
    }
    
    # List of random questions
    questions = [
        "What is machine learning?",
        "How does a neural network work?",
        "Explain the concept of blockchain.",
        "What are the benefits of cloud computing?",
        "How does natural language processing work?",
        "What is the difference between AI and machine learning?",
        "Explain quantum computing in simple terms.",
        "What are microservices in software architecture?",
        "How does containerization improve deployment?",
        "What is the role of DevOps in software development?"
    ]
    
    # Select two questions to repeat across sessions
    repeated_questions = random.sample(questions, 2)
    print(f"Selected questions to repeat: \n1. {repeated_questions[0]}\n2. {repeated_questions[1]}\n")
    
    # Track performance metrics
    results = []
    
    print(f"Starting API test with {num_requests} requests across 5 user sessions...")
    print(f"API endpoint: {url}")
    print("-" * 80)
    
    for i in range(num_requests):
        # Select a random user
        user = f"user{random.randint(1, 5)}"
        session_id = session_ids[user]
        
        # Decide whether to use a repeated question (40% chance)
        if random.random() < 0.4:
            question = random.choice(repeated_questions)
            question_type = "Repeated"
        else:
            # Choose a non-repeated question
            available_questions = [q for q in questions if q not in repeated_questions]
            question = random.choice(available_questions)
            question_type = "Unique"
        
        print(f"\nRequest {i+1}/{num_requests}")
        print(f"User: {user} (Session ID: {session_id[:8]}...)")
        print(f"Question Type: {question_type}")
        print(f"Question: {question}")

        # Prepare the request payload
        payload = {
            "question": question,
            "session_id": session_id
        }

        # Send the request and measure time
        start_time = time.time()
        try:
            response = requests.post(url, json=payload, timeout=60)
            request_time = time.time() - start_time
            
            # Process the response
            if response.status_code == 200:
                data = response.json()
                
                # Extract performance information
                performance = data.get("performance", {})
                api_call_time = performance.get("api_call_time", 0)
                total_time = performance.get("total_time", 0)
                is_from_cache = performance.get("from_cache", False)
                
                print(f"Status: Success (HTTP {response.status_code})")
                print(f"API call time: {api_call_time:.2f}s")
                print(f"Total time: {total_time:.2f}s")
                print(f"Client time: {request_time:.2f}s")
                print(f"From cache: {is_from_cache}")
                print(f"Answer: {data.get('answer')[:100]}..." if len(data.get('answer', '')) > 100 else f"Answer: {data.get('answer')}")
                
                # Store result
                results.append({
                    "request_num": i+1,
                    "user": user,
                    "session_id": session_id,
                    "question": question,
                    "question_type": question_type,
                    "api_call_time": api_call_time,
                    "total_time": total_time,
                    "client_time": request_time,
                    "from_cache": is_from_cache,
                    "status": "Success"
                })
            else:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                
                # Store error result
                results.append({
                    "request_num": i+1,
                    "user": user,
                    "session_id": session_id,
                    "question": question,
                    "question_type": question_type,
                    "status": f"Error: HTTP {response.status_code}"
                })
        except Exception as e:
            print(f"Exception: {str(e)}")
            
            # Store exception result
            results.append({
                "request_num": i+1,
                "user": user,
                "session_id": session_id,
                "question": question,
                "question_type": question_type,
                "status": f"Exception: {str(e)}"
            })

        # Wait before the next request
        if i < num_requests - 1:
            print(f"Waiting {delay_between_requests} seconds before next request...")
            time.sleep(delay_between_requests)

    # Print summary statistics
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    # Calculate statistics
    total_success = sum(1 for r in results if r["status"] == "Success")
    cache_hits = sum(1 for r in results if r.get("from_cache", False))
    
    # Calculate average times for successful requests
    successful_results = [r for r in results if r["status"] == "Success"]
    if successful_results:
        avg_api_time = sum(r["api_call_time"] for r in successful_results) / len(successful_results)
        avg_total_time = sum(r["total_time"] for r in successful_results) / len(successful_results)
        avg_client_time = sum(r["client_time"] for r in successful_results) / len(successful_results)
    else:
        avg_api_time = avg_total_time = avg_client_time = 0
    
    # Count requests per user
    user_counts = {}
    for r in results:
        user = r["user"]
        user_counts[user] = user_counts.get(user, 0) + 1
    
    # Count repeated questions
    question_counts = {}
    for r in results:
        q = r["question"]
        question_counts[q] = question_counts.get(q, 0) + 1
    
    # Print statistics
    print(f"Total requests: {num_requests}")
    print(f"Successful requests: {total_success}/{num_requests} ({total_success/num_requests*100:.1f}%)")
    print(f"Cache hits: {cache_hits}/{total_success} ({cache_hits/total_success*100:.1f}% of successful requests)" if total_success else "Cache hits: 0/0 (0.0%)")
    print(f"\nAverage times (successful requests):")
    print(f"  API call time: {avg_api_time:.2f} seconds")
    print(f"  Total time: {avg_total_time:.2f} seconds")
    print(f"  Client time: {avg_client_time:.2f} seconds")
    
    print("\nRequests per user:")
    for user, count in sorted(user_counts.items()):
        print(f"  {user}: {count} requests")
    
    print("\nMost frequent questions:")
    for question, count in sorted(question_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  '{question[:50]}...' - {count} times" if len(question) > 50 else f"  '{question}' - {count} times")
    
    print("\nTest completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test API with random questions across multiple sessions")
    parser.add_argument("--requests", type=int, default=10, help="Number of requests to make")
    parser.add_argument("--delay", type=float, default=1, help="Delay between requests in seconds")
    args = parser.parse_args()
    
    test_api_with_random_questions(
        num_requests=args.requests,
        delay_between_requests=args.delay
    )
