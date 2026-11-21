"""hyperobject-graph — the kernel-neutral graph core of the hyperobjects commons.

RFC 0067 (ruling G-2): one graph format, three node vocabularies. This package is the
shared half — the document format, typed sockets, parameters and derived values, the
1.1 expression dialect, validation (cycles, socket types, dangling references, unbound
inputs), declarations with i18n label keys, licence and provenance, the node-pack
interface a kernel implements, and the ``script`` node contract. It knows no geometry.

Each kernel (solid: Yantra4D; soft: Fashion Cabinet; sheet: Pliego) implements a
``NodePack`` and **vendors this package by hash** (``core.lock.json``; see
``docs/GRAPH_CORE.md`` › "Vendoring the core"). The package is stdlib-only and imports
nothing outside itself, so a copy of the directory is the whole dependency.

    from hyperobject_graph import validate, transpile, wrapper_plan

    problems = validate(doc, pack, parameters=manifest["parameters"])
    plan = wrapper_plan(doc, pack)           # a pure wrapper: render its source
    program = transpile(doc, pack, ...)      # a native graph: the pack's program
"""

from .declarations import (
    DECLARATION_KEYS,
    LOCALES,
    PARAMETER_TYPES,
    i18n_gaps,
    label_keys,
    manifest_projection,
)
from .errors import GraphCoreError, Problem
from .expression import (
    MAX_EXPR_LENGTH,
    MAX_EXPR_TOKENS,
    evaluate,
    expression_names,
    parse_expression,
    truthy,
)
from .pack import (
    KERNELS,
    NodePack,
    NodeSpec,
    ParamKind,
    ParamSpec,
    ScriptContract,
    SocketSpec,
    catalogue_from_json,
    export_catalogue,
)
from .provenance import source_digest_problems
from .script_node import (
    SCRIPT_CONTRACT_VERSION,
    SCRIPT_NODE_TYPE,
    WrapperPlan,
    wrapper_plan,
)
from .validate import (
    CORE_KEYS,
    FORMAT_VERSION,
    PACK_KEYS,
    binding_parameters,
    check,
    extract_bindings,
    format_minor,
    pack_document,
    transpile,
    validate,
)

#: The version of this package's contract. A kernel's vendored copy states it in its
#: lock; a change that moves what a valid document is bumps it.
CORE_VERSION = "1.0.0"

__all__ = [
    "CORE_KEYS",
    "CORE_VERSION",
    "DECLARATION_KEYS",
    "FORMAT_VERSION",
    "KERNELS",
    "LOCALES",
    "MAX_EXPR_LENGTH",
    "MAX_EXPR_TOKENS",
    "PACK_KEYS",
    "PARAMETER_TYPES",
    "SCRIPT_CONTRACT_VERSION",
    "SCRIPT_NODE_TYPE",
    "GraphCoreError",
    "NodePack",
    "NodeSpec",
    "ParamKind",
    "ParamSpec",
    "Problem",
    "ScriptContract",
    "SocketSpec",
    "WrapperPlan",
    "binding_parameters",
    "catalogue_from_json",
    "check",
    "evaluate",
    "export_catalogue",
    "expression_names",
    "extract_bindings",
    "format_minor",
    "i18n_gaps",
    "label_keys",
    "manifest_projection",
    "pack_document",
    "parse_expression",
    "source_digest_problems",
    "transpile",
    "truthy",
    "validate",
    "wrapper_plan",
]
