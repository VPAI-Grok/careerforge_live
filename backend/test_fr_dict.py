from google.genai import types

r = types.FunctionResponse(id='abc', name='test', response={'foo':'bar'})

def convert_fr(fr):
    fr_dict = {}
    if getattr(fr, 'id', None) is not None:
         fr_dict['id'] = fr.id
    if getattr(fr, 'name', None) is not None:
         fr_dict['name'] = fr.name
    if getattr(fr, 'response', None) is not None:
         fr_dict['response'] = fr.response
         
    if not fr_dict and isinstance(fr, dict):
         fr_dict = fr
    elif not fr_dict:
         fr_dict = {'name': getattr(fr, 'name', ''), 'response': getattr(fr, 'response', {})}
         if getattr(fr, 'id', None) is not None:
             fr_dict['id'] = fr.id
             
    return fr_dict

converted = convert_fr(r)
import json
print("Converted keys:", converted.keys())
print("JSON representation:", json.dumps(converted))
