from fsrs import Scheduler, Card, Rating, State
import sqlite3
import datetime
import os
from dateutil import parser

DB_PATH = 'vocabook.db'

class FSRSManager:
    def __init__(self, db_path=None):
        self.db_path = db_path if db_path else DB_PATH
        self.scheduler = Scheduler()

    def _ensure_utc(self, dt_val):
        """
        Helper to robustly convert string/float/int/datetime to UTC datetime.
        """
        if dt_val is None:
            return None
            
        dt = None
        if isinstance(dt_val, str):
            try:
                dt = parser.parse(dt_val)
            except:
                return None
        elif isinstance(dt_val, (int, float)):
            dt = datetime.datetime.fromtimestamp(dt_val, tz=datetime.timezone.utc)
        elif isinstance(dt_val, datetime.datetime):
            dt = dt_val
        else:
            return None
            

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:

            dt = dt.astimezone(datetime.timezone.utc)
            
        return dt

    def get_word_state(self, word):
        """
        Fetch current FSRS state for a word from DB.
        Returns (word_id, full_state_dict) or (None, None).
        full_state_dict includes 'card' (FSRS Card), 'reps', 'lapses', etc.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, due, stability, difficulty, elapsed_days, scheduled_days, reps, lapses, state, last_review 
            FROM words WHERE word = ?
        """, (word.lower(),))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None, None
            
        wid, due, stab, diff, elp, sch, reps, laps, state_val, last_rev = row
        
        card = Card()

        if stab is not None:
            card.stability = stab
            card.difficulty = diff
            card.state = State(state_val)
            

            card.due = self._ensure_utc(due)
            card.last_review = self._ensure_utc(last_rev)
            

        state_data = {
            'card': card,
            'reps': reps if reps else 0,
            'lapses': laps if laps else 0,
            'elapsed_days': elp if elp else 0,
            'scheduled_days': sch if sch else 0
        }
                    
        return wid, state_data

    def process_review(self, word, rating_val, review_time=None):
        """
        word: string
        rating_val: 1 (Again), 2 (Hard), 3 (Good), 4 (Easy)
        review_time: datetime (UTC)
        """
        if not review_time:
            review_time = datetime.datetime.now(datetime.timezone.utc)
        else:
            review_time = self._ensure_utc(review_time)
            if not review_time:
                 review_time = datetime.datetime.now(datetime.timezone.utc)
            
        wid, state_data = self.get_word_state(word)
        if not wid:
            return

        old_card = state_data['card']
        old_reps = state_data['reps']
        old_lapses = state_data['lapses']
        

        if old_card.last_review and review_time <= old_card.last_review:
            return

        try:
            rating = Rating(rating_val)
        except ValueError:
            print(f"Invalid rating {rating_val} for word '{word}'")
            return


        elapsed_days = 0
        if old_card.last_review:
            elapsed_days = (review_time - old_card.last_review).days
        
        try:
            updated_card, review_log = self.scheduler.review_card(old_card, rating, review_time)
            

            new_reps = old_reps + 1
            new_lapses = old_lapses
            if rating == Rating.Again:
                new_lapses += 1
                

            scheduled_days = 0
            if updated_card.due:
                scheduled_days = (updated_card.due - review_time).days
            
            self._update_db(wid, updated_card, new_reps, new_lapses, elapsed_days, scheduled_days, review_time, rating_val, old_card.state)
            print(f"FSRS Updated '{word}': Reps {new_reps}, State {updated_card.state}, Due {updated_card.due}")
            
        except Exception as e:
             print(f"Error calling scheduler.review_card: {e}")
             return

    def _update_db(self, wid, card, reps, lapses, elapsed_days, scheduled_days, review_time, rating, old_state_val):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        

        cursor.execute("""
            UPDATE words SET
                due = ?,
                stability = ?,
                difficulty = ?,
                elapsed_days = ?,
                scheduled_days = ?,
                reps = ?,
                lapses = ?,
                state = ?,
                last_review = ?
            WHERE id = ?
        """, (
            card.due.isoformat() if card.due else None,
            card.stability,
            card.difficulty,
            elapsed_days,
            scheduled_days,
            reps,
            lapses,
            int(card.state),
            card.last_review.isoformat() if card.last_review else None,
            wid
        ))
        

        cursor.execute("""
            INSERT INTO review_logs 
            (word_id, rating, scheduled_days, elapsed_days, review_date, state)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            wid,
            rating,
            scheduled_days,
            elapsed_days,
            review_time.isoformat(),
            int(old_state_val)
        ))
        
        conn.commit()
        conn.close()

    def reset_all_progress(self):
        """
        Resets all FSRS progress in the database.
        - Deletes all review_logs.
        - Resets words table columns to default/initial state.
        """
        print("Resetting all FSRS progress...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:

            cursor.execute("DELETE FROM review_logs")
            print("Deleted all review logs.")
            

            cursor.execute("""
                UPDATE words SET
                    due = NULL,
                    stability = NULL,
                    difficulty = NULL,
                    elapsed_days = 0,
                    scheduled_days = 0,
                    reps = 0,
                    lapses = 0,
                    state = 0,
                    last_review = NULL
            """)
            print("Reset all words to initial state.")
            
            conn.commit()
        except Exception as e:
            print(f"Error resetting progress: {e}")
            conn.rollback()
        finally:
            conn.close()
