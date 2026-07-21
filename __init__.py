"""ComfyUI entry point for the ai-product-scene-generator node pack.

When this repo is cloned into ComfyUI/custom_nodes/, ComfyUI loads this file and
reads NODE_CLASS_MAPPINGS from it. The actual node code lives in the comfyui_nodes/
subpackage (which also imports the shared brain in scripts/); we just re-export
its mappings here so the standard "git clone into custom_nodes" install works.
"""

from .comfyui_nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
