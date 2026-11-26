"""Hidden behavior probes evaluated against the pinned parent, reference, and candidate."""

from itertools import product
import json
from pathlib import Path
import sys


def observe(probe):
    try:
        return {"value": probe()}
    except Exception as error:
        return {"exception": type(error).__name__}


def click_probes():
    import click
    from click.testing import CliRunner

    def command(help_text, deprecated, width):
        cmd = click.Command("demo", help=help_text, deprecated=deprecated)
        result = CliRunner().invoke(cmd, ["--help"], terminal_width=width)
        return [result.exit_code, result.output]

    def option(help_text, deprecated):
        opt = click.Option(["--mode"], type=click.Choice(["one", "two"]),
                           help=help_text, deprecated=deprecated)
        with click.Context(click.Command("demo")) as context:
            return opt.get_help_record(context)

    help_texts = (None, "", " ", "Switch output mode.", "Line one.\n\nSecond paragraph.")
    reasons = (False, True, "Use the replacement")
    results = {}
    for text, reason in product(help_texts, reasons):
        for width in (37, 80):
            results[f"command/{text!r}/{reason!r}/{width}"] = observe(lambda: command(text, reason, width))
        results[f"option/{text!r}/{reason!r}"] = observe(lambda: option(text, reason))
    return results


def packaging_probes():
    from packaging._parser import Value
    from packaging.markers import Marker
    from packaging.requirements import Requirement

    def round_trip(source, kind):
        original = kind(source)
        serialized = str(original)
        return [serialized, kind(serialized) == original]

    literals = (
        ("plain", '"'), ("", "'"), ("two words", "'"), ("café", '"'),
        ('a"b', "'"), ('"quoted"', "'"), ('multiple "" marks', "'"),
        ("a'b", '"'), ("'quoted'", '"'), ("multiple '' marks", '"'),
    )
    results = {}
    for (value, quote), variable, operator in product(literals, ("platform_release", "platform_version"), ("==", "!=")):
        expression = f"{variable} {operator} {quote}{value}{quote}"
        for variant in ("plain", "compound"):
            fragment = expression if variant == "plain" else f'({expression} or os_name == "posix") and sys_platform != "win32"'
            results[f"marker/{variant}/{expression}"] = observe(lambda: round_trip(fragment, Marker))
            results[f"requirement/{variant}/{expression}"] = observe(
                lambda: round_trip(f"example[tool]>=1; {fragment}", Requirement),
            )
    for value in ("plain", "", 'double"', "single'", """both'" """):
        results[f"value/{value!r}"] = observe(lambda: Value(value).serialize())
    return results


def attrs_probes():
    import attrs
    from attrs.converters import pipe

    def build(convert, takes_self, takes_field, variant):
        adapter = attrs.Converter(convert, takes_self=takes_self, takes_field=takes_field)
        if variant == "plain":
            return adapter
        if variant == "pipe":
            return pipe(int, adapter, str)
        return pipe(int, pipe(adapter, str), str.upper)

    def check(takes_self, takes_field, variant, phase):
        calls = []

        def convert(value, *context):
            calls.append([
                type(value).__name__, str(value),
                [(type(item).__name__, getattr(item, "name", getattr(item, "prefix", None))) for item in context],
            ])
            return int(value) + 3

        try:
            converter = build(convert, takes_self, takes_field, variant)

            @attrs.define
            class Sample:
                prefix = attrs.field(default="xyz")
                item = attrs.field(default="2", converter=converter)

            if phase == "adapter":
                instance_arg = type("InstanceArg", (), {"prefix": "instance"})()
                field_arg = type("FieldArg", (), {"name": "field"})()
                result = converter("4", instance_arg, field_arg)
            else:
                instance = Sample()
                if phase == "assignment":
                    calls.clear()
                    instance.item = "4"
                result = instance.item
            return [type(result).__name__, result, calls]
        except Exception as error:
            return {"exception": type(error).__name__, "calls": calls}

    def regular():
        @attrs.define
        class Standard:
            item = attrs.field(converter=int)

        item = Standard("2")
        item.item = "4"
        return item.item

    results = {"ordinary-callable": observe(regular)}
    for own, field, variant, phase in product(
        (False, True), (False, True), ("plain", "pipe", "nested"), ("constructor", "assignment", "adapter"),
    ):
        results[f"{own}/{field}/{variant}/{phase}"] = check(own, field, variant, phase)
    return results


if __name__ == "__main__":
    sys.path.insert(0, str(Path("src").resolve()))
    probes = {"click-help": click_probes, "packaging-quotes": packaging_probes, "attrs-converter": attrs_probes}
    print(json.dumps(probes[sys.argv[1]](), sort_keys=True))
