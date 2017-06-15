#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sqlite3
#from flask import g

from flask import Flask, render_template, redirect
from flask_sockets import Sockets
import json
import redis

import gevent


REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
REDIS_CHAN = 'bus'
REDIS_STATE = 'actives'

DATABASE = '/Users/mimak/PycharmProjects/Zawody/V_ZAWODY/baza.sqlite'

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)
redis = redis.from_url(REDIS_URL)







class Backend(object):
    def __init__(self):
        self.clients = list()
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe(REDIS_CHAN)
        self.db = self.get_db()

    def get_db(self):
        #db = getattr(g, '_database', None)
        #if db is None:
        db = sqlite3.connect(DATABASE)
        return db



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
        redis.set(number,1)
        print(number, 'ew')
        return redis.sadd(REDIS_STATE, number)

    def reset_state(self):
        return redis.delete(REDIS_STATE)

    def insert(self, table, fields=(), values=()):
        # g.db is the database connection
        cur = g.db.cursor()
        query = 'INSERT INTO %s (%s) VALUES (%s)' % (
            table,
            ', '.join(fields),
            ', '.join(['?'] * len(values))
        )
        cur.execute(query, values)
        g.db.commit()
        id = cur.lastrowid
        cur.close()
        return id


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


# @app.teardown_appcontext
# def close_connection(exception):
#     db = getattr(g, '_database', None)
#     if db is not None:
#         db.close()



if __name__ == '__main__':
    app.run(debug=True)


