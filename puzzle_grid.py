import dearpygui.dearpygui as dpg
from piece import Piece
import os


def render_grid(arr):
    with dpg.table(header_row=False, resizable=True, borders_outerH=True, borders_innerV=True, 
                   borders_innerH=True, borders_outerV=True):
        
        for _ in range(4):
            dpg.add_table_column()

        for row in arr:
            with dpg.table_row():
                for cell in row:
                    if cell == -1:
                        dpg.add_button(label="[EMPTY]", width=50, height=100)
                    else:
                        piece_num = cell.destination
                        path = f"mona lisa 4x4 puzzle/piece{piece_num}.png"
                        texture_tag = f"texture_piece_{piece_num}"
                        
                        if not dpg.does_item_exist(texture_tag):
                            width, height, channels, data = dpg.load_image(path)
                            with dpg.texture_registry(show=False):
                                dpg.add_static_texture(width=width, height=height, default_value=data, tag=texture_tag)
                        
                        dpg.add_image(texture_tag, width=417, height=418)

dpg.create_context()
dpg.create_viewport(title='Puzzle Scratchpad Test', width=800, height=800)


with dpg.window(tag="Primary Window", label="Puzzle Board Window", width=780, height=760):
    dpg.add_text("Scratchpad Grid View:")
    
    render_grid(scratchpad)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)
dpg.start_dearpygui()
dpg.destroy_context()