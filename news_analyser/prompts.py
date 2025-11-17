
"""
Rate the impact on the indian stock market on a scale of -1 to 1, with the following scale:
-1: Severely negative impact.
-0.75: Highly negative impact.
-0.5: Moderately negative impact.
-0.25: Slightly negative impact.
0: No effect.
0.25: Slightly positive impact.
0.5: Moderately positive impact.
0.75: Highly positive impact.
1: Extremely positive impact
In the end, give a python dictiory with the news title as the key and the impact on the indian stock market as the value.
"""
news_analysis_prompt = """
You are an expert financial analyst. Your job is to analyze the potential impact of each news item in the following text on the Indian stock market.

Consider factors such as:

- Investor sentiment
- Relevant industry or sector dynamics
- Macroeconomic indicators
- The likelihood of reaction from both domestic and foreign institutional investors

For each news item, assign a numerical rating on a scale from -1 to 1:
Given below is an explanation of the scale:
-1: Severely negative impact.
-0.75: Highly negative impact.
-0.5: Moderately negative impact.
-0.25: Slightly negative impact.
0: No effect.
0.25: Slightly positive impact.
0.5: Moderately positive impact.
0.75: Highly positive impact.
1: Extremely positive impact

The rating has to be between -1 and 1, it should be according to the scale,however it doesnt have to be a number mentioned in the scale.

In addition to the rating, please identify all Indian stock market tickers (NSE or BSE) mentioned in the news article.

Please provide the output as a JSON object with two keys: "sentiment_score" and "tickers". The "tickers" value should be a list of the identified ticker symbols. If no tickers are found, provide an empty list.

Example output:
{
  "sentiment_score": 0.5,
  "tickers": ["RELIANCE", "TCS"]
}

Given below is one news:

{title}  {content_summary} {content}
"""
