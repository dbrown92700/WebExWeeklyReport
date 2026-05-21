from webexpythonsdk import WebexAPI
from anthropic import Anthropic
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
import pickle
import re
import sys

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.root.addHandler(console)

def generate_briefing(system_prompt: str, user_prompt: str):
    """Call the Claude API with web search and return the HTML briefing."""

    token = os.getenv("ANTHROPIC_API_KEY")
    MODEL = os.getenv("ANTHROPIC_MODEL")
    MAX_TOKENS = int(os.getenv("ANTHROPIC_TOKEN_LIMIT"))

    client = Anthropic(api_key=token)  # Reads ANTHROPIC_API_KEY from environment

    logger.info(f"[hd_briefing] Calling Claude {MODEL} with web search...")

    events = []

    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        # tools=[
        #     {
        #         "type": "web_search_20250305",
        #         "name": "web_search",
        #     }
        # ],
        messages=[
            {"role": "user", "content": user_prompt}
        ],
    ) as stream:
        print('Entering the neverending loop...', flush=True)
        for event in stream:
            events.append(event)
            logger.info(event)
            # print(event, file=sys.stderr, flush=True)

    # final = stream.get_final_message()
    # logger.info(f'\n\n\nFinal Message:\n\n\n{final}\n\n\n')

    with open('stream.pickle', 'wb') as handle:
        pickle.dump(events, handle)

    full_response = ''

    # Assemble text response
    for event in events:
        if event.type == 'content_block_delta' and event.delta.type == 'text_delta':
            full_response += event.delta.text

    # Ensure we got HTML back — basic sanity check
    if "<!DOCTYPE html>" not in full_response and "<html" not in full_response:
        raise ValueError(
            "Claude did not return an HTML document. "
            f"Response starts with: {full_response[:200]!r}"
        )

    # Strip any accidental markdown code fences
    full_response = re.sub(r"^```html?\s*", "", full_response, flags=re.IGNORECASE)
    full_response = re.sub(r"\s*```$", "", full_response)

    return full_response

def post_webex_message(token: str, room_id: str, message: str, files=None):

    api = WebexAPI(access_token=token)
    if not files:
        files = None
    api.messages.create(roomId=room_id, markdown=message, files=files)

def get_room_id(token: str, room_title: str):

    api = WebexAPI(access_token=token)
    rooms = api.rooms.list(type='group')
    for room in rooms:
        if room.title == room_title:
            return room.id

    return None

def main():

    load_dotenv()
    webex_key = os.getenv("WEBEX_BOT_TOKEN")
    room_name = os.getenv("ROOM_TITLE")
    post_as_file = os.getenv("POST_AS_FILE")

    room_id = get_room_id(webex_key, room_name)
    if room_id is None:
        logger.info("No room found")
        exit(1)

    ai_prompt = open("test_prompt.txt", "r").read()
    sys_prompt = open("test_system_prompt.txt", "r").read()

    response = generate_briefing(system_prompt=sys_prompt, user_prompt=ai_prompt)

    t = datetime.today()
    if post_as_file:
        post_as_file = f'.{t.year}{t.month}{t.day}.'.join(post_as_file.split('.'))
        with open(post_as_file, "w") as f:
            f.write(response)
        message = f'# THD Weekly Update {t.month}/{t.day}/{t.year}'
    else:
        message = f'# THD Weekly Update {t.month}/{t.day}/{t.year}\n\n{response}'

    post_webex_message(token=webex_key, room_id=room_id, message=message, files=[post_as_file])
    # logger.info(f'{t.month:02}/{t.day:02}-{t.hour:02}:{t.minute:02} '
    #             f'Input Tokens: {response.usage.input_tokens}  Output Tokens: {response.usage.output_tokens}')
    return response

if __name__ == "__main__":
    main()