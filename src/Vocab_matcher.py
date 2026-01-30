import os
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

class VocabMatcher:
    def __init__(self, csv_path, text_path, output_path):
        self.csv_path = csv_path
        self.text_path = text_path
        self.output_path = output_path
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
            
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=self.api_key,
            temperature=0
        )

    def get_target_word(self):
        """Gets the first word from the CSV file."""
        df = pd.read_csv(self.csv_path)
        # Assuming the first column matches the 'Word' header seen in `head` command
        first_word = df.iloc[0]['Word'] 
        return first_word.strip()

    def get_paragraph(self):
        """Reads the paragraph from the text file."""
        with open(self.text_path, 'r') as f:
            return f.read()

    def find_match_and_rewrite(self, target_word, paragraph):
        """
        Uses LangChain to find the synonym for 'target_word' in 'paragraph'
        and rewrites the paragraph.
        """
        
        # 1. Identify the matching word in the text
        identify_prompt = ChatPromptTemplate.from_template(
            """
            You are a vocabulary expert.
            Target Word: "{target_word}"
            
            Text:
            "{paragraph}"
            
            Task:
            Identify the single word in the text above that is most synonymous with "{target_word}".
            Return ONLY the word from the text, nothing else.
            """
        )
        
        identify_chain = identify_prompt | self.llm | StrOutputParser()
        
        print(f"Analyzing text for synonym of: '{target_word}'...")
        matched_word = identify_chain.invoke({"target_word": target_word, "paragraph": paragraph})
        matched_word = matched_word.strip()
        print(f"Identified synonym in text: '{matched_word}'")
        
        # Add delay to avoid rate limiting
        import time
        time.sleep(2)
        
        # 2. Rewrite the paragraph
        rewrite_prompt = ChatPromptTemplate.from_template(
            """
            You are a skilled editor.
            
            Original Text:
            "{paragraph}"
            
            Task:
            Rewrite the text above by replacing the word "{matched_word}" with the word "{target_word}".
            Ensure the context and grammar remain correct and the meaning is preserved. 
            Do not change any other parts of the text unnecessarily.
            
            Return only the rewritten text.
            """
        )
        
        rewrite_chain = rewrite_prompt | self.llm | StrOutputParser()
        
        print(f"Rewriting text to replace '{matched_word}' with '{target_word}'...")
        rewritten_text = rewrite_chain.invoke({
            "paragraph": paragraph,
            "matched_word": matched_word,
            "target_word": target_word
        })
        
        return rewritten_text

    def run(self):
        try:
            target_word = self.get_target_word()
            print(f"Target Vocab Word from CSV: '{target_word}'")
            
            paragraph = self.get_paragraph()
            
            rewritten_text = self.find_match_and_rewrite(target_word, paragraph)
            
            print("\n--- Original Paragraph ---")
            print(paragraph)
            print("\n--- Rewritten Paragraph ---")
            print(rewritten_text)
            
            # Save to file
            with open(self.output_path, 'w') as f:
                f.write(rewritten_text)
            print(f"\nSuccessfully saved rewritten text to: {self.output_path}")
            
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Define paths relative to the project root (assuming script runs from project root)
    # Adjust paths if running from 'src' directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_file = os.path.join(base_dir, "GRE Master Wordlist 5349.csv")
    text_file = os.path.join(base_dir, "paragraph.txt")
    output_file = os.path.join(base_dir, "paragraph_rewritten.txt")
    
    matcher = VocabMatcher(csv_file, text_file, output_file)
    matcher.run()
