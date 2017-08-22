import PyCapture2
import logging
import os

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GLib

class Config(Gtk.Window):
    """Display and edit the camera config."""

    def destroy_cb(self, widget, data = None):
        if self.refresh_timeout:
            GLib.source_remove(self.refresh_timeout)
            self.refresh_timeout = 0

        self.destroy()

    def refresh_item(self, name):
        self.updating[name] = True

        p = self.camera.getProperty(name)
        pi = self.camera.getPropertyInfo(name)

        onoff = self.onoff_table[p.type]
        auto = self.auto_table[p.type]
        value = self.value_table[p.type]

        min_val = pi.absMin
        max_val = pi.absMax
        val = p.absValue

        if not p.absControl:
            min_val = pi.min
            max_val = pi.max
            val = p.valueA

        if pi.onOffSupported:
            onoff.set_active(p.onOff)
            onoff.show()
        else:
            onoff.hide()

        if pi.autoSupported:
            auto.set_active(p.autoManualMode)
            auto.show()
        else:
            auto.hide()

        if name == PyCapture2.PROPERTY_TYPE.WHITE_BALANCE:
            value[0].configure(p.valueA, min_val, max_val, 1, 0, 0)
            value[1].configure(p.valueB, min_val, max_val, 1, 0, 0)
        else:
            value.configure(val, min_val, max_val, 1, 0, 0)

        self.updating[name] = False

    def refresh(self):
        for p in self.properties.keys():
            self.refresh_item(p)

    def refresh_cb(self, widget, data=None):
        self.refresh()

    def refresh_queue_cb(self):
        self.refresh()
        return True

    def update_item_cb(self, widget, name):
        if self.updating[name]:
            return

        info = self.properties[name]

        onoff = self.onoff_table[name]
        auto = self.auto_table[name]
        value = self.value_table[name]

        kwargs = {'type': name,
                  'onOff': onoff.get_active(),
                  'autoManualMode': auto.get_active()}

        if name == PyCapture2.PROPERTY_TYPE.WHITE_BALANCE:
            kwargs['valueA'] = value[0].get_value()
            kwargs['valueB'] = value[1].get_value()

        elif info.absValSupported:
            kwargs['absValue'] = value.get_value()

        else:
            kwargs['valueA'] = value.get_value()

        self.camera.setProperty(**kwargs)

    def __init__(self, camera):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)

        # retrieve raw camera from the camera wrapper
        self.camera = camera.camera
        self.properties = {}
        self.refresh_timeout = 0
        self.updating = {}

        # get all properties of the camera and exclude private members
        # output as INT: KEY instead
        self.property_types = {v: k for k, v in
                               vars(PyCapture2.PROPERTY_TYPE).items()
                               if not k.startswith('_') and type(v) is int}

        # build properties list
        for k, v in self.property_types.items():
            if k in (PyCapture2.PROPERTY_TYPE.TRIGGER_MODE,
                     PyCapture2.PROPERTY_TYPE.TRIGGER_DELAY,
                     PyCapture2.PROPERTY_TYPE.TEMPERATURE,
                     PyCapture2.PROPERTY_TYPE.UNSPECIFIED_PROPERTY_TYPE):
                continue

            property_info = self.camera.getPropertyInfo(k)

            if property_info.present:
                self.properties[k] = property_info

        # build UI - map UI element to widget ID
        self.value_table = {}
        self.auto_table = {}
        self.onoff_table = {}

        self.set_default_size(800, -1)

        # box = Gtk.Box()
        # box.show()
        # self.add(box)

        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        grid.set_border_width(10)
        self.add(grid)

        # draw header things
        b = Gtk.Label("Auto")
        grid.attach(b, 4, 0, 1, 1)

        b = Gtk.Label("On/Off")
        grid.attach(b, 5, 0, 1, 1)

        i = 1
        for k, p in self.properties.items():
            name = self.property_types[k].replace('_', ' ').title()

            # name label!
            b = Gtk.Label()
            b.set_markup("<b>%s</b>" % name)
            grid.attach(b, 0, i, 1, 1)

            # use absoulte or relative values
            min_val = p.absMin if p.absValSupported else p.min
            max_val = p.absMax if p.absValSupported else p.max

            # set the adjustment corresponding to the thingus
            if k == PyCapture2.PROPERTY_TYPE.WHITE_BALANCE:
                a = (Gtk.Adjustment.new(min_val, min_val, max_val, 1, 0, 0),
                     Gtk.Adjustment.new(min_val, min_val, max_val, 1, 0, 0))

                a[0].connect('value_changed', self.update_item_cb, k)
                a[1].connect('value_changed', self.update_item_cb, k)
            else:
                a = Gtk.Adjustment.new(min_val, min_val, max_val, 1, 0, 0)
                a.connect('value_changed', self.update_item_cb, k)

            self.value_table[k] = a

            # slider-scale
            if k == PyCapture2.PROPERTY_TYPE.WHITE_BALANCE:
                box = Gtk.VBox.new(True, 5)

                b = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, a[0])
                box.pack_start(b, True, True, 0)
                b.set_draw_value(False)
                b.set_hexpand(True)

                b = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, a[1])
                box.pack_start(b, True, True, 0)
                b.set_draw_value(False)
                b.set_hexpand(True)

                b = box
            else:
                b = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, a)
                b.set_draw_value(False)
                b.set_hexpand(True)

            grid.attach(b, 1, i, 1, 1)

            # spinner for finer-grained control
            if k == PyCapture2.PROPERTY_TYPE.WHITE_BALANCE:
                box = Gtk.VBox.new(True, 5)

                b = Gtk.SpinButton.new(a[0], 1, 1)
                box.pack_start(b, True, True, 0)

                b = Gtk.SpinButton.new(a[1], 1, 1)
                box.pack_start(b, True, True, 0)

                b = box
            else:
                b = Gtk.SpinButton.new(a, 1, 3 if p.absValSupported else 1)

            grid.attach(b, 2, i, 1, 1)

            # units label
            b = Gtk.Label(p.unitAbbr.decode('ascii'))
            b.set_xalign(0)
            grid.attach(b, 3, i, 1, 1)

            # auto-manual button
            b = Gtk.CheckButton()
            b.set_halign(Gtk.Align.CENTER)
            b.connect('toggled', self.update_item_cb, k)
            self.auto_table[k] = b
            grid.attach(b, 4, i, 1, 1)

            # on-off button
            b = Gtk.CheckButton()
            b.set_halign(Gtk.Align.CENTER)
            b.connect('toggled', self.update_item_cb, k)
            self.onoff_table[k] = b
            grid.attach(b, 5, i, 1, 1)

            i = i + 1

        grid.show_all()
        self.refresh()

        self.refresh_timeout = GLib.timeout_add(500, self.refresh_queue_cb)



        # sg = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        #
        # for p in self.properties:
        #     name = self.property_types[p.type].replace('_', ' ').title()
        #     value = p.type
        #
        #     min_val = p.absMin if p.absValSupported else p.min
        #     max_val = p.absMax if p.absValSupported else p.max
        #
        #     print(name, min_val, max_val, p.autoSupported, p.manualSupported)
        #
        #     widget = self.align_label(sg, name)
        #     b = Gtk.HScale.new_with_range(min_val, max_val, 1)
        #     b.set_draw_value(False)
        #     widget.pack_start(b, True, True, 10)
        #     b.show()
        #
        #     b = Gtk.CheckButton()
        #     widget.pack_start(b, False, False, 10)
        #     b.show()
        #
        #     b = Gtk.CheckButton()
        #     widget.pack_start(b, False, False, 10)
        #     b.show()
        #
        #     vbox.pack_start(widget, True, True, 10)
