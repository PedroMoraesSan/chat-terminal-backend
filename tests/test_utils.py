import re

from pyback.domain.utils import generate_random_chat_name


def test_generate_random_chat_name_format():
    name = generate_random_chat_name()
    assert re.match(r"^[A-Z]{3}-\d{3}$", name)
