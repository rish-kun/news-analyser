import json
from dotenv import load_dotenv
from typing import List
import asyncio
from browser_use import Agent, Controller, Browser, BrowserConfig
from pydantic import SecretStr, BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
import os
load_dotenv()


task = """
    Find the 1 most recent news articles on tariff war between US and China on google news. For each article:
    1. Visit the news page to extract the full content of the news

    IMPORTANT: Avoid websites which require a subscription or have captchas. If you run into such websites, then go back and find another news source.
"""


async def get_news(link):
    task = " grab the main content of the open tab."
    initial_actions = [
        {"open_tab": {"url": link}}
    ]

    class News(BaseModel):
        content: str
        keywords: List[str]

    config = BrowserConfig(
        headless=True,
    )

    browser = Browser(config=config)

    controller = Controller(output_model=News)
    agent = Agent(
        task=task,
        initial_actions=initial_actions,
        llm=ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite", api_key=SecretStr(os.getenv('GEMINI_API_KEY_3') or os.getenv('GEMINI_API_KEY')), controller=controller),
        browser=browser,
        controller=controller
    )
    try:
        history = await agent.run(max_steps=20)
        if history.extracted_content:
            content = history.final_result()
            content_dict = json.loads(content)
            print(type(content_dict))
            print(content_dict['content'])
            return content_dict
            # Try to parse the result as JSON first
            # try:
            #     # Clean the result string if it contains markdown code blocks
            #         "```json", "").replace("```", "").strip()
            #     json_result = json.loads(cleaned_result)
            #     parsed: NewsList = NewsList.model_validate(json_result)
            #     for news in parsed.news:
            #         print(f"Title: {news.news_title}")
            #         print(f"Content: {news.news_content}")
            #         print(f"URL: {news.news_url}")
            #         print(f"Date Posted: {news.date_posted}")
            #         print("\n")
            # except json.JSONDecodeError as e:
            #     print(f"Error parsing JSON: {e}")
            #     print("Cleaned result:", cleaned_result)
            # except Exception as e:
            #     print(f"Error processing result: {e}")
    except Exception as e:
        print(f"Error running agent: {e}")
