"""
Tools for Jarvis (Claude function-calling).
───────────────────────────────────────────
Gives Jarvis live abilities beyond Claude's training data: the current time,
weather, and web search. Claude decides when to call a tool; jarvis runs it and
feeds the result back so Claude can answer with real, current information.

Providers chosen to avoid signup gates:
  • weather    → Open-Meteo (free, no key)
  • web_search → DuckDuckGo (keyless) by default; Tavily if JARVIS_TAVILY_KEY set
  • datetime   → stdlib

All network/optional deps are imported lazily inside the tool functions, so this
module stays import-safe everywhere (tests, --check, CI).

A tool function takes keyword args (matching its input_schema) and returns a
plain string — that string is what Claude sees as the tool result. Tools never
raise; failures return a readable message so Claude can recover gracefully.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from importlib.util import find_spec
from typing import Callable

import config

_HTTP_TIMEOUT = 12


def _get_json(url: str, timeout: int = _HTTP_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─── Tool implementations ─────────────────────────────────────────────────────

def get_current_datetime() -> str:
    """Local date and time."""
    now = datetime.now().astimezone()
    return now.strftime("It is %A, %d %B %Y, %I:%M %p %Z.")


_WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog", 51: "light drizzle", 53: "drizzle",
    55: "dense drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain", 71: "light snow",
    73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers",
    81: "showers", 82: "violent showers", 85: "snow showers",
    86: "heavy snow showers", 95: "thunderstorm", 96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}


def get_weather(location: str) -> str:
    """Current weather for a place name, via Open-Meteo (no API key)."""
    try:
        geo = _get_json(
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urllib.parse.urlencode({"name": location, "count": 1})
        )
        results = geo.get("results") or []
        if not results:
            return f"I couldn't find a place called '{location}'."
        place = results[0]
        lat, lon = place["latitude"], place["longitude"]
        label = ", ".join(
            p for p in (place.get("name"), place.get("country")) if p
        )
        data = _get_json(
            "https://api.open-meteo.com/v1/forecast?"
            + urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                           "weather_code,wind_speed_10m",
                "timezone": "auto",
            })
        )
        cur = data["current"]
        desc = _WMO.get(cur.get("weather_code"), "unknown conditions")
        return (
            f"Weather in {label}: {desc}, {cur['temperature_2m']}°C "
            f"(feels like {cur['apparent_temperature']}°C), "
            f"humidity {cur['relative_humidity_2m']}%, "
            f"wind {cur['wind_speed_10m']} km/h."
        )
    except Exception as e:  # noqa: BLE001 — tools must not raise
        return f"Weather lookup failed: {e}"


def _web_search_tavily(query: str, max_results: int) -> str:
    payload = json.dumps({
        "api_key": config.TAVILY_KEY,
        "query": query,
        "max_results": max_results,
        "include_answer": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    lines = []
    if data.get("answer"):
        lines.append(f"Answer: {data['answer']}")
    for r in data.get("results", [])[:max_results]:
        lines.append(f"- {r.get('title','')}: {r.get('content','')} ({r.get('url','')})")
    return "\n".join(lines) or "No results found."


def _web_search_ddg(query: str, max_results: int) -> str:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS  # older package name
    with DDGS() as ddg:
        results = list(ddg.text(query, max_results=max_results))
    if not results:
        return "No results found."
    return "\n".join(
        f"- {r.get('title','')}: {r.get('body','')} ({r.get('href','')})"
        for r in results
    )


def get_web_search(query: str, max_results: int = 5) -> str:
    """Search the web for current information."""
    max_results = max(1, min(int(max_results or 5), 8))
    try:
        if config.TAVILY_KEY:
            return _web_search_tavily(query, max_results)
        return _web_search_ddg(query, max_results)
    except Exception as e:  # noqa: BLE001
        return f"Web search failed: {e}"


# ─── Registry ─────────────────────────────────────────────────────────────────

@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    func: Callable[..., str]


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools = {t.name: t for t in tools}

    def __bool__(self) -> bool:
        return bool(self._tools)

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def anthropic_schemas(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in self._tools.values()
        ]

    def run(self, name: str, tool_input: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}"
        try:
            return tool.func(**(tool_input or {}))
        except Exception as e:  # noqa: BLE001 — never break the tool loop
            return f"Tool {name} errored: {e}"


_DATETIME_TOOL = Tool(
    name="get_current_datetime",
    description="Get the current local date and time. Use for any 'what time/day is it' question.",
    input_schema={"type": "object", "properties": {}},
    func=get_current_datetime,
)

_WEATHER_TOOL = Tool(
    name="get_weather",
    description="Get the current weather for a place (city/town name).",
    input_schema={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City or place name, e.g. 'Auckland'"}
        },
        "required": ["location"],
    },
    func=get_weather,
)

_WEB_SEARCH_TOOL = Tool(
    name="web_search",
    description="Search the web for current/factual information the model may not "
                "know (news, recent events, live facts). Returns top results.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "How many results (1-8)"},
        },
        "required": ["query"],
    },
    func=get_web_search,
)


def build_registry() -> ToolRegistry:
    """Assemble the tools available in this environment (respects config + deps)."""
    if not config.ENABLE_TOOLS:
        return ToolRegistry([])
    tools = [_DATETIME_TOOL, _WEATHER_TOOL]
    # Only offer web_search if we actually have a working provider.
    has_ddg = find_spec("ddgs") is not None or find_spec("duckduckgo_search") is not None
    if config.TAVILY_KEY or has_ddg:
        tools.append(_WEB_SEARCH_TOOL)
    return ToolRegistry(tools)
