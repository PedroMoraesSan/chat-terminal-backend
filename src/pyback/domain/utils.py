import random


def generate_random_chat_name() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    numbers = "0123456789"
    name = "".join(random.choice(letters) for _ in range(3))
    name += "-"
    name += "".join(random.choice(numbers) for _ in range(3))
    return name
