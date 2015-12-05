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
        self._upstream_reset_counter = 0
        self.upstream_settings = upstream_settings
        self.init()

    def init(self):
        pass

    def add_invalid_upstream(self, upstream):
        weight = self.upstreams_weight.pop(upstream)
        self.invalid_upstreams[upstream] = weight

    def remove_invalid_upstream(self, upstream):
        self.upstreams_weight[upstream] = self.invalid_upstreams.pop(upstream)

    def reset_upstreams_weight(self):
        if self._upstream_reset_counter >= 1:
            return
        self.flush_invalid_upstream()
        self._upstream_reset_counter += 1

    def flush_invalid_upstream(self):
        self.upstreams_weight.update(self.invalid_upstreams)
        self.invalid_upstreams.clear()


    def get_best_upstream(self):
        raise NotImplementedError

    def flush(self):
        """each request has been processed after the call"""
        self._upstream_reset_counter = 0

    def sort_upstreams_weight(self):
        """according to the conditions to decide whether you want to reset upstreams weight"""
        valid_upstreams_total = len(self.invalid_upstreams)
        if (valid_upstreams_total  / self.upstreams_total) < 0.6:
            # when less then 60 percent of valid upstreams, the need to flush invalid_upstreams
            self.reset_upstreams_weight()

    @property
    def upstreams_total(self):
        return len(self.upstreams_weight) + len(self.invalid_upstreams)


class AutoStrategyManager(_IStrategyManager):
    pass

class IpStrategyManager(_IStrategyManager):
    pass

class RoundStrategyManager(_IStrategyManager):
    def get_best_upstream(self):
        self.sort_upstreams_weight()
        __hosts = sorted(self.upstreams_weight.keys())
        if not __hosts:
            return

        valid_hosts = set(__hosts) - set(self.__used_hosts)
        assert valid_hosts, 'must have valid hosts'

        _best_upstream = sorted(valid_hosts).pop()
        self.__used_hosts.add(_best_upstream)
        return _best_upstream

    def sort_upstreams_weight(self):
        super(RoundStrategyManager, self).sort_upstreams_weight()
        if self.upstreams_total == len(self.__used_hosts):
            self.__used_hosts.clear()

    def init(self):
        self.upstreams_weight = {}.fromkeys(self.upstream_settings.get('hosts'), 100)
        self.__used_hosts = set()

class WeightStrategyManager(_IStrategyManager):
    def get_best_upstream(self):
        self.sort_upstreams_weight()
        return _rand_upstream_by_weight(self.upstreams_weight)

    def init(self):
        self.upstreams_weight = self.upstream_settings.get('weight')

