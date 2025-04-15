
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
Only provide a single numerical rating for the given news as the final answer without any additional commentary.

Given below is one news:

{title}  {content_summary} {content}
"""
