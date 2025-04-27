"""import modules"""
import discord
import openai
import subprocess
from discord.ext import commands
from dotenv import load_dotenv
import os
import tempfile

"""Load environment variables from .env file"""
load_dotenv()

"""Set up your Discord bot"""
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
"""Set your OpenAI API key and Discord token from environment variables"""
openai.api_key = os.getenv('OPENAI_API_KEY')
discord_token = os.getenv('DISCORD_TOKEN')

"""Function to send large messages in chunks"""
async def send_large_message(channel, message):
    while len(message) > 0:
        await channel.send(message[:2000])
        message = message[2000:]

"""Function to generate UML image using PlantUML"""
def generate_uml_image(uml_text):
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as uml_file:
        uml_file.write(uml_text)
        uml_file_path = uml_file.name

    output_path = uml_file_path + '.png'
    plantuml_jar_path = r"plantuml-1.2025.2.jar"

    try:
        result = subprocess.run(
            ['java', '-jar', plantuml_jar_path, uml_file_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"PlantUML Output:\n{result.stdout.decode()}")
        print(f"PlantUML Error (if any):\n{result.stderr.decode()}")
    except subprocess.CalledProcessError as e:
        print(f"Error while running PlantUML: {e.stderr.decode()}")
        raise e

    return output_path

"""when the bot is ready"""
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

"""bot is mentioned"""
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return 

    if bot.user.mentioned_in(message):
        task = message.content.replace(f'<@{bot.user.id}>', '').strip()

        try:
            prompt = build_prompt(task)

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an assistant helping to automate SDLC tasks."},
                    {"role": "user", "content": prompt}
                ]
            )

            answer = response['choices'][0]['message']['content'].strip()

            if len(answer) > 2000:
                await send_large_message(message.channel, answer)
            else:
                await message.channel.send(answer)

            if "uml" in task.lower() or "diagram" in task.lower():
                clean_uml_text = extract_uml_text(answer)
                uml_image_path = generate_uml_image(clean_uml_text)
                await message.channel.send(file=discord.File(uml_image_path))

        except Exception as e:
            await message.channel.send(f"Sorry, something went wrong: {e}")

    await bot.process_commands(message)

"""build prompt based on task"""
def build_prompt(task):
    if "requirements" in task.lower():
        return f"Generate functional and non-functional requirements for {task}. Include: Requirement Description, Priority, Complexity, Expected Outcomes, and How to implement it."
    elif "design" in task.lower():
        return f"Generate system architecture design for {task}"
    elif "uml" in task.lower() or "diagram" in task.lower():
        return f"Generate a UML diagram for {task} (e.g., class diagram, sequence diagram)"
    elif "test" in task.lower() or "testing" in task.lower():
        return f"Generate test cases and suggest testing strategies for {task}"
    elif "documentation" in task.lower():
        return f"Generate technical documentation, such as a user manual or API documentation, for {task}"
    else:
        return f"Automate the SDLC task: {task}"

"""clean UML text from response"""
def extract_uml_text(answer):
    if '```' in answer:
        content = answer.split('```')[1].strip()
    else:
        content = answer

    if not content.startswith("@startuml"):
        content = f"@startuml\n{content}\n@enduml"
    return content


bot.run(discord_token)
