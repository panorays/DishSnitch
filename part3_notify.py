#!/usr/bin/env python
"""Post slack message."""

import os

import requests
from slacker import Slacker

import config
import global_vars

# https://github.com/os/slacker
# https://api.slack.com/methods


def post_slack(bad_guy):
    """Post slack message."""
    slack = Slacker(config.slack_token)

    obj = slack.chat.post_message(config.slack_channel, ' '.join([bad_guy, 'left dirty dishes today!']))
    print(obj.successful, obj.__dict__['body']['channel'], obj.__dict__['body']['ts'])

    dirty_dishes_image_path = os.path.join(config.saved_images_dir, 'saved_img.jpg')
    my_file = {
        'file': (dirty_dishes_image_path, open(dirty_dishes_image_path, 'rb'), 'jpg')
    }

    payload = {
        "filename": "proof.jpg",
        "token": config.slack_token,
        "channels": [config.slack_channel],
    }

    r = requests.post("https://slack.com/api/files.upload", params=payload, files=my_file)


if __name__ == '__main__':
    post_slack()

