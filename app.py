#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from flask import Flask, render_template, redirect
from flask_sockets import Sockets
import json
import redis

import gevent


REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
REDIS_CHAN = 'bus'
REDIS_STATE = 'actives'


app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)
redis = redis.from_url(REDIS_URL)


class Backend(object):
    def __init__(self):
        self.clients = list()
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe(REDIS_CHAN)

    def __iter_data(self):
        for message in self.pubsub.listen():
            data = message.get('data')
            if message['type'] == 'message':
                yield data

    def register(self, client):
        """Registers a WebSocket connection for Redis updates."""
        self.clients.append(client)

    def send(self, client, data):
        """Sends given data to the registered client."""
        try:
            client.send(data)
        except Exception:
            self.clients.remove(client)

    def run(self):
        """Listens for new messages in Redis and forwards them to clients."""
        for data in self.__iter_data():
            for client in self.clients:
                gevent.spawn(self.send, client, data)

    def start(self):
        """Maintains Redis subscription in the background."""
        gevent.spawn(self.run)

    def get_actives(self):
        return [int(e) for e in redis.smembers(REDIS_STATE)]

    def set_state(self, number):
        return redis.sadd(REDIS_STATE, number)

    def reset_state(self):
        return redis.delete(REDIS_STATE)


backend = Backend()
backend.start()


@app.route('/')
def index():
    return render_template('index.html', actives=backend.get_actives())


@app.route('/reset')
def reset():
    backend.reset_state()
    return redirect('/')


@sockets.route('/submit')
def inbox(ws):
    """Receives incoming messages."""
    while not ws.closed:
        gevent.sleep(0.1)
        message = ws.receive()

        if message:
            data = json.loads(message)
            backend.set_state(data.get('id'))
            redis.publish(REDIS_CHAN, message)


@sockets.route('/receive')
def outbox(ws):
    backend.register(ws)

    while not ws.closed:
        gevent.sleep(0.1)
