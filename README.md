
# Gedit Smart Autosave and Session Restore Plugin
This Gedit plugin enhances your editing experience by introducing smart autosave and session restore features.

## Key Features:

- **Smart Autosave:** Automatically saves documents in a designated temporary folder to prevent data loss.
- **Session Restore:** Reopens all .txt and .md files from the temporary folder when Gedit is launched, ensuring you can easily continue your work from where you left off.
- **Unsaved Document Management:** Prompts you to save or discard changes to unsaved documents when closing tabs or the editor, with an option to move discarded documents to trash.
- **Background Saving:** Utilizes GObject's timeout mechanism to periodically save unsaved changes, minimizing interruptions to your workflow.
With these functionalities, this plugin aims to provide a seamless and worry-free text editing experience.


## Install schema settings:
```bash
sudo cp org.gnome.gedit.plugins.sasplugin.gschema.xml /usr/share/glib-2.0/schemas/
sudo glib-compile-schemas /usr/share/glib-2.0/schemas/
```

## References
- https://theawless.github.io/How-to-write-plugins-for-gedit/
- https://github.com/seanh/gedit-smart-autosave/blob/master/smart_autosave/plugin.py
- https://github.com/kgshank/gse-sound-output-device-chooser
- https://github.com/GNOME/pygobject
- https://docs.gtk.org/gtk3/enum.ButtonsType.html
- https://python-gtk-3-tutorial.readthedocs.io/en/latest/dialogs.html
- https://github.com/jefferyto/gedit-ex-mortis
- https://github.com/raelgc/gedit-restore-tabs
- https://gedit-technology.github.io/apps/gedit/
- https://github.com/bndn/gedit-plugins
- https://valadoc.org/gedit/Gedit.Window.html