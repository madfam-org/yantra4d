"""Pure manifest parameter normalization shared by API and trusted batch renders.

The public API wrapper still obtains the manifest and retains its existing contract.
This module imports no renderer, configuration, request or worker state.
"""
import logging
import re

logger = logging.getLogger(__name__)


def validate_parameters(params: dict, definitions: list) -> dict:
    """Apply the API’s parameter types, declared select values and numeric bounds."""
    param_defs = {p["id"]: p for p in definitions}
    pass_through_keys = {"mode", "scad_file", "parameters"}
    cleaned = {}

    for key, value in params.items():
        if key in pass_through_keys:
            continue

        if key not in param_defs:
            logger.warning(f"Rejecting unknown parameter: {key}")
            continue

        defn = param_defs[key]
        param_type = defn.get("type", "slider")

        if param_type == "slider":
            try:
                num_val = float(value)
            except (TypeError, ValueError):
                logger.warning(f"Rejecting non-numeric value for {key}: {value}")
                continue
            min_val = defn.get("min")
            max_val = defn.get("max")
            if min_val is not None and num_val < float(min_val):
                num_val = float(min_val)
            if max_val is not None and num_val > float(max_val):
                num_val = float(max_val)
            cleaned[key] = num_val
        elif param_type == "select":
            # Native HTML selects may send strings, but the declared option
            # owns the kernel type. Quoting a numeric enum changes geometry.
            options = [option["value"] for option in defn.get("options", [])
                       if isinstance(option, dict) and "value" in option]
            matches = []
            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                matches = [option for option in options
                           if not isinstance(option, bool) and type(option) is type(value) and option == value]
                if not matches:
                    matches = [option for option in options
                               if isinstance(option, (str, int, float)) and not isinstance(option, bool)
                               and (str(option) == str(value)
                                    or (isinstance(option, (int, float)) and isinstance(value, (int, float))
                                        and option == value))]
            if len(matches) != 1:
                logger.warning("Rejecting undeclared or ambiguous select value for %s", key)
                continue
            cleaned[key] = matches[0]
        elif param_type == "text":
            str_val = str(value)
            if not re.match(r'^[a-zA-Z0-9 _.#,-]*$', str_val):
                logger.warning(f"Rejecting unsafe text value for {key}")
                continue
            maxlen = defn.get("maxlength", 255)
            if len(str_val) > maxlen:
                str_val = str_val[:maxlen]
            cleaned[key] = str_val
        elif param_type == "checkbox":
            if isinstance(value, bool):
                cleaned[key] = 1 if value else 0
            elif isinstance(value, (int, float)) and value in (0, 1, 0.0, 1.0):
                cleaned[key] = int(value)
            elif str(value).lower() in ("true", "false"):
                cleaned[key] = 1 if str(value).lower() == "true" else 0
            else:
                logger.warning(f"Rejecting non-boolean value for {key}: {value}")
                continue
        else:
            str_val = str(value)
            if not re.match(r'^[a-zA-Z0-9_]+$', str_val):
                logger.warning(f"Rejecting non-alphanumeric string for {key}: {value}")
                continue
            cleaned[key] = str_val

    # Explicitly remove render_mode if present, as it's handled via the mode ID
    cleaned.pop('render_mode', None)

    return cleaned

