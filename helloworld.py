import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport(title='Puzzle Solver', width=1000, height=750)

with dpg.window(tag="Primary Window"):
    dpg.add_text("Puzzle: Mona Lisa")
    dpg.add_button(label="pause")
    dpg.add_button(label="Resume")
    dpg.add_button(label="Restart")


    
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)
dpg.start_dearpygui()
dpg.destroy_context()
