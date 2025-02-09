import os
import asyncio
import json
from pydantic import BaseModel, Field
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import re
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def url_extraction(website):
    crawler_cfg = CrawlerRunConfig(
        exclude_external_links=True,
        exclude_social_media_links=True
    )

    async with AsyncWebCrawler(site=website) as crawler:
        # print(site)
        result = await crawler.arun(
            # "https://www.cnn.com/business",
            #"https://www.bbc.com/business",
            #"{site}",
            website,
            config=crawler_cfg
        )
        if result.success:
            internal_links = result.links.get("internal", [])
            external_links = result.links.get("external", [])

            # Return the links from the coroutine
            return internal_links, external_links
        else:
            print("[ERROR]", result.error_message)
            return [], []  # Return empty lists if failed

class Product(BaseModel):
    name: str
    price: str

async def main(url_list,newspaper):
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        provider="openai/gpt-4o-mini",            # e.g. "ollama/llama2"
        api_token=os.getenv('OPENAI_API_KEY'),
        schema=Product.schema_json(),            # Or use model_json_schema()
        extraction_type="schema",
        instruction="Extract only title and text from article. Disrecard all other content.",
        chunk_token_threshold=250,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="markdown",   # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 800}
    )
    


    prune_filter = PruningContentFilter(
        # Lower → more content retained, higher → more content pruned
        threshold=0.45,           
        # "fixed" or "dynamic"
        threshold_type="dynamic",  
        # Ignore nodes with <5 words
        min_word_threshold=5      
    )

    # Step 2: Insert it into a Markdown Generator
    md_generator = DefaultMarkdownGenerator(content_filter=prune_filter,    options={
            "ignore_links": True,
            "escape_html": False,
            "body_width": 80
        })

    # 2. Build the crawler config
    crawl_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS,
        markdown_generator=md_generator
        #content_filter=filter
    )

    # 3. Create a browser config if needed
    browser_cfg = BrowserConfig(headless=True)

    # The file where we'll store results
    filename = f"{newspaper}_results.md"

    async with AsyncWebCrawler(urls=url_list,config=browser_cfg) as crawler:
        with open(filename, "w", encoding="utf-8") as f:
        # Optionally, write a top-level heading:
            f.write("# Crawl Results\n\n")
            urls=url_list
            for url in urls:
                print('URL', url)
                result = await crawler.arun(
                    #url="https://www.cnn.com/2025/02/03/business/tariffs-gas-prices/index.html",
                    url=url,
                    config=crawl_config
                )
                if result.success:
                    # 5. The extracted content is presumably JSON
                    data = json.loads(result.extracted_content)
                    #print("Extracted items:", data)
                    # Extract text tags
                    print('URL is:',result.url)
                    name_tags = [item['name'] for item in data if 'name' in item]
                    print('Name of the article is: ', name_tags)
                    text_tags = [item['text'] for item in data if 'text' in item]
                    print('Text in the article is: ', text_tags)
                  # Write a sub-heading for each article
                    f.write(f"## Article from: {url}\n\n")
                    f.write(f"## name: {name_tags}\n\n")
                    f.write(f"## text: {text_tags}\n\n")

                    f.write("\n---\n\n")  # A separator between articles
                    llm_strategy.show_usage()  # prints token usage
                else:
                    print("Error:", result.error_message)

if __name__ == '__main__':
    # # Run the async function and capture the returned values
    newspaper='bbc'
    
    if newspaper=='cnn':
          website="https://www.cnn.com/business"
        pattern=re.compile(r'\.com/\d{4}/\d{2}/\d{2}/business')
    elif newspaper=='bbc':
        website="https://www.bbc.com/business"
        pattern=re.compile(r'\.com/news/articles')

    
    internal_links, external_links = asyncio.run(url_extraction(website))
    filtered_data = [entry for entry in internal_links if pattern.search(entry['href'])]
    # Extracting only the 'href' values into a list
    url_list = [entry['href'] for entry in filtered_data if 'href' in entry]
    if url_list:
        print('url list is not emtpy')
        asyncio.run(main(url_list,newspaper))



