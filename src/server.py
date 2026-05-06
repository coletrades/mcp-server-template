import httpx
import os
from fastmcp import FastMCP

mcp = FastMCP(
    name="discord-mcp",
    instructions="Use this integration to read messages, list channels, and send messages in Discord."
)

DISCORD_API = "https://discord.com/api/v10"
TOKEN = os.environ.get("DISCORDBOTTOKEN", "")

async def discord_fetch(path: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{DISCORD_API}{path}",
            headers={"Authorization": f"Bot {TOKEN}"}
        )
        res.raise_for_status()
        return res.json()

@mcp.tool
async def list_channels(guild_id: str) -> str:
    """List all text channels in a Discord server by guild ID."""
    channels = await discord_fetch(f"/guilds/{guild_id}/channels")
    text_channels = [{"id": c["id"], "name": c["name"]} for c in channels if c["type"] == 0]
    return str(text_channels)

@mcp.tool
async def get_messages(channel_id: str, limit: int = 10) -> str:
    """Fetch recent messages from a Discord channel by channel ID."""
    messages = await discord_fetch(f"/channels/{channel_id}/messages?limit={limit}")
    simplified = [{"author": m["author"]["username"], "content": m["content"]} for m in messages]
    return str(simplified)

@mcp.tool
async def send_message(channel_id: str, message: str) -> str:
    """Send a message to a Discord channel by channel ID."""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"},
            json={"content": message}
        )
        res.raise_for_status()
        return "Message sent successfully!"

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
