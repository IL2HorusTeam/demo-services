# coding: utf-8

import copy

import yaml

from jsonschema import validate

from il2fb.demo_services.core.utils import update_nested_dict


CONFIG_SCHEMA = {
    'type': 'object',
    'properties': {
        'bind': {
            'type': 'object',
            'properties': {
                'address': {
                    'format': 'hostname',
                },
                'port': {
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 65535,
                },
            },
            'required': ['address', 'port', ]
        },
        'debug': {
            'type': 'boolean',
        },
        'logging': {
            'type': 'object',
        },
        'access_log_format': {
            'type': 'string',
        },
        'cors': {
            'type': 'object',
        }
    },
    'required': ['bind', 'logging', 'access_log_format', ]
}

CONFIG_DEFAULTS = {
    'bind': {
        'address': "127.0.0.1",
        'port': 5000,
    },
    'debug': False,
    'logging': {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '[%(levelname)-8s %(asctime)s %(name)s] %(message)s',
                'datefmt': '%Y-%m-%dT%H:%M:%S%z',
            },
        },
        'handlers': {
            'default': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': True,
            },
        },
    },
    'access_log_format': (
        '%a %l %u "%r" %s %b %Dms "%{Referrer}i" "%{User-Agent}i"'
    ),
    'cors': {},
}


def load_config(path=None):
    config = copy.deepcopy(CONFIG_DEFAULTS)

    if path:
        with open(path, 'r') as f:
            custom = yaml.load(f.read())
            if custom:
                update_nested_dict(config, custom)

    validate(config, CONFIG_SCHEMA)
    return config
