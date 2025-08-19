#!/usr/bin/env python3
"""
This module contains a Cache class for basic operations with Redis.
It demonstrates storing and retrieving strings, incrementing values,
storing lists, and retrieving lists.
"""

import redis
import uuid
from typing import Union, Callable
from functools import wraps


def count_calls(method: Callable) -> Callable:
    """
    Decorator that counts the number of times a method is called.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        self._redis.incr(method.__qualname__)
        return method(self, *args, **kwargs)
    return wrapper


def call_history(method: Callable) -> Callable:
    """
    Decorator that stores the history of inputs and outputs of the method.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        input_key = f"{method.__qualname__}:inputs"
        output_key = f"{method.__qualname__}:outputs"
        self._redis.rpush(input_key, str(args))
        result = method(self, *args, **kwargs)
        self._redis.rpush(output_key, str(result))
        return result
    return wrapper


def replay(method: Callable):
    """
    Function that displays the history of calls of a particular function.
    """
    cache = Cache()
    method_name = method.__qualname__
    inputs = cache._redis.lrange(f"{method_name}:inputs", 0, -1)
    outputs = cache._redis.lrange(f"{method_name}:outputs", 0, -1)
    print(f"{method_name} was called {len(inputs)} times:")
    for inp, out in zip(inputs, outputs):
        # Convert input from string representation of tuple back to actual
        # tuple
        inp_tuple = eval(inp.decode('utf-8'))
        # Ensure that output is a string representation of UUID
        out_str = out.decode('utf-8')
        print(f"{method_name}(*{inp_tuple}) -> {out_str}")


class Cache:
    """
    Cache class for storing data in Redis.
    """
    def __init__(self):
        """
        Initialize the Redis client and flush the database.
        """
        self._redis = redis.Redis()
        self._redis.flushdb()

    @call_history
    @count_calls
    def store(self, data: Union[str, bytes, int, float]) -> str:
        """
        Store the input data in Redis using a random key.
        """
        key = str(uuid.uuid4())
        self._redis.set(key, data)
        return key

    def get(self, key: str, fn: Callable = None) -> Union[str, bytes, int,
                                                          float]:
        """
        Get the value from Redis by key and convert it using the provided
        function if not None.
        """
        value = self._redis.get(key)
        if fn:
            return fn(value)
        return value

    def get_str(self, key: str) -> str:
        """
        Get the value from Redis by key and convert it to a str.
        """
        value = self.get(key)
        return value.decode("utf-8") if value else value

    def get_int(self, key: str) -> int:
        """
        Get the value from Redis by key and convert it to an int.
        """
        value = self.get(key)
        return int(value) if value else value


if __name__ == "__main__":
    """
    MAIN
    """
    cache = Cache()

    # Test the store method
    data = "I'm a string!"
    key = cache.store(data)
    print(f"String stored with key: {key}")

    # Test the get_str method
    retrieved_str = cache.get_str(key)
    print(f"Retrieved string: {retrieved_str}")

    # Test the increment
    cache.store("Another string")
    cache.store("Yet another string")
    print(f"store method was called: {cache.get_int('Cache.store')} times")

    # Test the replay
    replay(cache.store)
