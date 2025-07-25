import json
import gradio as gr
from textblob import TextBlob


def sentiment_analysis(text: str) -> str:
    """Perform sentiment analysis on the input text.
    Args:
        text (str): The input text to analyze.

    Returns:
        str: A JSON string containing the sentiment polarity, subjectivity and assessment.
    """
    blob = TextBlob(text)
    sentiment = blob.sentiment
    result = {
        "polarity": sentiment.polarity,
        "subjectivity": sentiment.subjectivity,
        "assessment": (
            "Positive"
            if sentiment.polarity > 0
            else "Negative" if sentiment.polarity < 0 else "Neutral"
        ),
    }
    return json.dumps(result)


# Create a Gradio interface for the sentiment analysis function
demo = gr.Interface(
    fn=sentiment_analysis,
    inputs=gr.Textbox(
        label="Input Text", placeholder="Enter text to analyze sentiment..."
    ),
    outputs=gr.Textbox(label="Sentiment Analysis Result"),
    title="Sentiment Analysis",
    description="Analyze the sentiment of the input text using TextBlob.",
)

# Launch the Gradio interface
if __name__ == "__main__":
    demo.launch(mcp_server=True)
