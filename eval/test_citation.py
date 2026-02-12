"""
Citation Grounding Analysis

Checks if agent responses actually reference content from retrieved articles.
Calculates citation rate - % of key concepts from source that appear in response.

Usage:
    cd cherrytree-chat-agent
    source venv/bin/activate
    python eval/test_citation.py
"""

import os
import re
import json
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

# Connect to Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("cherrytree-knowledge")


def extract_key_phrases(text: str, min_length: int = 10) -> list:
    """
    Extract key phrases from source text.
    These are phrases that should appear in a grounded response.
    """
    # Simple approach: extract phrases between punctuation
    # More sophisticated: use NLP to extract key concepts

    # Remove common filler words and split into sentences
    sentences = re.split(r'[.!?]+', text)

    key_phrases = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) >= min_length:
            # Extract distinct phrases (avoid very common words)
            words = sentence.lower().split()
            if len(words) >= 3:  # At least 3-word phrases
                # Get 3-word sliding windows
                for i in range(len(words) - 2):
                    phrase = ' '.join(words[i:i+3])
                    # Filter out very common phrases
                    if not any(filler in phrase for filler in ['the ', 'and ', 'that ', 'this ', 'with ', 'from ']):
                        key_phrases.append(phrase)

    # Return unique phrases
    return list(set(key_phrases[:20]))  # Limit to 20 key phrases


def check_grounding(response: str, source_content: str) -> dict:
    """
    Check if response is grounded in source content.
    Returns citation score and details.
    """
    key_phrases = extract_key_phrases(source_content)

    if not key_phrases:
        return {
            "citation_score": 0,
            "matched_phrases": [],
            "total_key_phrases": 0
        }

    response_lower = response.lower()
    matched_phrases = []

    for phrase in key_phrases:
        if phrase in response_lower:
            matched_phrases.append(phrase)

    citation_score = len(matched_phrases) / len(key_phrases) if key_phrases else 0

    return {
        "citation_score": citation_score,
        "matched_phrases": matched_phrases,
        "total_key_phrases": len(key_phrases),
        "matched_count": len(matched_phrases)
    }


def analyze_response_grounding(query: str, response: str, expected_article_ids: list):
    """
    Analyze if a response is grounded in the expected articles.
    """
    print(f"\nQuery: \"{query}\"")
    print(f"Expected articles: {expected_article_ids}")

    # Retrieve the expected articles from Pinecone
    all_scores = []
    all_matched = []

    for article_id in expected_article_ids:
        # Search for this specific article
        results = index.search(
            namespace="cherrytree",
            query={"top_k": 5, "inputs": {"text": query}},
            fields=["title", "content"]
        )

        hits = results.get("result", {}).get("hits", [])

        # Find the article in results
        article = None
        for hit in hits:
            if hit.get("id") == article_id:
                article = hit
                break

        if article:
            fields = article.get("fields", {})
            content = fields.get("content", "")
            title = fields.get("title", "Untitled")

            grounding = check_grounding(response, content)
            all_scores.append(grounding["citation_score"])
            all_matched.extend(grounding["matched_phrases"])

            print(f"\n  Article: {title}")
            print(f"  Citation score: {grounding['citation_score']:.2%}")
            print(f"  Matched: {grounding['matched_count']}/{grounding['total_key_phrases']} key phrases")
        else:
            print(f"\n  ❌ Article {article_id} not found in retrieval results")

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    print(f"\nOverall citation score: {avg_score:.2%}")
    print(f"Response length: {len(response)} characters")

    # Check if response has disclaimer
    has_disclaimer = any(phrase in response.lower() for phrase in [
        "not legal advice",
        "educational guidance",
        "consult an attorney"
    ])

    print(f"Has legal disclaimer: {'✓' if has_disclaimer else '✗'}")

    return {
        "citation_score": avg_score,
        "has_disclaimer": has_disclaimer,
        "matched_phrases": all_matched,
        "response_length": len(response)
    }


# Example test cases with sample responses
# In production, these would be real chatbot responses
CITATION_TEST_CASES = [
    {
        "query": "How should I handle a lazy cofounder?",
        "expected_articles": ["help-my-cofounder-is-lazy"],
        "sample_response": """
A cofounder appearing unmotivated might signal underlying issues rather than simple laziness.
Before dismissing them, consider what could be driving their disengagement.

Some common causes include lack of intrinsic motivation, cognitive dissonance about their
performance, avoidance of growth due to fear, burnout, or imposter syndrome. Rather than
demanding more effort, try reconnecting them with the original mission.

Ask compassionately: "I've noticed [specific behavior]. I want to understand what's making
this difficult." This removes shame and redirects conversation toward solutions.

If it's actually laziness after addressing underlying causes, the critical question is:
do they genuinely want to build this with you? If not, you need to move forward.

This is educational guidance, not legal advice. For specific contract or legal issues,
consult an attorney.
        """.strip()
    },
    {
        "query": "Should I prioritize chemistry or credentials?",
        "expected_articles": ["credentials-or-chemistry"],
        "sample_response": """
Chemistry should take priority over credentials when choosing a cofounder.

Research shows that while prioritizing credentials gets higher investor ratings, prioritizing
chemistry leads to lower rates of early-stage dissolution. You'll spend more time with your
cofounder than anyone else in your career, so compatibility matters more than resume.

Skills can be developed over time, but interpersonal dynamics are foundational. If you both
lack credentials, find a trustworthy advisor. Build the relationship before building the business.

This is educational guidance, not legal advice.
        """.strip()
    }
]


def run_citation_evaluation():
    """Run citation grounding evaluation on sample responses."""
    print("=" * 80)
    print("CITATION GROUNDING EVALUATION")
    print("=" * 80)
    print(f"\nTesting {len(CITATION_TEST_CASES)} sample responses...\n")

    results = []

    for i, test_case in enumerate(CITATION_TEST_CASES, 1):
        print(f"\n[{i}/{len(CITATION_TEST_CASES)}]")
        print("=" * 80)

        result = analyze_response_grounding(
            test_case["query"],
            test_case["sample_response"],
            test_case["expected_articles"]
        )

        results.append({
            "query": test_case["query"],
            **result
        })

    # Summary
    avg_citation_score = sum(r["citation_score"] for r in results) / len(results)
    disclaimer_rate = sum(1 for r in results if r["has_disclaimer"]) / len(results)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal responses tested: {len(results)}")
    print(f"Average citation score: {avg_citation_score:.2%}")
    print(f"Disclaimer rate: {disclaimer_rate:.2%}")
    print("\nNote: To test with real chatbot responses, integrate with /chat endpoint")
    print("\n")

    return results


if __name__ == "__main__":
    run_citation_evaluation()
