from dotenv import load_dotenv; load_dotenv()
from elevenlabs import ElevenLabs
import os
client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

for query in ['carol', 'mora']:
    print(f'\n=== Searching: {query} ===')
    resp = client.voices.search(search=query, page_size=5)
    for v in resp.voices:
        labels = v.labels or {}
        age = labels.get('age', '')
        gender = labels.get('gender', '')
        desc = labels.get('description', '')
        accent = labels.get('accent', '')
        print(f'  {v.voice_id}  {v.name}  age={age}  gender={gender}  accent={accent}  desc={desc}')

