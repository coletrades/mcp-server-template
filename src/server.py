import httpx
import os
import asyncio
import threading
from fastmcp import FastMCP

mcp = FastMCP(
    name="discord-mcp",
    instructions="Use this integration to read messages, list channels, and send messages in Discord."
)

DISCORD_API = "https://discord.com/api/v10"
TOKEN = os.environ.get("DISCORDBOTTOKEN", "")
POKE_API_KEY = os.environ.get("POKEAPIKEY", "")
DISCORD_BOT_ID = None

async def discord_fetch(path: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{DISCORD_API}{path}",
            headers={"Authorization": f"Bot {TOKEN}"}
        )
        res.raise_for_status()
        return res.json()

async def send_to_poke(message: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://poke.com/api/v1/inbound-sms/webhook",
            headers={"Authorization": f"Bearer {POKE_API_KEY}", "Content-Type": "application/json"},
            json={"message": message}
        )

async def poll_mentions():
    global DISCORD_BOT_ID
    # Get bot user ID
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{DISCORD_API}/@me",
            headers={"Authorization": f"Bot {TOKEN}"}
        )
        bot = res.json()
        DISCORD_BOT_ID = bot["id"]

    seen_ids = set()
    print(f"Polling for mentions of bot {DISCORD_BOT_ID}...")

    while True:
        try:
            async with httpx.AsyncClient() as client:
                # Get all guilds
                res = await client.get(
                    f"{DISCORD_API}/users/@me/guilds",
                    headers={"Authorization": f"Bot {TOKEN}"}
                )
                guilds = res.json()

            for guild in guilds:
                # Get channels
                channels = await discord_fetch(f"/guilds/{guild['id']}/channels")
                text_channels = [c for c in channels if c["type"] == 0]

                for channel in text_channels:
                    try:
                        async with httpx.AsyncClient() as client:
                            res = await client.get(
                                f"{DISCORD_API}/channels/{channel['id']}/messages?limit=5",
                                headers={"Authorization": f"Bot {TOKEN}"}
                            )
                            messages = res.json()

                        for msg in messages:
                            if msg["id"] in seen_ids:
                                continue
                            seen_ids.add(msg["id"])
                            # Check if bot is mentioned
                            mentions = [m["id"] for m in msg.get("mentions", [])]
                            if DISCORD_BOT_ID in mentions:
                                text = f"Someone mentioned you in #{channel['name']}: {msg['author']['username']} said: {msg['content']} (channel_id: {channel['id']})"
                                print(f"Mention found: {text}")
                                await send_to_poke(text)
                    except:
                        pass

        except Exception as e:
            print(f"Polling error: {e}")

        await asyncio.sleep(15)

def start_polling():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(poll_mentions())

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
    # Start polling in background thread
    t = threading.Thread(target=start_polling, daemon=True)
    t.start()
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
