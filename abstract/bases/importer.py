import pathlib
import queue
import time
import traceback
import functools
import threading
import pymysql
from plum import dispatch
import abc
import requests
from collections.abc import Iterable
import fractions
import openai
import base64
import datetime
import getopt
import io
import random
import filetype
import numpy
import psutil
import itertools
import operator
import json
import sys
import inspect
import git
import urllib3
import os
import select
import enum
import cairosvg
import matplotlib
import matplotlib.patheffects
import matplotlib.pyplot
import matplotlib.dates
import matplotlib.font_manager
import pandas
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import warnings
import copy
import socket
import platform
import decimal
import typing
LAST_COMMIT = git.Repo(pathlib.Path(__file__).parents[2]).head.commit
def local_time():
    return datetime.datetime.now().astimezone()
LOCAL_TIMEZONE = local_time().tzinfo
LOCAL_TIMESHIFT = LOCAL_TIMEZONE.utcoffset(datetime.datetime.now())
UTC_TIMEZONE = datetime.timezone.utc
def today_7am():
    replaced_localtime = local_time().replace(hour=7, minute=0, second=0, microsecond=0)
    if local_time() > replaced_localtime:
        return replaced_localtime
    return replaced_localtime + datetime.timedelta(days=-1)
