#!/usr/bin/env python3
"""
Simple Web Search Module
Uses OpenAI o4-mini with web_search tool to find vendors
"""

import os
from openai import OpenAI

def run_web_search(query: str) -> str:
    """Run web search using the exact code pattern provided."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not set")
            return ""

        client = OpenAI(api_key=api_key)

        resp = client.responses.create(
            model="o4-mini",                     # reasoning-capable model
            reasoning={"effort": "medium"},      # low | medium | high
            input=query,
            tools=[{"type": "web_search"}],      # minimal tool declaration
            tool_choice="auto"
        )

        return resp.output_text or ""
    except Exception as e:
        print(f"❌ Web search error: {e}")
        return ""
        