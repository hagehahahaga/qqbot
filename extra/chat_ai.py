from abstract.bases.importer import fractions, threading, openai, requests
from abstract.bases.importer import dispatch, itertools, operator

import abstract.apis.table
from abstract.apis.table import NULL
from config import CONFIG
from abstract.bases.log import LOG
from abstract.session import Session
from abstract.bases.interruptible_tasks.interruptible_request import InterruptibleRequest


class LLM:
    def __init__(
        self,
        client: openai.Client,
        messages_table: abstract.apis.table.Table,
        name: str,
        prompts: list,
        vision=False,
        r18=False
    ):
        def get_part_from_message(message):
            match message[1]:
                case 'image_url':
                    return {'url': message[2]}
                case 'text':
                    return message[2]
                case _:
                    raise ValueError(f'Unknown message type{message[1]}')

        def get_part_from_role_group(role, group):
            match role:
                case 'user':
                    return [
                        {
                            'type': message[1],
                            message[1]: get_part_from_message(message)
                        } for message in group
                    ]
                case _:
                    return ''.join(map(operator.itemgetter(2), group))

        self.lock = threading.Lock()
        self.client = client
        self.messages_table = messages_table
        self.name = name
        self.vision = vision
        self.r18 = r18
        if not self.messages_table.get(f'where target = "{self.name}" and role = "system"'):
            for message in prompts:
                self.messages_table.add(NULL, self.name, message['role'], message['content'])

        self.messages = []
        messages_data = self.messages_table.get_all(
            f'where target = "{self.name}"',
            attr='role, type, text'
        )

        for role, group in itertools.groupby(messages_data, key=operator.itemgetter(0)):
            self.messages.append(
                {
                    'role': role,
                    'content': get_part_from_role_group(role, group)
                }
            )
        self.cost = 0

    @dispatch
    def say(self, text: str, role='user'):
        data = {
            'role': role,
            'content': text
        }
        self.messages_table.add(NULL, self.name, role, text, 'text')
        self.messages.append(
            data
        )

    @dispatch
    def say(self, content: list[dict], role='user'):
        for part in content:
            type = part['type']
            match type:
                case 'image_url':
                    part = part['image_url']['url']
                case 'text':
                    part = part['text']
            self.messages_table.add(NULL, self.name, role, part, type)

        data = {
            'role': role,
            'content': content
        }
        self.messages.append(
            data
        )

    def hear(self, session: Session) -> str:
        while True:
            response = InterruptibleRequest(session).run(
                str(self.client.base_url.join('/v1/tokenizers/estimate-token-count')),
                json={"model": "moonshot-v1-8k-vision-preview", 'messages': self.messages},
                headers={'Authorization': f"Bearer {self.client.api_key}"},
                method='POST'
            )
            try:
                total_tokens = response.json()['data']['total_tokens']
            except requests.exceptions.JSONDecodeError:
                continue
            if total_tokens <= 128 * 1024:
                break
            for a in range(len(self.messages)):
                if self.messages[a]['role'] == 'user':
                    while self.messages[a]['role'] == 'user':
                        del self.messages[a]
                    while self.messages[a]['role'] == 'assistant':
                        del self.messages[a]
                    break
        model = 'moonshot-v1-'
        self.cost = fractions.Fraction(total_tokens) / 10 ** 6
        match total_tokens:
            case x if x <= 8 * 1024:
                model += '8k'
                self.cost *= 12
            case x if x <= 32 * 1024:
                model += '32k'
                self.cost *= 24
            case x if x <= 128 * 1024:
                model += '128k'
                self.cost *= 60

        if self.vision:
            model += '-vision-preview'

        return self.client.chat.completions.create(
            model=model,
            messages=self.messages,
            temperature=0.3
        ).choices[0].message.content

    @dispatch
    def chat(self, session: Session, content: str | list[dict]) -> str:
        with self.lock:
            self.say(content)
            result = self.hear(session)
            assert result, 'LLM returned nothing!'
            self.say(result, 'assistant')
            return result


LOG.INF('Loading LLM modules...')
CHAT_AIs = {
    name: LLM(
        openai.OpenAI(base_url=CONFIG['ai']['base_url'], api_key=CONFIG['ai']['api_key']),
        abstract.apis.table.AI_MESSAGES_TABLE,
        name,
        **CONFIG['ai']['characters'][name]
    ) for name in CONFIG['ai']['characters']
}
LOG.INF(f'Loaded {len(CHAT_AIs)} LLMs: {", ".join(CHAT_AIs.keys())}')
