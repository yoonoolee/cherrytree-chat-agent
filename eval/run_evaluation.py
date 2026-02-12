"""
Master Evaluation Runner

Runs all evaluation metrics and generates a comprehensive report.

Usage:
    cd cherrytree-chat-agent
    source venv/bin/activate
    python eval/run_evaluation.py
"""

import sys
from datetime import datetime

# Import evaluation modules
from test_retrieval import run_evaluation as run_retrieval_eval
from test_citation import run_citation_evaluation


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")


def run_full_evaluation():
    """Run all evaluation tests and generate final report."""

    print_header("CHERRYTREE CHATBOT EVALUATION SUITE")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. Retrieval Precision Test
    print_header("TEST 1: RETRIEVAL PRECISION@3")
    print("Measuring: Does Pinecone return the right articles for test queries?\n")

    try:
        retrieval_results, avg_precision = run_retrieval_eval()
        retrieval_success = True
    except Exception as e:
        print(f"❌ Retrieval evaluation failed: {e}")
        retrieval_success = False
        avg_precision = 0

    # 2. Citation Grounding Test
    print_header("TEST 2: CITATION GROUNDING")
    print("Measuring: Do responses reference source material?\n")

    try:
        citation_results = run_citation_evaluation()
        avg_citation = sum(r["citation_score"] for r in citation_results) / len(citation_results)
        disclaimer_rate = sum(1 for r in citation_results if r["has_disclaimer"]) / len(citation_results)
        citation_success = True
    except Exception as e:
        print(f"❌ Citation evaluation failed: {e}")
        citation_success = False
        avg_citation = 0
        disclaimer_rate = 0

    # Final Report
    print_header("FINAL EVALUATION REPORT")

    print("METRICS SUMMARY:")
    print("-" * 80)
    print(f"  Retrieval Precision@3:  {avg_precision:.1%}")
    print(f"  Citation Grounding:     {avg_citation:.1%}")
    print(f"  Legal Disclaimer Rate:  {disclaimer_rate:.1%}")
    print("-" * 80)

    # Overall grade
    overall_score = (avg_precision + avg_citation) / 2
    if overall_score >= 0.85:
        grade = "🟢 EXCELLENT"
    elif overall_score >= 0.70:
        grade = "🟡 GOOD"
    elif overall_score >= 0.50:
        grade = "🟠 FAIR"
    else:
        grade = "🔴 NEEDS IMPROVEMENT"

    print(f"\nOverall Performance: {grade} ({overall_score:.1%})")

    # Recommendations
    print("\nRECOMMENDATIONS:")
    print("-" * 80)

    if avg_precision < 0.85:
        print("  ⚠️  Retrieval precision below target (85%)")
        print("      → Review test cases and knowledge base coverage")
        print("      → Consider adding more articles or improving embeddings")

    if avg_citation < 0.90:
        print("  ⚠️  Citation rate below target (90%)")
        print("      → Agent may not be using retrieved content effectively")
        print("      → Update prompt to encourage grounding in source material")

    if disclaimer_rate < 1.0:
        print("  ⚠️  Some responses missing legal disclaimer")
        print("      → Update prompt to ensure disclaimer in every response")

    if not retrieval_success or not citation_success:
        print("  ❌ Some tests failed to run")
        print("      → Check error messages above")

    print("\n" + "=" * 80)
    print("\nEvaluation complete!\n")

    return {
        "retrieval_precision": avg_precision,
        "citation_score": avg_citation,
        "disclaimer_rate": disclaimer_rate,
        "overall_score": overall_score
    }


if __name__ == "__main__":
    try:
        results = run_full_evaluation()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Evaluation failed: {e}")
        sys.exit(1)
