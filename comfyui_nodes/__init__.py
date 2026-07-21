"""ai-product-scene-generator — ComfyUI custom node pack.

Wraps the V2 Python "brain" (see ../scripts/) as ComfyUI nodes so the pipeline
can run inside ComfyUI and be shared with other users. Two nodes:

  - AnalyzeProductLighting  (pre-generation): product -> positive prompt + shadow_dir
  - CompositeProductScene   (post-generation): background + product -> final composite

Both import the existing shared modules (geometry / analyze_product_light /
prompt_builder) rather than duplicating logic. Tensors are converted to PIL only
at the node boundaries; the internal logic stays PIL (Phase 4 decision #3).

ComfyUI discovers a custom node pack by reading NODE_CLASS_MAPPINGS from this
module. Each node registers itself here as it lands (Phase 4 tasks 3 & 4).
"""

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def _register(module_name: str) -> None:
    """Import a node module and merge its mappings. Missing modules are skipped
    so the pack still loads cleanly while nodes are being built out."""
    try:
        mod = __import__(f"{__name__}.{module_name}", fromlist=["*"])
    except ImportError:
        return
    NODE_CLASS_MAPPINGS.update(getattr(mod, "NODE_CLASS_MAPPINGS", {}))
    NODE_DISPLAY_NAME_MAPPINGS.update(getattr(mod, "NODE_DISPLAY_NAME_MAPPINGS", {}))


# task 3: analyze node -> comfyui_nodes/node_analyze.py
_register("node_analyze")
# task 4: composite node -> comfyui_nodes/node_composite.py
_register("node_composite")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
