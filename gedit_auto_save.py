import os
from datetime import datetime
import subprocess
from gi.repository import GObject, Gedit, Gio, Gtk, PeasGtk

__all__ = ["SASViewActivatable", "SASWindowActivatable", "SASPreferences"]

SCHEMA_ID = "org.gnome.gedit.plugins.sasplugin"
DEFAULT_TMP_FOLDER = "~/Documents/.gedit/"


class SASPreferences(GObject.Object, PeasGtk.Configurable):
    __gtype_name__ = "SASPreferences"
    object = GObject.property(type=GObject.Object)

    def do_create_configure_widget(self):
        """Create preferences dialog for setting temporary folder path."""
        vbox = Gtk.VBox(spacing=6)

        label = Gtk.Label(label="Temporary Files Folder:")
        vbox.pack_start(label, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.set_text(_get_tmp_folder())
        vbox.pack_start(self.entry, False, False, 0)

        save_button = Gtk.Button(label="Save")
        save_button.connect("clicked", self._on_save_clicked)
        vbox.pack_start(save_button, False, False, 0)

        return vbox

    def _on_save_clicked(self, button):
        """Save the temporary folder path to settings."""
        settings = _get_settings(SCHEMA_ID)
        settings.set_string("tmp-folder", self.entry.get_text())


class SASViewActivatable(GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "SASViewActivatable"
    view = GObject.property(type=Gedit.View)

    def __init__(self):
        """Initialize the view activatable."""
        GObject.Object.__init__(self)
        self.timeout_id = None

    def do_activate(self):
        """Activate the plugin and connect document changed signal."""
        self.document_changed_handler_id = self.document.connect(
            "changed", self.document_changed
        )

    def do_deactivate(self):
        """Deactivate the plugin and disconnect document changed signal."""
        self.document.disconnect(self.document_changed_handler_id)

    def document_changed(self, _document):
        """Handle document change event and schedule saving."""
        if self.timeout_id is not None:
            GObject.source_remove(self.timeout_id)

        self.timeout_id = GObject.timeout_add(
            500, self.maybe_save, priority=GObject.PRIORITY_LOW
        )

    def maybe_save(self):
        """Save the document if conditions are met."""
        maybe_save(self.window)
        self.timeout_id = None

    @property
    def document(self):
        """Return the current document."""
        return self.view.get_buffer()

    @property
    def window(self):
        """Return the top-level window."""
        return self.view.get_toplevel()


class SASWindowActivatable(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "SASWindowActivatable"
    window = GObject.Property(type=Gedit.Window)

    def __init__(self):
        """Initialize the window activatable."""
        GObject.Object.__init__(self)
        self.is_closing = False

    def do_activate(self):
        """Activate the plugin and connect window signals."""
        self.window.smart_autosave_plugin_handler_ids = [
            self.window.connect("active-tab-changed", self.active_tab_changed),
            self.window.connect("focus-out-event", self.focus_out),
            self.window.connect("tab-removed", self.tab_removed),
            self.window.connect("delete-event", self.on_window_delete_event),
            self.window.connect("show", self.on_window_show),
        ]

    def do_deactivate(self):
        """Deactivate the plugin and disconnect window signals."""
        for handler_id in self.window.smart_autosave_plugin_handler_ids:
            self.window.disconnect(handler_id)

    def active_tab_changed(self, window, _new_tab):
        """Handle active tab change event."""
        maybe_save(window)

    def focus_out(self, window, _event):
        """Handle focus out event."""
        maybe_save(window)

    def tab_removed(self, window, tab):
        """Handle tab removed event and prompt to save unsaved documents."""
        if not self.is_closing:
            document = tab.get_document()
            file = document.get_file()
            if (
                file
                and file.get_location()
                and ".gedit" in file.get_location().get_path()
            ):
                dialog = Gtk.MessageDialog(
                    transient_for=self.window,
                    flags=0,
                    message_type=Gtk.MessageType.QUESTION,
                    buttons=Gtk.ButtonsType.NONE,
                    text="Salvar documento?",
                )
                dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
                dialog.add_button(Gtk.STOCK_NO, Gtk.ResponseType.NO)
                dialog.add_button(Gtk.STOCK_YES, Gtk.ResponseType.YES)
                dialog.format_secondary_text(
                    "Você deseja salvar as alterações feitas no documento?"
                )
                response = dialog.run()
                if response == Gtk.ResponseType.YES:
                    document.save(Gedit.SAVE_FLAG_NONE)
                elif response == Gtk.ResponseType.NO:
                    try:
                        file_path = file.get_location().get_path()
                        subprocess.run(["gio", "trash", file_path])
                    except Exception as e:
                        print(f"Erro ao mover o arquivo para a lixeira: {e}")
                else:
                    Gedit.commands_load_locations(
                        window, [file.get_location()], None, 0, 0
                    )

                dialog.destroy()

    def on_window_delete_event(self, window, event):
        """Handle window delete event."""
        self.is_closing = True

    def on_window_show(self, window, data=None):
        """Restore tabs if this window is the first Gedit window instance."""
        if self._is_first_window():
            self.restore_tabs(window)

    def _is_first_window(self):
        """Return True if the window being added is the first window instance."""
        app = Gedit.App.get_default()
        return len(app.get_windows()) <= 1

    def restore_tabs(self, window):
        """Restore tabs from the temporary folder."""
        folder_path = os.path.expanduser(_get_tmp_folder())
        if os.path.isdir(folder_path):
            locations = []
            for filename in os.listdir(folder_path):
                if filename.endswith(".txt") or filename.endswith(".md"):
                    uri = os.path.join(folder_path, filename)
                    location = Gio.file_new_for_uri(f"file://{uri}")
                    if location.query_exists():
                        locations.append(location)

            if locations:
                locations.sort()
                Gedit.commands_load_locations(window, locations, None, 0, 0)
                documents = window.get_documents()
                if documents:
                    window.set_active_tab(Gedit.Tab.get_from_document(documents[0]))


def maybe_save(window):
    """Save unsaved documents in the window."""
    for document in window.get_unsaved_documents():
        file = document.get_file()
        if file.is_readonly():
            continue
        if file.is_externally_modified():
            continue
        if not file.get_location():
            save_path = os.path.expanduser(_get_tmp_folder())
            os.makedirs(save_path, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_file_name = f"{timestamp}.txt"
            temp_file_path = os.path.join(save_path, temp_file_name)
            file.set_location(Gio.File.new_for_path(temp_file_path))
        if not file.is_local():
            continue
        if not document.get_modified():
            continue
        Gedit.commands_save_document_async(document, window)


def _get_tmp_folder():
    """Get the current temporary folder path from settings."""
    settings = _get_settings(SCHEMA_ID)
    tmp_folder = settings.get_string("tmp-folder") if settings else DEFAULT_TMP_FOLDER
    return tmp_folder


def _get_settings(schema):
    if not _is_schema_installed():
        print("Settings schema is not installed")
        return None
    try:
        return Gio.Settings.new(schema)
    except Exception as e:
        print(e)


def _is_schema_installed():
    """Check if the GSettings schema is installed."""
    return SCHEMA_ID in Gio.Settings.list_schemas()
