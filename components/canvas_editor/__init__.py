import streamlit.components.v1 as components
import os

_component_func = components.declare_component(
    "canvas_editor",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
)

def canvas_editor(width=700, height=450, grid_px=25, mm_per_cell=500,
                  is_dark=True, initial_vertices_mm=None, key=None):
    """
    Custom interactive canvas with real-time dimension and angle annotations.
    Returns list of vertices in mm: [[x_mm, y_mm], ...]
    """
    mm_per_px = mm_per_cell / grid_px
    result = _component_func(
        width=width, height=height, gridPx=grid_px,
        mmPerCell=mm_per_cell, mmPerPx=mm_per_px,
        isDark=is_dark,
        initialVerticesMm=initial_vertices_mm or [],
        key=key, default=[]
    )
    return result if result else []
