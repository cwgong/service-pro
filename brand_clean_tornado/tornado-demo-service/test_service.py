# -*- coding: utf-8 -*-

import io
import os
import requests
import json
import random
from functools import wraps
import time


def timefn(fn):
    """计算函数耗时的修饰器"""
    @wraps(fn)
    def measure_time(*args, **kwargs):
        t1 = time.time()
        result = fn(*args, **kwargs)
        t2 = time.time()
        print("@timefn: " + fn.__name__ + " took: " + str(t2 - t1) + " seconds")
        return result
    return measure_time


@timefn
def server_test(url, post_data):

    url += '/analysis'
    response = requests.post(url, data=json.dumps(post_data))
    print('status: ', response)
    response = response.json()
    print('response: ', response)


if __name__ == '__main__':

    url = 'http://localhost:31001'

    title = '《this is title》'
    content = 'this is content'

    post_data = {'title': title,
                 'content': content}

    server_test(url, post_data)




