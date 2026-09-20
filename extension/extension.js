import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import Shell from 'gi://Shell';
import Meta from 'gi://Meta';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {InPlacePopup} from './popup.js';
import {VirtualKeyboard} from './keyboard.js';

export default class WritingAssistantExtension extends Extension {
    enable() {
        this._popup = new InPlacePopup();
        this._keyboard = new VirtualKeyboard();
        this._settings = this.getSettings();

        // 1. Register global shortcut
        Main.wm.addKeybinding(
            'toggle-assistant',
            this._settings,
            Meta.KeyBindingFlags.NONE,
            Shell.ActionMode.ALL,
            () => this._triggerAssistant()
        );

        // 2. Add Top Panel Indicator (Tray Menu)
        this._indicator = new PanelMenu.Button(0.0, 'WritingAssistantIndicator', false);
        const icon = new St.Icon({
            icon_name: 'accessories-dictionary-symbolic',
            style_class: 'system-status-icon',
        });
        this._indicator.add_child(icon);

        const titleItem = new PopupMenu.PopupMenuItem('✨ Writing Assistant', { reactive: false });
        this._indicator.menu.addMenuItem(titleItem);

        this._indicator.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const dashboardItem = new PopupMenu.PopupMenuItem('⚙️  Open Dashboard & Settings');
        dashboardItem.connect('activate', () => {
            this._launchDashboard();
        });
        this._indicator.menu.addMenuItem(dashboardItem);

        const shortcutItem = new PopupMenu.PopupMenuItem('⌨️  Shortcut: Ctrl + Alt + G', { reactive: false });
        this._indicator.menu.addMenuItem(shortcutItem);

        Main.panel.addToStatusArea('writing-assistant-indicator', this._indicator);

        console.log('[WritingAssistant] Extension enabled with top panel indicator.');
    }

    disable() {
        Main.wm.removeKeybinding('toggle-assistant');

        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }

        if (this._popup) {
            this._popup.close();
            this._popup = null;
        }

        this._keyboard = null;
        this._settings = null;

        console.log('[WritingAssistant] Extension disabled cleanly.');
    }

    _launchDashboard() {
        const pythonPath = this._getPythonExecutable();
        try {
            Gio.Subprocess.new(
                [pythonPath, '-m', 'writing_companion.cli', '--dashboard'],
                Gio.SubprocessFlags.NONE
            );
        } catch (e) {
            console.error('[WritingAssistant] Failed to launch dashboard:', e);
        }
    }

    _triggerAssistant() {
        const clipboard = St.Clipboard.get_default();
        clipboard.get_text(St.ClipboardType.PRIMARY, (clip, text) => {
            if (!text || !text.trim()) {
                this._popup.showToast('Please select text first');
                return;
            }

            const selectedText = text.trim();
            this._popup.showLoading();

            this._runPythonIPC(
                {
                    action: 'correct',
                    text: selectedText,
                },
                (err, res) => {
                    if (err) {
                        this._popup.showError(err.message || 'Execution error');
                        return;
                    }

                    if (res.status === 'error') {
                        this._popup.showError(res.error?.message || 'Error processing text');
                        return;
                    }

                    const eventId = res.metadata?.event_id;
                    const data = res.data;

                    this._popup.showResult(
                        data,
                        () => {
                            // User pressed Enter (Accept)
                            if (!data.is_correct) {
                                clipboard.set_text(St.ClipboardType.CLIPBOARD, data.corrected_text);
                                clipboard.set_text(St.ClipboardType.PRIMARY, data.corrected_text);
                                this._keyboard.emitPaste();
                            }
                            if (eventId) {
                                this._runPythonIPC({
                                    action: 'log_feedback',
                                    event_id: eventId,
                                    accepted: true,
                                });
                            }
                        },
                        () => {
                            // User pressed Esc or clicked outside (Dismiss)
                            if (eventId) {
                                this._runPythonIPC({
                                    action: 'log_feedback',
                                    event_id: eventId,
                                    accepted: false,
                                });
                            }
                        }
                    );
                }
            );
        });
    }

    _getPythonExecutable() {
        // Look for project virtual environment python first, then system python3
        const projectDir = this.path;
        // extension is inside project/extension
        const venvPython = GLib.build_filenamev([projectDir, '..', '.venv', 'bin', 'python']);
        if (GLib.file_test(venvPython, GLib.FileTest.IS_EXECUTABLE)) {
            return venvPython;
        }
        return 'python3';
    }

    _runPythonIPC(payload, callback) {
        try {
            const pythonPath = this._getPythonExecutable();
            const proc = Gio.Subprocess.new(
                [pythonPath, '-m', 'writing_companion.cli', '--ipc'],
                Gio.SubprocessFlags.STDIN_PIPE |
                Gio.SubprocessFlags.STDOUT_PIPE |
                Gio.SubprocessFlags.STDERR_PIPE
            );

            const jsonInput = JSON.stringify(payload);
            let isTimedOut = false;

            // 4500ms watchdog timer (T033)
            const timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 4500, () => {
                isTimedOut = true;
                try {
                    proc.force_exit();
                } catch (e) {}
                if (callback) callback(new Error('Process timed out after 4500ms.'));
                return GLib.SOURCE_REMOVE;
            });

            proc.communicate_utf8_async(jsonInput, null, (subprocess, result) => {
                if (isTimedOut) return;
                GLib.source_remove(timeoutId);

                try {
                    const [, stdout, stderr] = subprocess.communicate_utf8_finish(result);
                    if (!subprocess.get_successful()) {
                        if (callback) callback(new Error(`Exit error: ${stderr || 'Unknown'}`));
                        return;
                    }

                    const parsed = JSON.parse(stdout.trim());
                    if (callback) callback(null, parsed);
                } catch (e) {
                    if (callback) callback(e);
                }
            });
        } catch (err) {
            if (callback) callback(err);
        }
    }
}
