import json
from textblob import TextBlob
from mcp.server.fastmcp import FastMCP

# from pydantic import Field
mcp = FastMCP("sentiment-analysis")


@mcp.tool(
    name="sentiment_analysis",
    description="Perform sentiment analysis on the input text.",
)
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


# Start the server
if __name__ == "__main__":
    mcp.run(transport="stdio")
