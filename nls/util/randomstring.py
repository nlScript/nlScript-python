import string
import random


class RandomString:
    def __init__(self, length):
        self._length = length

    def nextString(self, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(self._length))