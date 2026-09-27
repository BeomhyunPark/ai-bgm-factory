from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .config import FactoryError
from .util import read_json, scan_secrets


@lru_cache
def validator(name):
    schema = read_json(Path(__file__).parent / "schemas" / f"{name}.schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate(name, obj):
    try:
        validator(name).validate(obj)
    except ValidationError:
        raise FactoryError(f"{name} schema validation failed") from None
    scan_secrets(obj)
