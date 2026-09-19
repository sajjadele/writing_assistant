/**
 * Virtual keyboard controller using Clutter input devices (ADR-07).
 * Emits Shift + Insert to replace selected text in the active application window.
 */

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';

export class VirtualKeyboard {
    constructor() {
        this._virtualDevice = null;
    }

    _getVirtualDevice() {
        if (!this._virtualDevice) {
            const seat = Clutter.get_default_backend().get_default_seat();
            if (seat && typeof seat.create_virtual_device === 'function') {
                this._virtualDevice = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
            }
        }
        return this._virtualDevice;
    }

    /**
     * Emit simulated Shift + Insert keystroke.
     */
    emitPaste() {
        const device = this._getVirtualDevice();
        if (!device) {
            console.error('[WritingAssistant] Virtual keyboard device unavailable on current seat.');
            return;
        }

        const now = Clutter.get_current_event_time();

        // Press Shift_L
        device.notify_keyval(now, Clutter.KEY_Shift_L, Clutter.KeyState.PRESS);

        // Small micro-delay for event loop dispatch
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 15, () => {
            const t1 = Clutter.get_current_event_time();
            // Press Insert
            device.notify_keyval(t1, Clutter.KEY_Insert, Clutter.KeyState.PRESS);
            // Release Insert
            device.notify_keyval(t1, Clutter.KEY_Insert, Clutter.KeyState.RELEASE);

            // Release Shift_L
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 15, () => {
                const t2 = Clutter.get_current_event_time();
                device.notify_keyval(t2, Clutter.KEY_Shift_L, Clutter.KeyState.RELEASE);
                return GLib.SOURCE_REMOVE;
            });

            return GLib.SOURCE_REMOVE;
        });
    }
}
