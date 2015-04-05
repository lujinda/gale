#!/usr/bin/env python
#coding:utf-8
from __future__ import unicode_literals, print_function

from jinja2 import Environment, FileSystemLoader
from os import path

def Env(template_settings):
    template_path = template_settings.pop('template_path', 
            path.join(path.dirname(path.abspath(__file__)), '../template'))
    loader = FileSystemLoader(template_path)

    return Environment(loader = loader, **template_settings)

