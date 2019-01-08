import pico.client


example = pico.client.load('http://localhost:4242/example')
print(example.hello('You bastard'))
