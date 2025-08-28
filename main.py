import os
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

def fetch_article_text(url):
    """
    Fetches and extracts the main text content from a news article URL.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 

        soup = BeautifulSoup(response.content, 'html.parser')
        
        paragraphs = soup.find_all('p')
        article_text = ' '.join([p.get_text() for p in paragraphs])
        
        if not article_text.strip():
            return None, "Could not extract meaningful article text. The page might be heavily script-based or empty."

        title = soup.find('h1').get_text() if soup.find('h1') else "Untitled Article"
        return article_text, title

    except requests.exceptions.RequestException as e:
        return None, f"Error fetching URL: {e}"

def generate_analysis(article_text, article_title):
    """
    Sends the article text to the AI and returns a validated report.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not found. Please set it in your .env file."

    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    prompt = f"""
    You are a "Digital Skeptic" AI, an expert in media analysis and critical thinking. Your mission is to analyze a news article, not to determine if it is "true" or "false," but to arm the reader with the tools to think critically about it.

    Analyze the following news article text and generate a "Critical Analysis Report" in Markdown format.

    The report MUST contain these five distinct sections, exactly as follows:
    1.  ### Core Claims
    2.  ### Language & Tone Analysis
    3.  ### Potential Red Flags
    4.  ### Verification Questions
    5.  ### Key Entities to Investigate

    Here are the detailed instructions for each section:
    - **Core Claims**: Summarize the 3-5 most significant factual claims the article makes.
    - **Language & Tone Analysis**: Describe the article's language and tone.
    - **Potential Red Flags**: Identify specific signs of potential bias or poor reporting.
    - **Verification Questions**: Create a list of 3-4 specific, insightful questions a reader should ask.
    - **Key Entities to Investigate**: Identify key people, organizations, and locations and suggest an investigation point for each.

    Here is the article text:
    ---
    {article_text}
    ---
    """

    try:
        response = model.generate_content(prompt)
        
        if not response.parts:
            reason = response.prompt_feedback.block_reason if response.prompt_feedback else "Unknown"
            return f"Error: The AI model returned an empty response. This may be due to the article's content triggering a safety filter. Reason: {reason}"

        full_response_text = "".join(part.text for part in response.parts)
        
        if not full_response_text.strip():
            return "Error: The AI model generated a blank response. The content may have been filtered."
        
        report = f"# Critical Analysis Report for: {article_title.strip()}\n\n" + full_response_text
        return report
    except Exception as e:
        return f"An error occurred with the AI model: {e}"

def save_report(report_content, article_title):
    """
    Saves the provided content to a Markdown file.
    """
    try:
        clean_title = article_title.strip()
        # A more robust way to clean filename
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            clean_title = clean_title.replace(char, '')
        
        file_name = clean_title.replace(' ', '_')[:50] + ".md"
        
        with open(file_name, "w", encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\n✅ Report successfully saved as {file_name}")
        # Add a small delay to ensure filesystem has caught up
        time.sleep(0.5)

    except Exception as e:
        print(f"\n❌ Error saving file: {e}")


if __name__ == '__main__':
    article_url = input("Please enter the URL of the news article to analyze: ")

    if not article_url.strip():
        print("No URL provided. Exiting.")
    else:
        print("\nFetching article content...")
        text, title = fetch_article_text(article_url)

        if text:
            print("Analyzing article with AI (this may take a moment)...")
            analysis_report = generate_analysis(text, title)
            
            print("\n--- ANALYSIS REPORT ---")
            print(analysis_report)
            
            # Restructured Logic: Only save if the report is valid.
            if analysis_report and not analysis_report.strip().startswith("Error:"):
                save_report(analysis_report, title)
            else:
                print("\nSkipping file save due to an error or empty report.")
        else:
            print(f"Failed to retrieve article: {title}")
