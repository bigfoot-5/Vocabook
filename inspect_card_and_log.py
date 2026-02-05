from fsrs import Card, ReviewLog, Scheduler, Rating
from datetime import datetime, timezone

def inspect():
    c = Card()
    print("Card attributes:", dir(c))
    if hasattr(c, '__annotations__'):
        print("Card annotations:", c.__annotations__)
        
    rl = ReviewLog(
        card_id=c.card_id,
        rating=Rating.Good,
        review_datetime=datetime.now(timezone.utc),
        review_duration=100
    )
    print("\nReviewLog attributes:", dir(rl))
    if hasattr(rl, '__annotations__'):
        print("ReviewLog annotations:", rl.__annotations__)

    # Run a review to see the output card
    s = Scheduler()
    updated_card, log = s.review_card(c, Rating.Good, datetime.now(timezone.utc))
    print("\nUpdated Card attributes:", dir(updated_card))
    print("Has elapsed_days?", hasattr(updated_card, 'elapsed_days'))
    print("Log has elapsed_days?", hasattr(log, 'elapsed_days'))

if __name__ == "__main__":
    inspect()
