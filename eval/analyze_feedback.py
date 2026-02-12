"""
User Feedback Analysis

Analyzes thumbs up/down feedback from production to measure user satisfaction.
Pulls data from LangSmith and calculates approval rates by day, topic, and other dimensions.

Usage:
    cd cherrytree-chat-agent
    source venv/bin/activate
    python eval/analyze_feedback.py
"""

import os
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from langsmith import Client

load_dotenv()

# Connect to LangSmith
client = Client()


def classify_topic(query: str) -> str:
    """
    Classify a user query into a topic category.

    Simple keyword-based classification. Could be improved with
    embeddings or LLM classification later.
    """
    query_lower = query.lower()

    # Topic keywords
    if any(word in query_lower for word in ['lazy', 'unmotivated', 'not working', 'slacking']):
        return 'cofounder_traits'
    elif any(word in query_lower for word in ['narcissist', 'ego', 'credit', 'selfish']):
        return 'cofounder_traits'
    elif any(word in query_lower for word in ['paranoid', 'trust', 'suspicious']):
        return 'cofounder_traits'
    elif any(word in query_lower for word in ['chemistry', 'credentials', 'choose', 'find', 'select']):
        return 'cofounder_selection'
    elif any(word in query_lower for word in ['equity', 'split', 'ownership', 'shares']):
        return 'equity'
    elif any(word in query_lower for word in ['vesting', 'cliff', 'acceleration']):
        return 'vesting'
    elif any(word in query_lower for word in ['conflict', 'fight', 'disagree', 'argument']):
        return 'conflict_resolution'
    elif any(word in query_lower for word in ['communicate', 'conversation', 'talk', 'discuss']):
        return 'communication'
    elif any(word in query_lower for word in ['relationship', 'partnership', 'dynamic']):
        return 'relationship_dynamics'
    else:
        return 'other'


