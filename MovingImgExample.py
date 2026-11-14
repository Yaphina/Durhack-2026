import dearpygui.dearpygui as dpg
import numpy

# Return True when image has arrived at destination
# Return False when image has not arrived at destination
def moveTo(destinationPos, imageTag):
    
    # Speed at which the image moves
    SPEED = 2

    imgPos = dpg.get_item_pos(imageTag)
    length = [numpy.abs(destinationPos[0] - imgPos[0]), numpy.abs(destinationPos[1] - imgPos[1])]
    
    # Checks the distance between image and detination if it is 0 where it is at destination
    if (length[0] == 0):
        # Returns true as piece has arrived at destination
        dpg.configure_item(imageTag, pos=destinationPos)
        return True
    
    # Calculate the cardinal speed
    angle = numpy.arctan(length[1] / length[0])
    xSpeed = numpy.cos(angle) * SPEED
    ySpeed = numpy.sin(angle) * SPEED
    # Calculates direction in which the image should move
    xDirection = numpy.sign(destinationPos[0] - imgPos[0])
    yDirection = numpy.sign(destinationPos[1] - imgPos[1])
    # New destination for the image after one frame
    newPos = (imgPos[0] + (xSpeed * xDirection), imgPos[1] + (ySpeed * yDirection))
        
    # When the image has not arrived at destination yet
    dpg.configure_item(imageTag, pos=newPos)
    return False

dpg.create_context()
dpg.create_viewport(title="Hello, World!", width=1440, height=900)

width, height, channels, data = dpg.load_image("mona lisa 4x4 puzzle/piece1.png")
width, height, channels, data = dpg.load_image("mona lisa 4x4 puzzle/piece2.png")


SCALER = 1
with dpg.texture_registry():
    dpg.add_static_texture(width=width * SCALER, height=height * SCALER, default_value=data, tag="p1")
    dpg.add_static_texture(width=width * SCALER, height=height * SCALER, default_value=data, tag="p2")

with dpg.window(label="Hello, World!", tag = "Primary Window", width=1440, height=900):
    dpg.add_image("p1", pos=(0, 100), tag="piece1")
    dpg.add_image("p1", pos=(1000, 100), tag="piece2")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)


while dpg.is_dearpygui_running():
    
    targetPos = dpg.get_item_pos("piece2")
    moveTo(targetPos, "piece1") 

    targetPos = dpg.get_item_pos("piece1")
    moveTo(targetPos, "piece2")
    

    dpg.render_dearpygui_frame()
    
dpg.destroy_context()