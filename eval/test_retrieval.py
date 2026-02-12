"""
Retrieval Precision Evaluation

WHAT THIS DOES:
Tests if Pinecone's semantic search returns the RIGHT articles when given a question.

HOW IT WORKS:
1. We have 10 test questions with "ground truth" (which article SHOULD match)
2. We send each question to Pinecone
3. Pinecone returns the top 3 most similar articles (based on embeddings)
4. We check: Are the expected articles in those top 3?
5. Calculate Precision@3 = (# of relevant articles in top 3) / 3

EXAMPLE:
Query: "How should I handle a lazy cofounder?"
Expected: "help-my-cofounder-is-lazy" article
Retrieved top 3: ["help-my-cofounder-is-lazy", "other-article-1", "other-article-2"]
Precision@3: 1/3 = 33% (1 relevant article out of 3 results)

PERFECT SCORE: 100% means every query returned the right article in top 3

Usage:
    cd cherrytree-chat-agent
    source venv/bin/activate
    python eval/test_retrieval.py
"""

import os
from dotenv import load_dotenv
from pinecone import Pinecone

# Load environment variables (API keys)
load_dotenv()

# Connect to Pinecone vector database
# This is where our 21 Cherrytree articles are stored as embeddings
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("cherrytree-knowledge")


# ============================================================================
# TEST CASES - "Ground Truth"
# ============================================================================
# Each test case has:
# - query: The question we're asking
# - relevant_ids: Which article(s) SHOULD be retrieved (manually verified)
# - category: What type of question this is
#
# We manually decided these IDs are "correct" answers based on article content
# ============================================================================
TEST_CASES = [
    {
        "query": "How should I handle a lazy cofounder?",
        "relevant_ids": ["help-my-cofounder-is-lazy"],  # This article ID should match
        "category": "cofounder_traits"
    },
    {
        "query": "My cofounder is a narcissist, what should I do?",
        "relevant_ids": ["help-my-cofounder-is-a-narcissist"],
        "category": "cofounder_traits"
    },
    {
        "query": "Should I choose someone with credentials or chemistry?",
        "relevant_ids": ["credentials-or-chemistry"],
        "category": "cofounder_selection"
    },
    {
        "query": "How do I find a technical cofounder?",
        "relevant_ids": ["why-you-cant-find-a-technical-cofounder"],
        "category": "cofounder_selection"
    },
    {
        "query": "What are the rules for cofounders?",
        "relevant_ids": ["15-rules-for-cofounders"],
        "category": "best_practices"
    },
    {
        "query": "How can I destroy my cofoundership?",
        "relevant_ids": ["how-to-destroy-your-cofoundership-b4e0"],
        "category": "conflict_resolution"
    },
    {
        "query": "My cofounder is paranoid about everything",
        "relevant_ids": ["help-my-cofounder-is-paranoid"],
        "category": "cofounder_traits"
    },
    {
        "query": "What makes someone cofounder material?",
        "relevant_ids": ["what-makes-someone-cofounder-material"],
        "category": "cofounder_selection"
    },
    {
        "query": "How to build a great cofounder relationship?",
        "relevant_ids": ["great-companies-result-from-great-company", "what-bread-has-to-do-with-your-cofoundership"],
        "category": "relationship_dynamics"
    },
    {
        "query": "We're avoiding tough conversations",
        "relevant_ids": ["avoiding-tough-conversations-3b29"],
        "category": "communication"
    },
]


def search_pinecone(query: str, top_k: int = 3):
    """
    Send a question to Pinecone and get back the most similar articles.

    HOW IT WORKS:
    1. Pinecone automatically converts the query text into an embedding (vector)
    2. Compares that vector to all 21 article vectors in the database
    3. Returns the K most similar articles (highest cosine similarity scores)

    Args:
        query: The question text (e.g., "How do I handle a lazy cofounder?")
        top_k: How many results to return (default: 3)

    Returns:
        List of matching articles with their scores and metadata
    """
    # Call Pinecone's search API
    # namespace="cherrytree" is where our articles are stored
    # query={"inputs": {"text": query}} tells Pinecone to embed this text
    # fields=["title", "content", "topic"] tells Pinecone to return these metadata fields
    results = index.search(
        namespace="cherrytree",
        query={"top_k": top_k, "inputs": {"text": query}},
        fields=["title", "content", "topic"]
    )

    # Extract the actual hits from the nested response structure
    hits = results.get("result", {}).get("hits", [])
    return hits


def calculate_success_at_k(retrieved_ids: list, relevant_ids: list, k: int = 3):
    """
    Calculate Success@K metric (also called Hit Rate@K).

    FORMULA: Success@K = Did we find at least 1 relevant doc in top K?
    - If YES → 1.0 (100%)
    - If NO  → 0.0 (0%)

    EXAMPLE 1 (Success):
    Retrieved IDs: ["article-a", "article-b", "article-c"]
    Relevant IDs: ["article-a", "article-d"]

    Is "article-a" in top 3? YES → Success@3 = 1.0 (100%)

    EXAMPLE 2 (Failure):
    Retrieved IDs: ["article-x", "article-y", "article-z"]
    Relevant IDs: ["article-a", "article-d"]

    Is either "article-a" or "article-d" in top 3? NO → Success@3 = 0.0 (0%)

    Args:
        retrieved_ids: List of IDs that Pinecone returned
        relevant_ids: List of IDs we expect (ground truth)
        k: How many results to consider (default: 3)

    Returns:
        1.0 if at least one relevant doc found in top K, else 0.0
    """
    # Get only the top K results
    top_k_ids = retrieved_ids[:k]

    # Check if ANY of the relevant IDs are in the top K
    # Returns True if we find at least one match
    found = any(id in relevant_ids for id in top_k_ids)

    # Return 1.0 for success, 0.0 for failure
    return 1.0 if found else 0.0


