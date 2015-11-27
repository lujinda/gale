#!/usr/bin/env python
#coding:utf-8
# Author        : tuxpy
# Email         : q8886888@qq.com.com
# Last modified : 2015-11-27 10:27:59
# Filename      : strategy.py
# Description   : from __future__ import print_function, unicode_literals
from __future__ import print_function, unicode_literals
import random


def _rand_upstream_by_weight(weight_data):
    if not weight_data:
        return None

    weight_items = weight_data.items()
    weight_items.sort(key = lambda item: item[1])
    freq_queue = [0]

    for value, freq in weight_items:
        freq = freq_queue[-1] + freq
        freq_queue.append(freq)

    max_freq = max(freq_queue)
    if max_freq == 0:
        return None

    freq_pos = random.randint(0, max_freq)

    for index, freq in enumerate(freq_queue):
        if freq > freq_pos:
            return weight_items[index - 1][0]

    return weight_items[-1][0]

class _IStrategyManager(object):
    invalid_upstreams = {}
    def __init__(self, upstream_settings):
        self.upstream_settings = upstream_settings
        self.upstreams_weight = upstream_settings.get('weight', {})

    def add_invalid_upstream(self, upstream):
        weight = self.upstreams_weight.pop(upstream)
        self.invalid_upstreams[upstream] = weight

    def remove_invalid_upstream(self, upstream):
        self.upstreams_weight[upstream] = self.invalid_upstreams.pop(upstream)

    def get_best_upstream(self):
        raise NotImplementedError


class AutoStrategyManager(_IStrategyManager):
    pass

class IpStrategyManager(_IStrategyManager):
    pass

class RoundStrategyManager(_IStrategyManager):
    pass

class WeightStrategyManager(_IStrategyManager):
    def get_best_upstream(self):
        return _rand_upstream_by_weight(self.upstreams_weight)