def get_feedback_data(days_back: int = 30):
    """
    Fetch feedback data from LangSmith for the last N days.

    Returns list of feedback records with metadata.
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    print(f"Fetching feedback from {start_date.date()} to {end_date.date()}...")

    try:
        # Get all feedback for the project
        # LangSmith API: client.list_feedback()
        feedback_list = client.list_feedback(
            project_name="cherrytree-chat-agent",
            # Could add filters here if needed
        )

        feedback_data = []
        for feedback in feedback_list:
            # Get the associated run to extract query and metadata
            try:
                run = client.read_run(feedback.run_id)

                # Extract data
                record = {
                    'run_id': feedback.run_id,
                    'score': feedback.score,  # 1 = thumbs up, 0 = thumbs down
                    'timestamp': feedback.created_at,
                    'query': run.inputs.get('messages', [{}])[-1].get('content', '') if run.inputs else '',
                    'response': run.outputs.get('response', '') if run.outputs else '',
                    'latency': (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else None,
                    'total_tokens': run.total_tokens if hasattr(run, 'total_tokens') else None,
                }

                # Classify topic from query
                record['topic'] = classify_topic(record['query'])

                # Extract date
                record['date'] = feedback.created_at.date()

                feedback_data.append(record)

            except Exception as e:
                print(f"Warning: Could not fetch run {feedback.run_id}: {e}")
                continue

        return feedback_data

    except Exception as e:
        print(f"Error fetching feedback: {e}")
        return []


def calculate_approval_by_day(feedback_data):
    """Calculate approval rate for each day."""
    daily_stats = defaultdict(lambda: {'thumbs_up': 0, 'thumbs_down': 0, 'total': 0})

    for record in feedback_data:
        date = record['date']
        daily_stats[date]['total'] += 1

        if record['score'] == 1:
            daily_stats[date]['thumbs_up'] += 1
        else:
            daily_stats[date]['thumbs_down'] += 1

    # Calculate approval rates
    results = []
    for date, stats in sorted(daily_stats.items()):
        approval_rate = stats['thumbs_up'] / stats['total'] if stats['total'] > 0 else 0
        results.append({
            'date': date,
            'approval_rate': approval_rate,
            'thumbs_up': stats['thumbs_up'],
            'thumbs_down': stats['thumbs_down'],
            'total': stats['total']
        })

    return results


def calculate_approval_by_topic(feedback_data):
    """Calculate approval rate for each topic."""
    topic_stats = defaultdict(lambda: {'thumbs_up': 0, 'thumbs_down': 0, 'total': 0})

    for record in feedback_data:
        topic = record['topic']
        topic_stats[topic]['total'] += 1

        if record['score'] == 1:
            topic_stats[topic]['thumbs_up'] += 1
        else:
            topic_stats[topic]['thumbs_down'] += 1

    # Calculate approval rates
    results = []
    for topic, stats in sorted(topic_stats.items(), key=lambda x: x[1]['total'], reverse=True):
        approval_rate = stats['thumbs_up'] / stats['total'] if stats['total'] > 0 else 0
        results.append({
            'topic': topic,
            'approval_rate': approval_rate,
            'thumbs_up': stats['thumbs_up'],
            'thumbs_down': stats['thumbs_down'],
            'total': stats['total']
        })

    return results


def run_analysis(days_back=30):
    """Run the full feedback analysis."""
    print("=" * 80)
    print("USER FEEDBACK ANALYSIS")
    print("=" * 80)

    # Fetch data
    feedback_data = get_feedback_data(days_back)

    if not feedback_data:
        print("\nNo feedback data found.")
        print("\nThis is expected if:")
        print("  - App is not in production yet")
        print("  - No users have submitted feedback")
        print("  - LangSmith project name is incorrect")
        print("\nOnce you have production data, this script will show:")
        print("  - Approval rate by day")
        print("  - Approval rate by topic")
        print("  - Overall statistics")
        return

    print(f"\nFound {len(feedback_data)} feedback records\n")

    # Overall stats
    total_feedback = len(feedback_data)
    thumbs_up = sum(1 for r in feedback_data if r['score'] == 1)
    thumbs_down = sum(1 for r in feedback_data if r['score'] == 0)
    overall_approval = thumbs_up / total_feedback if total_feedback > 0 else 0

    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    print(f"Total feedback: {total_feedback}")
    print(f"Thumbs up: {thumbs_up}")
    print(f"Thumbs down: {thumbs_down}")
    print(f"Overall approval rate: {overall_approval:.1%}")

    # Approval by day
    print("\n" + "=" * 80)
    print("APPROVAL RATE BY DAY")
    print("=" * 80)
    print(f"{'Date':<12} {'Approval':<10} {'Up':<6} {'Down':<6} {'Total':<6}")
    print("-" * 80)

    daily_results = calculate_approval_by_day(feedback_data)
    for day in daily_results:
        print(f"{day['date']!s:<12} {day['approval_rate']:>8.1%} "
              f"{day['thumbs_up']:>6} {day['thumbs_down']:>6} {day['total']:>6}")

    # Approval by topic
    print("\n" + "=" * 80)
    print("APPROVAL RATE BY TOPIC")
    print("=" * 80)
    print(f"{'Topic':<25} {'Approval':<10} {'Up':<6} {'Down':<6} {'Total':<6}")
    print("-" * 80)

    topic_results = calculate_approval_by_topic(feedback_data)
    for topic in topic_results:
        print(f"{topic['topic']:<25} {topic['approval_rate']:>8.1%} "
              f"{topic['thumbs_up']:>6} {topic['thumbs_down']:>6} {topic['total']:>6}")

    # Target assessment
    print("\n" + "=" * 80)
    print("ASSESSMENT")
    print("=" * 80)

    if overall_approval >= 0.85:
        grade = "EXCELLENT"
    elif overall_approval >= 0.75:
        grade = "GOOD"
    elif overall_approval >= 0.60:
        grade = "FAIR"
    else:
        grade = "NEEDS IMPROVEMENT"

    print(f"Overall performance: {grade} ({overall_approval:.1%})")
    print(f"\nTarget: 80%+ approval rate")

    if overall_approval < 0.80:
        print("\nRecommendations:")
        print("  - Review thumbs down responses to identify issues")
        print("  - Check if agent is using RAG search appropriately")
        print("  - Analyze low-performing topics for knowledge gaps")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        run_analysis(days_back=30)
    except Exception as e:
        print(f"\nAnalysis failed: {e}")
        print("\nNote: This script requires production data from LangSmith.")
        print("It will work once users start submitting feedback in production.")