def run_evaluation():
    """
    Main evaluation function - runs all test cases and calculates metrics.

    FLOW:
    1. Loop through each test question
    2. Send question to Pinecone
    3. Get back top 3 most similar articles
    4. Check if expected articles are in those top 3
    5. Calculate precision score
    6. Show summary statistics across all questions

    Returns:
        (results, avg_precision) tuple
    """
    print("=" * 80)
    print("RETRIEVAL PRECISION EVALUATION")
    print("=" * 80)
    print(f"\nTesting {len(TEST_CASES)} queries...\n")

    # Store results for each test case
    results = []
    # Track total success rate to calculate average later
    total_success = 0

    # ========================================================================
    # STEP 1: Loop through each test case
    # ========================================================================
    for i, test_case in enumerate(TEST_CASES, 1):
        # Extract the question, expected article IDs, and category
        query = test_case["query"]
        relevant_ids = test_case["relevant_ids"]  # Ground truth
        category = test_case["category"]

        print(f"\n[{i}/{len(TEST_CASES)}] Query: \"{query}\"")
        print(f"Category: {category}")
        print(f"Expected: {relevant_ids}")

        # ====================================================================
        # STEP 2: Search Pinecone with this query
        # ====================================================================
        hits = search_pinecone(query, top_k=3)

        # If Pinecone returned nothing, mark as failed
        if not hits:
            print("❌ No results returned")
            results.append({
                "query": query,
                "success": 0.0,
                "retrieved": [],
                "expected": relevant_ids
            })
            continue

        # ====================================================================
        # STEP 3: Extract the IDs from Pinecone's response
        # ====================================================================
        # Each hit looks like: {"_id": "article-id", "fields": {...}, "_score": 0.85}
        # We want just the IDs to compare against our expected IDs
        retrieved_ids = [hit.get("_id", "") for hit in hits]

        # ====================================================================
        # STEP 4: Calculate Success@3 for this query
        # ====================================================================
        # This checks: did we find at least 1 expected article in top 3?
        success = calculate_success_at_k(retrieved_ids, relevant_ids, k=3)
        total_success += success  # Add to running total

        # ====================================================================
        # STEP 5: Display results for this query
        # ====================================================================
        print(f"Retrieved (top 3):")
        for j, hit in enumerate(hits[:3], 1):
            # Extract ID, score, and metadata from each hit
            doc_id = hit.get("_id", "unknown")  # If ID missing, show "unknown"
            score = hit.get("_score", 0)  # Similarity score (0-1, higher = more similar)
            fields = hit.get("fields", {})
            title = fields.get("title", "Untitled")

            # Check if this ID is in our expected list
            is_relevant = "✓" if doc_id in relevant_ids else "✗"
            print(f"  {j}. [{is_relevant}] {title}")
            print(f"     ID: {doc_id} | Score: {score:.3f}")

        # Show success or failure for this query
        success_status = "✓ Success" if success == 1.0 else "✗ Failed"
        print(f"Success@3: {success_status}")

        # Save this query's results
        results.append({
            "query": query,
            "success": success,
            "retrieved": retrieved_ids[:3],
            "expected": relevant_ids,
            "category": category
        })

    # ========================================================================
    # STEP 6: Calculate summary statistics across ALL test cases
    # ========================================================================
    # Success rate = total successes / number of queries
    # This is the main metric: "What % of queries found at least 1 relevant article?"
    success_rate = total_success / len(TEST_CASES)

    # How many queries succeeded (found at least 1 relevant article)?
    successful_queries = sum(1 for r in results if r["success"] == 1.0)

    # How many queries failed (found NO relevant articles)?
    failed_queries = sum(1 for r in results if r["success"] == 0.0)

    # ========================================================================
    # STEP 7: Display summary report
    # ========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal queries tested: {len(TEST_CASES)}")
    print(f"Success@3: {success_rate:.1%}")  # THE KEY METRIC
    print(f"Successful queries: {successful_queries}/{len(TEST_CASES)}")
    print(f"Failed queries: {failed_queries}/{len(TEST_CASES)}")

    # WHAT THESE NUMBERS MEAN:
    # - 90%+ success rate = EXCELLENT (Pinecone consistently finds right articles)
    # - 75-90% = GOOD
    # - Below 75% = NEEDS IMPROVEMENT (knowledge base may have gaps)

    # Category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r["success"])

    print(f"\nSuccess rate by category:")
    for cat, successes in categories.items():
        rate = sum(successes) / len(successes)
        print(f"  {cat}: {rate:.1%} ({len(successes)} queries)")

    print("\n" + "=" * 80)

    return results, success_rate


if __name__ == "__main__":
    run_evaluation()
