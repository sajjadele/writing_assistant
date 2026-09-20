/**
 * In-place floating popup actor inside GNOME Shell compositor (Mutter/Clutter).
 * Completely immune to Pop-Shell tiling and anchored to global.get_pointer().
 */

import Clutter from 'gi://Clutter';
import St from 'gi://St';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export class InPlacePopup {
    constructor() {
        this._actor = null;
        this._keyEventId = 0;
        this._onAccept = null;
        this._onDismiss = null;
        this._capturedEventId = 0;
    }

    /**
     * Show a transient notification toast for empty selection (T016).
     */
    showToast(message) {
        this.close();

        const [x, y] = global.get_pointer();
        const toast = new St.Label({
            style_class: 'writing-companion-toast',
            text: `⚠️  ${message}`,
        });

        Main.uiGroup.add_child(toast);
        toast.set_position(x + 10, y + 15);

        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1800, () => {
            if (toast && toast.get_parent()) {
                Main.uiGroup.remove_child(toast);
                toast.destroy();
            }
            return GLib.SOURCE_REMOVE;
        });
    }

    /**
     * Smart adaptive positioning anchored to cursor or active input box.
     */
    _updatePosition() {
        if (!this._actor) return;

        let [x, y] = global.get_pointer();
        const focusWindow = global.display.focus_window;

        if (focusWindow) {
            const rect = focusWindow.get_frame_rect();
            // If pointer was left on a different window or top bar, anchor near active window
            const isOutside = (
                x < rect.x || x > rect.x + rect.width ||
                y < rect.y || y > rect.y + rect.height
            );
            if (isOutside) {
                x = Math.round(rect.x + rect.width * 0.35);
                y = Math.round(rect.y + rect.height - 100);
            }
        }

        const monitor = Main.layoutManager.currentMonitor || Main.layoutManager.primaryMonitor;
        const [actorW, actorH] = this._actor.get_transformed_size();
        const width = actorW > 50 ? actorW : 420;
        const height = actorH > 30 ? actorH : 200;

        // Horizontal positioning: default to x + 15, flip left if overflowing
        let posX = x + 15;
        if (posX + width > monitor.x + monitor.width - 20) {
            posX = x - width - 15;
        }
        posX = Math.max(monitor.x + 20, Math.min(posX, monitor.x + monitor.width - width - 20));

        // Vertical positioning:
        // If cursor is in the lower 55% of the screen, open ABOVE the cursor
        let posY;
        const isLowerHalf = y > (monitor.y + monitor.height * 0.55);
        if (isLowerHalf) {
            posY = y - height - 15;
        } else {
            posY = y + 15;
        }

        // Clamp vertically inside monitor bounds (leaving space for top bar)
        posY = Math.max(monitor.y + 40, Math.min(posY, monitor.y + monitor.height - height - 20));

        this._actor.set_position(posX, posY);
        console.log(`[WritingAssistant] Popup positioned at (${posX}, ${posY}) for target (${x}, ${y}), size=(${width}, ${height}), isLowerHalf=${isLowerHalf}`);
    }

    /**
     * Open popup in loading state anchored to cursor (T015).
     */
    showLoading(onDismiss) {
        this.close();
        this._onDismiss = onDismiss;

        this._actor = new St.BoxLayout({
            vertical: true,
            style_class: 'writing-companion-popup',
            reactive: true,
            can_focus: true,
        });

        // Header
        const header = new St.BoxLayout({
            style_class: 'writing-companion-header',
        });
        const title = new St.Label({
            style_class: 'writing-companion-title',
            text: '✨ Writing Companion',
        });
        header.add_child(title);
        this._actor.add_child(header);

        // Loading message
        this._contentBox = new St.BoxLayout({
            vertical: true,
            style_class: 'writing-companion-loading',
        });
        const spinner = new St.Label({
            text: '⏳ Analyzing expression & semantic intent...',
        });
        this._contentBox.add_child(spinner);
        this._actor.add_child(this._contentBox);

        // Add to Mutter compositor scene graph
        Main.uiGroup.add_child(this._actor);

        // Set initial position
        this._updatePosition();

        // Grab keyboard focus for Enter/Esc
        this._setupEvents();
    }

    /**
     * Render the single-inference response (T020, T025, T026).
     */
    showResult(data, onAccept, onDismiss) {
        if (!this._actor) return;

        this._onAccept = onAccept;
        this._onDismiss = onDismiss;

        this._contentBox.destroy_all_children();

        if (data.is_correct) {
            // No Change Needed confirmation
            const correctBox = new St.BoxLayout({
                style_class: 'writing-companion-no-change-box',
                vertical: true,
            });
            const checkLabel = new St.Label({
                text: '✓  No Change Needed — Expression is clear & correct!',
            });
            correctBox.add_child(checkLabel);
            this._contentBox.add_child(correctBox);
        } else {
            // 1. Persian Semantic Checkpoint (Anti-Drift)
            if (data.interpreted_meaning_fa) {
                const persianBox = new St.BoxLayout({
                    vertical: true,
                    style_class: 'writing-companion-persian-box',
                });
                const meaningLabel = new St.Label({
                    style_class: 'writing-companion-persian-text',
                    text: `💡 منظور: ${data.interpreted_meaning_fa}`,
                });
                persianBox.add_child(meaningLabel);
                this._contentBox.add_child(persianBox);
            }

            // 2. English Suggestion in ScrollView for long texts (T032)
            const scrollView = new St.ScrollView({
                style: 'max-height: 220px;',
                hscrollbar_policy: St.PolicyType.NEVER,
                vscrollbar_policy: St.PolicyType.AUTOMATIC,
            });
            const suggestionBox = new St.BoxLayout({
                vertical: true,
                style_class: 'writing-companion-suggestion-box',
            });
            const suggestionLabel = new St.Label({
                style_class: 'writing-companion-suggestion-text',
                text: data.corrected_text,
            });
            suggestionBox.add_child(suggestionLabel);
            scrollView.set_child(suggestionBox);
            this._contentBox.add_child(scrollView);
        }

        // Footer with keyboard tips
        const footer = new St.BoxLayout({
            style_class: 'writing-companion-footer',
        });
        const enterKey = new St.Label({
            style_class: 'writing-companion-key',
            text: 'Enter',
        });
        const replaceLabel = new St.Label({
            text: ' Replace   ',
        });
        const escKey = new St.Label({
            style_class: 'writing-companion-key',
            text: 'Esc',
        });
        const dismissLabel = new St.Label({
            text: ' Dismiss',
        });

        footer.add_child(enterKey);
        footer.add_child(replaceLabel);
        footer.add_child(escKey);
        footer.add_child(dismissLabel);
        this._contentBox.add_child(footer);

        // Re-calculate position dynamically once content layout is allocated
        GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._updatePosition();
            return GLib.SOURCE_REMOVE;
        });
    }

    /**
     * Show error state.
     */
    showError(errorMsg) {
        if (!this._actor) return;
        this._contentBox.destroy_all_children();

        const errBox = new St.BoxLayout({
            vertical: true,
            style_class: 'writing-companion-persian-box',
        });
        const errLabel = new St.Label({
            text: `❌ ${errorMsg}`,
        });
        errBox.add_child(errLabel);
        this._contentBox.add_child(errBox);

        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2500, () => {
            this.close();
            return GLib.SOURCE_REMOVE;
        });
    }

    _setupEvents() {
        this._actor.grab_key_focus();

        this._keyEventId = this._actor.connect('key-press-event', (actor, event) => {
            const symbol = event.get_key_symbol();
            if (symbol === Clutter.KEY_Escape) {
                if (this._onDismiss) this._onDismiss();
                this.close();
                return Clutter.EVENT_STOP;
            }

            if (symbol === Clutter.KEY_Return || symbol === Clutter.KEY_KP_Enter) {
                if (this._onAccept) this._onAccept();
                this.close();
                return Clutter.EVENT_STOP;
            }

            return Clutter.EVENT_PROPAGATE;
        });

        // Dismiss on outside pointer click
        this._capturedEventId = global.stage.connect('captured-event', (stage, event) => {
            if (event.type() === Clutter.EventType.BUTTON_PRESS) {
                const [targetX, targetY] = event.get_coords();
                const [actorX, actorY] = this._actor.get_transformed_position();
                const [actorW, actorH] = this._actor.get_transformed_size();

                if (
                    targetX < actorX ||
                    targetX > actorX + actorW ||
                    targetY < actorY ||
                    targetY > actorY + actorH
                ) {
                    if (this._onDismiss) this._onDismiss();
                    this.close();
                }
            }
            return Clutter.EVENT_PROPAGATE;
        });
    }

    /**
     * Cleanly remove actor from compositor scene graph.
     */
    close() {
        if (this._capturedEventId) {
            global.stage.disconnect(this._capturedEventId);
            this._capturedEventId = 0;
        }

        if (this._keyEventId && this._actor) {
            this._actor.disconnect(this._keyEventId);
            this._keyEventId = 0;
        }

        if (this._actor) {
            if (this._actor.get_parent()) {
                Main.uiGroup.remove_child(this._actor);
            }
            this._actor.destroy();
            this._actor = null;
        }

        this._onAccept = null;
        this._onDismiss = null;
    }
}
