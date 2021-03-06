#!/usr/bin/python

"""A widget for displaying infomation.
Info -- display messages and errors
Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import logging

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

# how long to keep the bar visible, in milliseconds
info_timeout = 5000

class Info(Gtk.InfoBar):

    """Display messages and errors.
    The widget hides itself after a short delay and is less obtrusive than a
    popup dialog box.

    Messages come in two parts: a high-level summary, and a detailed
    description.
    """

    def hide_cb(self, widget, response_id, client):
        self.hide()

    def __init__(self):
        Gtk.InfoBar.__init__(self)

        self.hide_timeout = 0

        content = self.get_content_area()

        self.label = Gtk.Label()
        content.pack_start(self.label, False, False, 0)
        self.label.show()

        self.add_button('Close', 0)
        self.connect('response', self.hide_cb, None)

    def timeout_cb(self):
        self.hide_timeout = 0
        self.hide()
        return False

    def pop(self):
        self.show()
        if self.hide_timeout:
            GLib.source_remove(self.hide_timeout)
            self.hide_timeout = 0
        self.hide_timeout = GLib.timeout_add(info_timeout, self.timeout_cb)

    def set_msg(self, main, sub):
        self.label.set_markup('<b>%s</b>\n%s' % (main, sub))

    def msg(self, main, sub):
        """Display an informational message.
        main -- a summary of the message
        sub -- message details
        """
        self.set_msg(main, sub)
        logging.debug('info: %s, %s', main, sub)
        self.set_message_type(Gtk.MessageType.INFO)
        self.pop()

    def err(self, main, sub):
        """Display an error message.
        main -- a summary of the error
        sub -- error details
        """
        self.set_msg(main, sub)
        logging.error('error: %s, %s', main, sub)
        self.set_message_type(Gtk.MESSAGE_ERROR)
        self.pop()
