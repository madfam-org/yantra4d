"""The node-pack interface: what a kernel gives the core, and what the core asks of it.

The core knows the graph — nodes, typed sockets, parameters, expressions, declarations —
and nothing about geometry. A kernel plugs in through one object, a **node pack**:

* a **catalogue**: every node type the kernel transpiles, each with typed params (a
  *kind*, a default, whether a manifest parameter may bind it and whether it takes an
  expression), typed input sockets and one typed output socket;
* the **socket types** it speaks and which of them a graph may name as an output part;
* the **script contract**: the source languages its sandbox runs for a ``script`` node
  and the socket types a script may yield (see ``script_node``);
* the **identifiers it reserves** in the program it emits, which a parameter, a derived
  value or a script binding may not shadow;
* a **transpiler** from a validated pack document to the kernel's program text.

The solid pack is Yantra4D's graph engine (23 nodes, ``solid``/``profile`` sockets,
CadQuery out). The soft pack (Fashion Cabinet's drafting kernel) and the sheet pack
(Pliego's fold kernel) implement the same interface when they are built; nothing in the
core names a kernel.

A pack is any object with these attributes; ``NodePack`` is the Protocol a type checker
reads. ``catalogue_from_json`` builds the catalogue from the JSON catalogue a kernel
already publishes (Yantra4D's ``graph-node-catalog.json`` shape), so a kernel does not
describe its nodes twice.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .errors import GraphCoreError

__all__ = [
    "KERNELS",
    "NodePack",
    "NodeSpec",
    "ParamKind",
    "ParamSpec",
    "ScriptContract",
    "SocketSpec",
    "catalogue_from_json",
    "export_catalogue",
]

#: The three commons kernels. A graph names one in ``kernel`` (format 1.2); a 1.0 or 1.1
#: document predates the field and is a solid graph, the only kind that existed.
KERNELS = ("solid", "soft", "sheet")


@dataclass(frozen=True)
class ParamKind:
    """The per-kind contract a catalogue publishes, so an editor can render an input
    for a kind it has never seen.

    ``bindable``: a manifest parameter may drive it through ``binding``.
    ``expr``: it accepts ``{"expr": ...}``. ``literal``: what a literal looks like.
    """

    name: str
    bindable: bool
    expr: bool
    literal: str


@dataclass(frozen=True)
class ParamSpec:
    kind: str
    default: object
    bindable: bool = False
    expr: bool = False


@dataclass(frozen=True)
class SocketSpec:
    """A typed input socket. ``required`` sockets must be connected."""

    type: str
    required: bool = True


@dataclass(frozen=True)
class NodeSpec:
    type: str
    output: str
    params: Mapping[str, ParamSpec] = field(default_factory=dict)
    inputs: Mapping[str, SocketSpec] = field(default_factory=dict)


@dataclass(frozen=True)
class ScriptContract:
    """What a kernel's sandbox runs for a ``script`` node.

    ``languages`` maps a language id to the source suffixes it accepts
    (solid: ``{"cadquery": (".py", ".cq"), "openscad": (".scad",)}``). ``outputs`` are
    the socket types a script node may declare as its output. ``part_parameter`` is the
    name under which the kernel's runner passes the selected output part to a source
    (solid: ``target_part``); the wrapper lowering passes it through unchanged.
    ``reserved`` are the names the runner defines for every source (solid: ``cq`` and
    ``math``), which a binding may not overwrite.
    """

    languages: Mapping[str, tuple[str, ...]]
    outputs: tuple[str, ...]
    part_parameter: str
    reserved: frozenset[str] = frozenset()


@runtime_checkable
class NodePack(Protocol):
    """The interface a kernel implements to plug its vocabulary into the core."""

    #: One of ``KERNELS``.
    kernel: str
    #: A stable pack name (``"yantra4d-solid"``) and the version of its vocabulary.
    name: str
    version: str
    #: Every socket type this pack's nodes produce or consume.
    socket_types: frozenset[str]
    #: The socket types a graph's ``outputs`` may reference (solid: ``{"solid"}``).
    output_types: frozenset[str]
    #: Socket types whose output may feed at most N consumers (solid: a ``profile``
    #: holds pending wires the first consumer takes, so ``{"profile": 1}``).
    fan_out: Mapping[str, int]
    #: Names the emitted program defines or the runner injects.
    reserved_identifiers: frozenset[str]
    script: ScriptContract | None
    #: Whether ``transpile`` lowers a ``script`` node inside a native graph. A pack that
    #: does not still serves wrappers, which are rendered by invoking the source.
    embedded_scripts: bool

    def catalogue(self) -> Mapping[str, NodeSpec]:
        """node type → spec. Must not contain ``script``: the core owns that node."""
        ...

    def param_kinds(self) -> Mapping[str, ParamKind]:
        """kind name → contract, for every kind the catalogue uses."""
        ...

    def transpile(self, pack_doc: dict, bindings: dict, source_name: str) -> str:
        """The kernel program for a validated document with no core-only keys.

        ``bindings`` maps ``(node id, param name)`` to the declared parameter id that
        drives it. Raises the kernel's own error type on anything the kernel refuses
        (value ranges, geometry-specific rules the core cannot know).
        """
        ...


def catalogue_from_json(catalog: Mapping) -> tuple[dict[str, NodeSpec], dict[str, ParamKind]]:
    """Read a kernel's published JSON node catalogue (Yantra4D's shape).

    ``{"param_kinds": {kind: {bindable, expr, literal}},
       "nodes": {type: {"output": t, "inputs": {socket: t}, "params": {name: {kind,
       default, bindable, expr}}}}}``. An input socket may also be written
    ``{"type": t, "required": false}``.
    """
    kinds: dict[str, ParamKind] = {}
    for name, spec in (catalog.get("param_kinds") or {}).items():
        kinds[name] = ParamKind(
            name=name,
            bindable=bool(spec.get("bindable")),
            expr=bool(spec.get("expr")),
            literal=str(spec.get("literal", "")),
        )
    nodes: dict[str, NodeSpec] = {}
    for node_type, spec in (catalog.get("nodes") or {}).items():
        params = {}
        for pname, p in (spec.get("params") or {}).items():
            if p.get("kind") not in kinds:
                raise GraphCoreError(
                    f"catalogue: {node_type}.{pname} has unknown kind {p.get('kind')!r}",
                    code="catalogue",
                )
            params[pname] = ParamSpec(
                kind=p["kind"],
                default=p.get("default"),
                bindable=bool(p.get("bindable")),
                expr=bool(p.get("expr")),
            )
        inputs = {}
        for socket, t in (spec.get("inputs") or {}).items():
            if isinstance(t, Mapping):
                inputs[socket] = SocketSpec(type=t["type"], required=t.get("required", True))
            else:
                inputs[socket] = SocketSpec(type=t)
        nodes[node_type] = NodeSpec(
            type=node_type, output=spec["output"], params=params, inputs=inputs
        )
    return nodes, kinds


def export_catalogue(pack: NodePack) -> dict:
    """The pack's vocabulary as neutral JSON, for an editor palette in any commons.

    Includes the core's ``script`` node when the pack declares a script contract, so a
    palette built from this never has to special-case it.
    """
    from .script_node import SCRIPT_NODE_TYPE, script_node_catalogue_entry

    nodes = {}
    for node_type, spec in sorted(pack.catalogue().items()):
        nodes[node_type] = {
            "output": spec.output,
            "inputs": {
                s: ({"type": i.type} if i.required else {"type": i.type, "required": False})
                for s, i in sorted(spec.inputs.items())
            },
            "params": {
                n: {"kind": p.kind, "default": p.default, "bindable": p.bindable,
                    "expr": p.expr}
                for n, p in sorted(spec.params.items())
            },
        }
    if pack.script is not None:
        nodes[SCRIPT_NODE_TYPE] = script_node_catalogue_entry(pack.script)
    return {
        "kernel": pack.kernel,
        "pack": pack.name,
        "pack_version": pack.version,
        "socket_types": sorted(pack.socket_types),
        "output_types": sorted(pack.output_types),
        "fan_out": dict(sorted(pack.fan_out.items())),
        "param_kinds": {
            k: {"bindable": v.bindable, "expr": v.expr, "literal": v.literal}
            for k, v in sorted(pack.param_kinds().items())
        },
        "nodes": nodes,
    }
