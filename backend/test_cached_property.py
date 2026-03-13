import asyncio
from functools import cached_property

class MyModel:
    @cached_property
    def api_client(self):
        print("Initializing default client")
        return "DEFAULT_CLIENT"

def test():
    model1 = MyModel()
    print("model1 client:", model1.api_client) # Should print Initializing... then DEFAULT_CLIENT
    
    model2 = MyModel()
    model2.api_client = "CUSTOM_CLIENT" # Overwrite the cached property
    print("model2 client:", model2.api_client) # Should NOT print Initializing, just CUSTOM_CLIENT

test()
