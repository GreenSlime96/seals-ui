import logging
import cv2

import numpy as np
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

gi.require_version('Vips', '8.0')
from gi.repository import Vips

import rect
import time

# inter-frame delay, in milliseconds
# 50 gives around 20 fps and doesn't overload the machine too badly
frame_timeout = 50

# width of selection box border
select_width = 2

# size of corner resize boxes
select_corner = 15

# scale the original image
scale = 0.25

# we have a small state machine for manipulating the select box
def enum(**enums):
    return type('Enum', (), enums)


SelectState = enum(WAIT=1, DRAG=2, RESIZE=3)

# For each edge direction, the corresponding cursor we select
resize_cursor_shape = {
    rect.Edge.NW:   Gdk.Cursor(Gdk.CursorType.TOP_LEFT_CORNER),
    rect.Edge.NE:   Gdk.Cursor(Gdk.CursorType.TOP_RIGHT_CORNER),
    rect.Edge.SW:   Gdk.Cursor(Gdk.CursorType.BOTTOM_LEFT_CORNER),
    rect.Edge.SE:   Gdk.Cursor(Gdk.CursorType.BOTTOM_RIGHT_CORNER),
    rect.Edge.N:    Gdk.Cursor(Gdk.CursorType.TOP_SIDE),
    rect.Edge.S:    Gdk.Cursor(Gdk.CursorType.BOTTOM_SIDE),
    rect.Edge.E:    Gdk.Cursor(Gdk.CursorType.RIGHT_SIDE),
    rect.Edge.W:    Gdk.Cursor(Gdk.CursorType.LEFT_SIDE)
}

# another cursor for grag
drag_cursor_shape = Gdk.Cursor(Gdk.CursorType.FLEUR)


# clip a number to a range
def clip(lower, value, upper):
    return max(min(value, upper), lower)


