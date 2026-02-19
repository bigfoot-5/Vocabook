# Vocabook

**Vocabook** is an advanced vocabulary learning tool designed to integrate seamlessly with your Calibre e-book library. It leverages the power of the **FSRS (Free Spaced Repetition Scheduler)** algorithm to help you master new words efficiently directly within the context of your reading.

## Key Features

- **Seamless Calibre Integration**: Connects directly to your Calibre library (`metadata.db`) to load books and manage annotations without modifying the original files destructively.
- **Intelligent Review Scheduling**: Uses the state-of-the-art **FSRS v4** algorithm to schedule reviews based on your performance, optimizing retention.
- **Dual Workflow System**:
    - **History Mode**: Sync your past reading highlights to update word mastery levels. 
        - **Yellow**: "Again" (Forgot)
        - **Green/Blue/Other**: "Good" (Remembered)
    - **Future Mode**: Prepare upcoming chapters by injecting definitions and context for target words using AI.
- **Smart Highlighting**: Automatically updates word highlights in your EPUBs to reflect their current spaced-repetition state (e.g., Red for learning, Green for mastered).
- **AI-Powered Enrichment**: Uses LLMs to generate definitions, synonyms, and context sentences for target words, injecting them as non-intrusive annotations.
- **Custom Wordlists**: Import your own wordlists (e.g., GRE, TOEFL) to focus your learning.

## Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/yourusername/vocabook.git
    cd vocabook
    ```

2.  **Set Up Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**:
    - Ensure you have a valid `.env` file with necessary API keys (e.g., for AI features).
    - Update `LIBRARY_PATH` in `src/config.py` or `.env` to point to your Calibre library.

## Usage

1.  **Launch the Application**:
    ```bash
    python3 app.py
    ```

2.  **Select a Book**: comprehensive dropdown list of books from your Calibre library.

3.  **Sync Past Reading**:
    - Go to the **"History Bookmarks"** section.
    - Select the range you just read (e.g., "Start of Book" to "Chapter 1").
    - Click **"Sync Reviews"**. The app will analyze your highlights:
        - Words you highlighted in **Yellow** are marked as "Forgot" and scheduled effectively.
        - Other colors count as "Good".

4.  **Prepare Next Reading**:
    - Go to the **"Future Bookmarks"** section.
    - Select the range you plan to read next.
    - Configure AI settings (optional).
    - Click **"Inject (AI)"** to scan the text, identify target words, and inject definitions/highlights.

## Project Structure

- `app.py`: Main PyQt6 application entry point.
- `src/`: Core source code.
    - `calibre_db.py`: Handles interaction with Calibre's SQLite database.
    - `fsrs_manager.py`: Implements the FSRS scheduling logic.
    - `epub_injector.py`: Logic for modifying EPUB content (safe injection).
    - `bulk_highlighter.py`: Applies color-coded highlights based on word states.
    - `review_sync.py`: Syncs user highlights back to the FSRS database.
    - `vocab_matcher.py`: NLP logic for matching words in text.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

[MIT License](LICENSE)
