import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport(title="Hello, World!", width=300, height=150)

with dpg.window(label="Hello, World!", width=280, height=120):
    dpg.add_button(label="Exit", callback=lambda: dpg.stop_dearpygui())

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