class Preview(Gtk.EventBox):
    """A widget displaying a live preview.

    get_live -- return True if the preview is currently live
    set_live -- turn the live preview on and off
    get_selection -- get the currently selected rect.Rect (if any)
    """

    def draw_rect(self, colour, rect, margin):
        window = self.image.get_window()
        cr = window.cairo_create()

        cr.set_source_rgb(*colour)

        cr.rectangle(rect.left - margin,
                     rect.top - margin,
                     rect.width + margin * 2,
                     margin * 2)
        cr.rectangle(rect.right() - margin,
                     rect.top + margin,
                     margin * 2,
                     max(0, rect.height - margin * 2))
        cr.rectangle(rect.left - margin,
                     rect.bottom() - margin,
                     rect.width + margin * 2,
                     margin * 2)
        cr.rectangle(rect.left - margin,
                     rect.top + margin,
                     margin * 2,
                     max(0, rect.height - margin * 2))

        cr.fill()

    # expose on our Gtk.Image
    def expose_event(self, widget, event):
        if self.select_visible:
            self.draw_rect(widget.get_style().white.to_floats(),
                           self.select_area, select_width)
            self.draw_rect(widget.get_style().black.to_floats(),
                           self.select_area, select_width - 1)
        return False

    def button_press_event(self, widget, event):
        x = int(event.x)
        y = int(event.y)
        direction = self.select_area.which_corner(select_corner, x, y)

        if self.select_state == SelectState.WAIT and \
            self.select_visible and \
            direction != rect.Edge.NONE:
            self.select_state = SelectState.RESIZE
            self.resize_direction = direction
            corner = self.select_area.corner(direction)
            (cx, cy) = corner.centre()
            self.drag_x = x - cx
            self.drag_y = y - cy
            self.queue_draw()

        elif self.select_state == SelectState.WAIT and \
            self.select_visible and \
            self.select_area.includes_point(x, y):
            self.select_state = SelectState.DRAG
            self.drag_x = x - self.select_area.left
            self.drag_y = y - self.select_area.top
            self.queue_draw()

        elif self.select_state == SelectState.WAIT and \
            self.select_visible:
            self.select_visible = False
            self.queue_draw()

        elif self.select_state == SelectState.WAIT and \
            not self.select_visible:
            image_width = self.image.get_allocation().width
            image_height = self.image.get_allocation().height

            self.select_visible = True
            self.select_area.width = 3 * select_corner
            self.select_area.height = 3 * select_corner
            self.select_area.left = min(x, image_width-self.select_area.width)
            self.select_area.top = min(y, image_height-self.select_area.height)
            self.select_state = SelectState.RESIZE
            self.resize_direction = rect.Edge.SE
            self.drag_x = 1
            self.drag_y = 1
            self.queue_draw()

    def motion_notify_event(self, widget, event):
        x = int(event.x)
        y = int(event.y)
        image_width = self.image.get_allocation().width
        image_height = self.image.get_allocation().height

        if self.select_state == SelectState.DRAG:
            self.select_area.left = clip(0,
                                         x - self.drag_x,
                                         image_width - self.select_area.width)
            self.select_area.top = clip(0,
                                        y - self.drag_y,
                                        image_height - self.select_area.height)
            self.queue_draw()
        elif self.select_state == SelectState.RESIZE:
            if self.resize_direction in [rect.Edge.SE, rect.Edge.E,
                                         rect.Edge.NE]:
                right = x - self.drag_x
                self.select_area.width = max(right - self.select_area.left,
                                             3 * select_corner)

            if self.resize_direction in [rect.Edge.SW, rect.Edge.S,
                                         rect.Edge.SE]:
                bottom = y - self.drag_y
                self.select_area.height = max(bottom - self.select_area.top,
                                              3 * select_corner)

            if self.resize_direction in [rect.Edge.SW, rect.Edge.W,
                                         rect.Edge.NW]:
                left = min(x - self.drag_x,
                           self.select_area.right() - 3 * select_corner)
                self.select_area.width = self.select_area.right() - left
                self.select_area.left = left

            if self.resize_direction in [rect.Edge.NW, rect.Edge.N,
                                         rect.Edge.NE]:
                top = min(y - self.drag_y,
                          self.select_area.bottom() - 3 * select_corner)
                self.select_area.height = self.select_area.bottom() - top
                self.select_area.top = top

            self.select_area.normalise()
            image = rect.Rect(0, 0, image_width, image_height)
            self.select_area = self.select_area.intersection(image)
            self.queue_draw()

        elif self.select_state == SelectState.WAIT:
            window = self.image.get_window()
            direction = self.select_area.which_corner(select_corner, x, y)
            if self.select_visible and \
                direction != rect.Edge.NONE:
                window.set_cursor(resize_cursor_shape[direction])

            elif self.select_visible and \
                self.select_area.includes_point(x, y):
                window.set_cursor(drag_cursor_shape)

            else:
                window.set_cursor(None)

    def button_release_event(self, widget, event):
        self.select_state = SelectState.WAIT

    def __init__(self, camera):
        """
        Startup.
        camera -- the camera to display, see camera.py
        The preview starts at 640x426 pixels, this may change if the camera
        turns out to have a different size for its preview image.
        """

        Gtk.EventBox.__init__(self)
        self.times = []

        self.image = Gtk.Image()
        self.add(self.image)
        self.image.show()

        self.image.set_app_paintable(True)

        self.frame_image = None
        self.frame_buffer = None
        self.preview_timeout = 0
        self.camera = camera
        self.frame = 0
        self.select_visible = False
        self.select_area = rect.Rect(10, 10, 100, 100)
        self.select_state = SelectState.WAIT
        self.resize_direction = rect.Edge.N
        self.drag_x = 0
        self.drag_y = 0

        self.image.connect_after('draw', self.expose_event)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('button-press-event', self.button_press_event)
        self.connect('motion-notify-event', self.motion_notify_event)
        self.connect('button-release-event', self.button_release_event)

        self.score = None

    def grab_frame(self):
        logging.debug('grabbing frame ..')
        frame = self.camera.preview()

        if self.frame_buffer is frame:
            return

        start_time = time.time()

        image = np.copy(frame['array'])
        small = cv2.resize(image, None, fx=scale, fy=scale)
        height, width, channels = small.shape
        self.frame_image = small.tobytes()

        roi = self.get_selection()
        if roi is not None:
            roi = image[roi.top:roi.top + roi.height,
                        roi.left:roi.left + roi.width]
        else:
            roi = small

        roi = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        score = cv2.Laplacian(roi, cv2.CV_32F).var()

        self.score_label.set_text("Score: {:.2f}".format(score))

        # try:
        #     roi = cv2.resize(roi, None, fx=scale, fy=scale)
        # except:
        #     print(roi.shape)

        # roi = Vips.Image.new_from_memory_copy(roi.tobytes(),
        #                                       roi.shape[1],
        #                                       roi.shape[0],
        #                                       roi.shape[2],
        #                                       Vips.BandFormat.UCHAR)
        #
        # self.score = str(roi.conv(mask).deviate() ** 2)
        # self.score = print(laplace(roi).var())

        # print('tt: %f' % (time.time() - start_time))
        self.times.append(time.time() - start_time)

        pixbuf = GdkPixbuf.Pixbuf.new_from_data(self.frame_image,
                                                GdkPixbuf.Colorspace.RGB,
                                                False,
                                                8,
                                                width,
                                                height,
                                                width * channels,
                                                None, None)

        self.image.set_from_pixbuf(pixbuf)

        self.frame_buffer = frame
        self.frame += 1

    def get_live(self):
        """Return True if the display is currently live."""
        return self.preview_timeout != 0

    def get_selection(self):
        """Return a rect.Rect for the selection, or None if no selection
        is active.
        """
        if not self.select_visible:
            return None

        return rect.Rect(self.select_area.left / scale,
                         self.select_area.top / scale,
                         self.select_area.width / scale,
                         self.select_area.height / scale)

    def live_cb(self):
        self.grab_frame()
        return True

    def fps_cb(self):
        logging.debug('fps = %d', self.frame)
        print('fps = %d' % self.frame)
        # print([min(self.times), max(self.times), sum(self.times) / len(self.times)])
        self.frame = 0
        return True

    def set_live(self, live):
        """Turn the live preview on and off.

        live -- True means start the live preview display
        """
        if live and self.preview_timeout == 0:
            logging.debug('starting timeout ..')
            self.preview_timeout = GLib.timeout_add(frame_timeout, self.live_cb)
            self.fps_timeout = GLib.timeout_add(1000, self.fps_cb)

        elif not live and self.preview_timeout != 0:
            GLib.source_remove(self.preview_timeout)
            self.preview_timeout = 0
            GLib.source_remove(self.fps_timeout)
            self.fps_timeout = 0

        if live:
            # grab a frame immediately so we can get an exception, if there
            # are any
            self.grab_frame()
