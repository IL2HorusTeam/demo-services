# -*- coding: utf-8 -*-

import six
import traceback
import ujson as json

from geventwebsocket.exceptions import WebSocketError
from operator import itemgetter

from il2fb.parsers.events import parse_string
from il2fb.parsers.events.exceptions import EventParsingError

from project.app import app, sockets
from project.responses import APISuccess, APIError, APIWarning

from .reporting import reporter
from .serializers import shorten_issue


__all__ = ('parse', )


def get_route(router, path, *args, **kwargs):
    full_path = "/api/v1/events-parser/{0}".format(path)
    return router.route(full_path, *args, **kwargs)


def api_route(path, *args, **kwargs):
    return get_route(app, path, *args, **kwargs)


def ws_route(path, *args, **kwargs):
    return get_route(sockets, path, *args, **kwargs)


@api_route('data', methods=['GET'])
def get_data_view():
    return APISuccess({
        'supported_events': get_supported_events(),
    })


def get_supported_events():
    import il2fb.parsers.events.structures.events as events_structures

    def description(structure):
        return six.text_type(
            structure.__doc__.strip().replace('::', ':').replace('    ', '')
        )

    result = (
        getattr(events_structures, name)
        for name in events_structures.__all__
    )
    result = (
        (six.text_type(x.verbose_name), description(x))
        for x in result
    )
    return sorted(result, key=itemgetter(0))


@ws_route('parse')
def parse(ws):
    while True:
        data = receive_data(ws)
        if data is None:
            break
        else:
            try_to_parse_string(ws, data.get('string'))


def receive_data(ws):
    try:
        message = ws.receive()
    except WebSocketError:
        message = None

    if message is not None:
        try:
            data = json.loads(message)
        except ValueError as e:
            app.logger.exception(
                "Failed to read message '{:}':".format(message))
            ws.send(APIError(e))
        else:
            return data


def try_to_parse_string(ws, string):
    if string:
        try:
            event = parse_string(string).to_primitive()
        except EventParsingError:
            on_error(ws, string)
        else:
            ws.send(APISuccess({'event': event}))
    else:
        ws.send(APIError("Nothing to parse"))


def on_error(ws, string):
    app.logger.exception(string)

    similar = map(shorten_issue, reporter.get_similar_issues(title=string))
    payload = {
        'similar': similar,
        'traceback': traceback.format_exc(),
    }

    issue = reporter.get_issue(string)
    if issue:
        issue = shorten_issue(issue)
        payload['issue'] = issue

        if issue['state'] == 'open' or not issue['is_valid']:
            ws.send(APIError(payload=payload))
        else:
            reopen_issue(ws, issue, payload)
    else:
        report_new_issue(ws, string, payload)


def reopen_issue(ws, issue, payload):
    ws.send(APIWarning(payload=payload))
    data = receive_data(ws)
    if data and data.get('confirm'):
        reporter.reopen_issue(issue)
        ws.send(APISuccess())


def report_new_issue(ws, title, payload):
    ws.send(APIWarning(payload=payload))
    data = receive_data(ws)
    if data and data.get('confirm'):
        issue = reporter.report_issue(title=title)
        issue = shorten_issue(issue)
        ws.send(APISuccess({'issue': issue}))
