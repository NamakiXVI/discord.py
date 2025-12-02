import asyncio
from putergenai import PuterClient

import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import datetime

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
if not token:
    print("ERROR: No token found in environment variables!")
    exit(1)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

def log_message(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if message.guild:
        server_name = message.guild.name
        server_id = message.guild.id
        channel_name = message.channel.name
        channel_id = message.channel.id
        location_info = f"[Server: {server_name} ({server_id}) | Channel: #{channel_name} ({channel_id})]"
    else:  
        server_name = "DM"
        server_id = "N/A"
        channel_name = "Direct Message"
        channel_id = message.channel.id
        location_info = f"[DM with {message.author} | Channel ID: {channel_id}]"
    
    log_entry = f'[{timestamp}] {location_info} {message.author} ({message.author.id}): "{message.content}"\n'

    with open('messages.log', 'a', encoding='utf-8') as f:
        f.write(log_entry)

bot = commands.Bot(command_prefix='§', intents=intents)

@bot.event
async def on_ready():
    print('Logged on as', bot.user.name)
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        
@bot.event
async def on_message(message):
    log_message(message)

    if message.author.bot:
        await bot.process_commands(message)
        return

    if message.guild is None and message.author != bot.user:
        try:
            if message.content.startswith(bot.command_prefix):
                await bot.process_commands(message)
                return
            
            if not message.content.strip():
                response = "Hello! You sent an empty message."
            else:
                response = await deepseek(message.content, "deepseek-chat")
                print(len(response))
                if len(response) > 2000:
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"response_{timestamp}.txt"

                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(response)
                    
                    await message.channel.send("Response too long for a message. Here's the response as a file:", file=discord.File(filename))
                    
                    os.remove(filename)
                else:
                    await message.channel.send(response)

            
            # Log the bot's response
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f'[{timestamp}] [DM Response to {message.author} ({message.author.id})]: "{response}"\n'
            
            with open('messages.log', 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except discord.Forbidden:
            # User has DMs closed or blocked the bot
            print(f"Cannot send DM to {message.author}")
        except Exception as e:
            print(f"Error responding to DM from {message.author}: {e}")
    
    # Process commands for both DMs and server messages
    await bot.process_commands(message)


@bot.hybrid_command(
    name="ask",
    description="Ask the AI to generate text or create an image"
)
@app_commands.choices(model=[
    app_commands.Choice(name="▬▬DeepSeek▬▬", value=""),
    app_commands.Choice(name="DeepSeek Chat", value="deepseek-chat"),
    app_commands.Choice(name="DeepSeek DeepThink", value="deepseek-reasoner"),

    app_commands.Choice(name="▬▬ChatGPT▬▬", value=""),
    app_commands.Choice(name="GPT-5", value="gpt-5.1"),
    app_commands.Choice(name="GPT-4", value="gpt-4o"),

    app_commands.Choice(name="▬▬Claude▬▬", value=""),
    app_commands.Choice(name="Claude Opus", value="claude-opus-4-5-latest"),
    app_commands.Choice(name="Claude Haiku", value="claude-haiku-4.5"),
    app_commands.Choice(name="Claude Sonnet", value="claude-sonnet-4.5"),
    app_commands.Choice(name="Claude Sonnet", value="claude-sonnet-4.5"),

    app_commands.Choice(name="▬▬Grok▬▬", value=""),
    app_commands.Choice(name="Grok 3", value="grok-3"),
    app_commands.Choice(name="Grok Fast", value="grok-3-fast"),
    app_commands.Choice(name="Grok Mini", value="grok-3-mini"),
    app_commands.Choice(name="Grok Mini Fast", value="grok-3-mini-fast"),

    app_commands.Choice(name="▬▬Gemini▬▬", value=""),
    app_commands.Choice(name="Gemini Flash", value="gemini-2.5-flash"),
    app_commands.Choice(name="Gemini Flash Lite", value="gemini-2.5-flash-lite"),
    app_commands.Choice(name="Gemini Pro", value="gemini-2.5-pro"),

    app_commands.Choice(name="▬▬Qwen▬▬", value=""),
    app_commands.Choice(name="Qwen thinking", value="openrouter:qwen/qwen3-vl-8b-thinking"),
    app_commands.Choice(name="Qwen instruct", value="openrouter:qwen/qwen3-vl-8b-instruct"),
])
async def ask(ctx, user_prompt: str, model: app_commands.Choice[str] = None):
    # Get the model value if a choice was provided
    model_value = model.value if model else None
    # Call the prompt function with the correct arguments
    await ask_prompt(ctx, prompt=user_prompt, model=model_value)

# Renamed from 'prompt' to 'ask_prompt' to avoid conflict
async def ask_prompt(ctx, *, prompt: str, model: str = None):
    if ctx.interaction: 
        log_content = f"/ask {prompt}"
    else:
        log_content = f":ask {prompt}"
    
    if ctx.interaction:
        await ctx.defer()
    
    # Log the message properly
    if ctx.interaction:
        # For slash commands, create a fake message for logging
        class FakeMessage:
            def __init__(self, content, author, guild, channel):
                self.content = content
                self.author = author
                self.guild = guild
                self.channel = channel
        
        fake_msg = FakeMessage(
            content=log_content,
            author=ctx.author,
            guild=ctx.guild,
            channel=ctx.channel
        )
        log_message(fake_msg)
    else:
        # For text commands, use the actual message
        log_message(ctx.message)
    
    # Call deepseek with the prompt and model
    response = await deepseek(prompt, model)
    
    if len(response) > 2000:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"response_{timestamp}.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response)
        
        await ctx.send("Response too long for a message. Here's the response as a file:", file=discord.File(filename))
        
        os.remove(filename)
    else:
        embed = discord.Embed(title="AI Response", description=response)
        if model:
            embed.set_footer(text=f"Model: {model}")
        poll_message = await ctx.send(embed=embed)
        await poll_message.add_reaction("👍")
        await poll_message.add_reaction("👎🏿")

@bot.hybrid_command(
    name="senddm",
    description="Send a direct message to a user"
)
@app_commands.describe(
    user="The user to DM (can be ID, mention, or username#discriminator)",
    message="The message to send"
)
async def send_dm(ctx, user: str, *, message: str):
    """Send a direct message to a user using various identifier methods"""
    
    if ctx.interaction:
        await ctx.defer(ephemeral=True)
    
    # Log the command
    if ctx.interaction:
        log_content = f"/senddm user:{user} message:{message}"
        class FakeMessage:
            def __init__(self, content, author, guild, channel):
                self.content = content
                self.author = author
                self.guild = guild
                self.channel = channel
        
        fake_msg = FakeMessage(
            content=log_content,
            author=ctx.author,
            guild=ctx.guild,
            channel=ctx.channel
        )
        log_message(fake_msg)
    else:
        log_message(ctx.message)
    
    # Permission check (optional - customize as needed)
    if not ctx.author.guild_permissions.administrator and ctx.author.id != ctx.bot.owner_id:
        await ctx.send("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    target_user = None
    
    try:
        # Method 1: Check if it's a mention
        if user.startswith('<@') and user.endswith('>'):
            user_id = user.strip('<@!>')
            target_user = await bot.fetch_user(int(user_id))
        
        # Method 2: Check if it's a user ID
        elif user.isdigit():
            target_user = bot.get_user(int(user))
            if not target_user:
                target_user = await bot.fetch_user(int(user))
        
        # Method 3: Try to parse as username#discriminator
        elif '#' in user:
            username, discriminator = user.split('#', 1)
            # Search in all guilds the bot is in
            for guild in bot.guilds:
                member = discord.utils.get(guild.members, name=username, discriminator=discriminator)
                if member:
                    target_user = member
                    break
            
            # If not found in guilds, we can't fetch by username#discriminator via API
            if not target_user:
                await ctx.send("❌ User not found in any shared servers. Try using their user ID instead.", ephemeral=True)
                return
        
        # Method 4: Try to get by username only (less reliable)
        else:
            # Search in current guild first
            if ctx.guild:
                member = discord.utils.get(ctx.guild.members, name=user)
                if member:
                    target_user = member
            
            # If not found, search all guilds
            if not target_user:
                for guild in bot.guilds:
                    member = discord.utils.get(guild.members, name=user)
                    if member:
                        target_user = member
                        break
            
            if not target_user:
                await ctx.send("❌ User not found. Try using their full username#discriminator or user ID.", ephemeral=True)
                return
        
        # Send the DM
        try:
            embed = discord.Embed(
                title=f"Message from {ctx.author.display_name}",
                description=message,
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            if ctx.guild:
                embed.set_footer(text=f"Server: {ctx.guild.name}")
            
            await target_user.send(embed=embed)
            
            # Success response
            success_embed = discord.Embed(
                title="✅ DM Sent Successfully",
                description=f"**To:** {target_user.mention}\n**Message sent!**",
                color=discord.Color.green()
            )
            success_embed.add_field(name="User ID", value=f"`{target_user.id}`", inline=False)
            
            await ctx.send(embed=success_embed, ephemeral=True)
            
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot send DM to {target_user.mention}. They might have DMs disabled.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", ephemeral=True)
            
    except ValueError:
        await ctx.send("❌ Invalid user format. Use: ID, @mention, or username#discriminator", ephemeral=True)
    except discord.NotFound:
        await ctx.send("❌ User not found. Make sure the ID or username is correct.", ephemeral=True)
    except Exception as e:
        await ctx.send(f"❌ Unexpected error: {str(e)}", ephemeral=True)

@bot.command()
async def reply(ctx, *, msg):
    log_message(ctx.message)
    response = await deepseek(msg, model=None)  # Fixed: pass 'msg' not 'prompt'
    await ctx.reply(response)

async def deepseek(set_prompt, set_model):
    async with PuterClient() as client:
        # Login to Puter.com
        await client.login("verplanter", "Ichbinder1.")

        # AI Chat with GPT-4o
        result = await client.ai_chat(
            prompt=set_prompt,
            options={"model": set_model if set_model else "gpt-4o", "stream": False}
        )

        print(result["response"]["result"]["message"]["content"])
        return result["response"]["result"]["message"]["content"]

bot.run(token, log_handler=handler, log_level=logging.DEBUG)