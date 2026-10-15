"""Defaults for the CLI from a TOML file: one section per subcommand, keys named after the long flags."""
import argparse
import os
import sys
import tomllib

FILENAME = "muthur.toml"
PATH_KEYS = {"image", "audio", "srt", "font", "out", "keep"}
NOT_CONFIGURABLE = {"help", "config"}


def find(explicit):
    if explicit:
        if not os.path.isfile(explicit):
            sys.exit(f"config file not found: {explicit}")
        return explicit
    return FILENAME if os.path.isfile(FILENAME) else None


def load(path):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        sys.exit(f"{path}: {e}")


def options(parser):
    return {a.dest: a for a in parser._actions
            if a.option_strings and a.dest not in NOT_CONFIGURABLE}


def defaults(parser, section, values, path):
    allowed = options(parser)
    base = os.path.dirname(os.path.abspath(path))
    out = {}
    for key, value in values.items():
        action = allowed.get(key)
        if action is None:
            sys.exit(f"{path}: unknown key [{section}].{key}")
        where = f"{path}: [{section}].{key}"
        if isinstance(action, argparse.BooleanOptionalAction):
            if not isinstance(value, bool):
                sys.exit(f"{where} must be true or false")
        elif isinstance(action, argparse._AppendAction):
            if not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
                sys.exit(f"{where} must be a list of strings")
            key = "config_" + key
        elif action.type is int:
            if type(value) is not int:
                sys.exit(f"{where} must be a whole number")
        elif not isinstance(value, str):
            sys.exit(f"{where} must be a string")
        if action.choices is not None and value not in action.choices:
            sys.exit(f"{where} must be one of: {', '.join(action.choices)}")
        if key in PATH_KEYS:
            value = os.path.join(base, os.path.expanduser(value))
        out[key] = value
    return out


def apply(subparsers, data, path):
    for section, values in data.items():
        parser = subparsers.get(section)
        if parser is None or not isinstance(values, dict):
            sys.exit(f"{path}: unknown section [{section}]")
        parser.set_defaults(**defaults(parser, section, values, path))
