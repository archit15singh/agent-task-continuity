"""Independent predicates for the pinned upstream changes."""

from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path.cwd() / "src"))


def check_click():
    import click
    from click.testing import CliRunner

    @click.command(context_settings={"terminal_width": 60})
    @click.pass_context
    def example(ctx):
        click.echo(ctx.terminal_width)

    result = CliRunner().invoke(example, context_settings={"terminal_width": 100})
    assert (result.exit_code, result.output) == (0, "100\n"), result.exception


def check_packaging():
    from packaging import tags

    for abis in (["cp316t"], ["none", "cp316t"], ["abi3t"]):
        result = set(tags.cpython_tags((3, 16), abis, ["platform"]))
        assert tags.Tag("cp315", "abi3t", "platform") in result, abis
        assert all(tag.abi in {"cp316t", "none", "abi3t"} for tag in result), abis
    ordinary = set(tags.cpython_tags((3, 16), ["cp316"], ["platform"]))
    assert tags.Tag("cp315", "abi3", "platform") in ordinary


def check_attrs():
    import attr
    from attr import _funcs

    @attr.define
    class Container:
        payload: object

    class WrappedInt(int):
        pass

    with patch.object(_funcs, "has", wraps=_funcs.has) as checked:
        result = attr.astuple(Container({1: "one", 2: WrappedInt(2), "child": Container(7)}))
    assert result == ({1: "one", 2: 2, "child": (7,)},), result
    assert type(result[0][2]) is WrappedInt
    probed = {call.args[0] for call in checked.call_args_list}
    assert int not in probed and str not in probed, probed


if __name__ == "__main__":
    {"click": check_click, "packaging": check_packaging, "attrs": check_attrs}[sys.argv[1]]()
    print("case predicate passed")
