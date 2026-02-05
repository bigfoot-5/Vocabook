from fsrs import Scheduler, Card, Rating, State
import datetime
from dateutil import parser

def test_fsrs():
    s = Scheduler()
    
    # Case 1: New Card
    c1 = Card()
    now = datetime.datetime.now(datetime.timezone.utc)
    print("Testing New Card review...")
    try:
        s.review_card(c1, now)
        print("New Card Success")
    except Exception as e:
        print(f"New Card Failed: {e}")

    # Case 2: Existing Card (simulating DB load)
    c2 = Card()
    c2.state = State.Review
    c2.stability = 2.0
    c2.difficulty = 5.0
    c2.elapsed_days = 1
    c2.scheduled_days = 1
    c2.reps = 1
    c2.lapses = 0
    
    # Set dates with timezone
    last_review_str = "2025-02-01T12:00:00+00:00"
    due_str = "2025-02-02T12:00:00+00:00"
    
    c2.last_review = parser.parse(last_review_str)
    c2.due = parser.parse(due_str)
    
    review_time = datetime.datetime.now(datetime.timezone.utc)
    
    print("\nTesting Existing Card review (Timezone Aware)...")
    try:
        s.review_card(c2, review_time)
        print("Existing Card Success")
    except Exception as e:
        print(f"Existing Card Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fsrs()
