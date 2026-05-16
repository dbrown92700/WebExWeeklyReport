from webexpythonsdk import WebexAPI
from anthropic import Anthropic
import os
from dotenv import load_dotenv
from datetime import datetime


def get_claude_response(token: str, model: str, prompt: str):
    client = Anthropic(api_key=token)
    client.messages.create()
    message = client.messages.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model
    )
    client.close()

    return message

def post_webex_message(token: str, message: str, files=None):

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

if __name__ == "__main__":

    load_dotenv()
    webex_key = os.getenv("WEBEX_BOT_TOKEN")
    room_name = os.getenv("ROOM_TITLE")
    claude_api = os.getenv("ANTHROPIC_API_KEY")
    ai_model = os.getenv("ANTHROPIC_MODEL")
    post_as_file = os.getenv("POST_AS_FILE")

    room_id = get_room_id(webex_key, room_name)
    if room_id is None:
        print("No room found")
        exit(1)

    ai_prompt = open("prompt.txt", "r").read()
    response = get_claude_response(token=claude_api, model=ai_model, prompt=ai_prompt)

    t = datetime.today()
    if post_as_file:
        post_as_file = f'.{t.year}{t.month}{t.day}.'.join(post_as_file.split('.'))
        with open(post_as_file, "w") as f:
            f.write(response.content[0].text)
        message = f'# THD Weekly Update {t.month}/{t.day}/{t.year}'
    else:
        message = f'# THD Weekly Update {t.month}/{t.day}/{t.year}\n\n{response.content[0].text}'

    post_webex_message(webex_key, message, files=[post_as_file])
    print(f'{t.month:02}/{t.day:02}-{t.hour:02}:{t.minute:02} '
          f'Input Tokens: {response.usage.input_tokens}  Output Tokens: {response.usage.output_tokens}')
