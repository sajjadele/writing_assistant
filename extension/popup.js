/**
 * In-place floating popup actor inside GNOME Shell compositor (Mutter/Clutter).
 * Completely immune to Pop-Shell tiling and anchored to global.get_pointer().
 */

import Clutter from 'gi://Clutter';
import St from 'gi://St';
import Pango from 'gi://Pango';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export class InPlacePopup {
    constructor() {
        this._actor = null;
        this._keyEventId = 0;
        this._onAccept = null;
        this._onDismiss = null;
        this._onDashboard = null;
        this._capturedEventId = 0;
        this._grab = null;
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
        const width = actorW > 50 ? actorW : 520;
        const height = actorH > 30 ? actorH : 240;

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
    showLoading(onDismiss, onDashboard) {
        this.close();
        this._onDismiss = onDismiss;
        this._onDashboard = onDashboard;

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
            text: '✨ WRITING ASSISTANT',
        });
        header.add_child(title);

        this._badge = new St.Label({
            style_class: 'writing-companion-badge',
            text: '⚡ Analyzing...',
        });
        this._badge.set_x_align(Clutter.ActorAlign.END);
        this._badge.set_x_expand(true);
        header.add_child(this._badge);

        this._actor.add_child(header);

        // Loading message
        this._contentBox = new St.BoxLayout({
            vertical: true,
            style_class: 'writing-companion-loading',
        });
        const spinner = new St.Label({
            text: 'در حال درک نیت و نگارش طبیعی...',
        });
        this._contentBox.add_child(spinner);
        this._actor.add_child(this._contentBox);

        // Add to Mutter compositor scene graph
        Main.uiGroup.add_child(this._actor);

        // Set initial position
        this._updatePosition();

        // Take modal grab so Enter/Esc/D and outside clicks reach the popup
        this._setupEvents();
    }

    /**
     * Render the single-inference response (T020, T025, T026).
     */
    showResult(data, onAccept, onDismiss, onDashboard, backendName = 'AI', durationMs = 0) {
        if (!this._actor) return;

        this._onAccept = onAccept;
        this._onDismiss = onDismiss;
        this._onDashboard = onDashboard;

        if (this._badge) {
            const timeStr = durationMs > 0 ? ` • ${durationMs}ms` : '';
            this._badge.set_text(`${backendName.toUpperCase()}${timeStr}`);
        }

        this._contentBox.destroy_all_children();

        if (data.is_correct) {
            // No Change Needed confirmation
            const correctBox = new St.BoxLayout({
                style_class: 'writing-companion-no-change-box',
                vertical: true,
            });
            const checkTitle = new St.Label({
                style_class: 'writing-companion-no-change-title',
                text: '✓  No Change Needed',
            });
            const checkDesc = new St.Label({
                style_class: 'writing-companion-no-change-desc',
                text: 'جمله شما از نظر گرامری و بیان فنی کاملاً درست و رسا است.',
            });
            checkDesc.clutter_text.line_wrap = true;
            checkDesc.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
            checkDesc.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
            correctBox.add_child(checkTitle);
            correctBox.add_child(checkDesc);
            this._contentBox.add_child(correctBox);
        } else {
            // 1. Persian Semantic Checkpoint (Anti-Drift) with ScrollView
            if (data.interpreted_meaning_fa) {
                const persianBox = new St.BoxLayout({
                    vertical: true,
                    style_class: 'writing-companion-persian-box',
                });
                const meaningTitle = new St.Label({
                    style_class: 'writing-companion-persian-title',
                    text: '💡 منظور شما (Semantic Checkpoint):',
                });
                persianBox.add_child(meaningTitle);

                const persianScrollView = new St.ScrollView({
                    style_class: 'writing-companion-scroll-view',
                    style: 'max-height: 105px;',
                    hscrollbar_policy: St.PolicyType.NEVER,
                    vscrollbar_policy: St.PolicyType.AUTOMATIC,
                    overlay_scrollbars: true,
                    x_expand: true,
                });

                const meaningContent = new St.BoxLayout({
                    vertical: true,
                    x_expand: true,
                });

                const meaningLabel = new St.Label({
                    style_class: 'writing-companion-persian-text',
                    text: data.interpreted_meaning_fa,
                    x_expand: true,
                });
                meaningLabel.clutter_text.line_wrap = true;
                meaningLabel.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
                meaningLabel.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;

                meaningContent.add_child(meaningLabel);
                persianScrollView.set_child(meaningContent);
                persianBox.add_child(persianScrollView);
                this._contentBox.add_child(persianBox);
            }

            // 2. English Suggested Expression with ScrollView
            const suggestionBox = new St.BoxLayout({
                vertical: true,
                style_class: 'writing-companion-suggestion-box',
            });
            const suggestionTitle = new St.Label({
                style_class: 'writing-companion-suggestion-title',
                text: 'Suggested Expression (طبیعی و روان):',
            });
            suggestionBox.add_child(suggestionTitle);

            const suggestionScrollView = new St.ScrollView({
                style_class: 'writing-companion-scroll-view',
                style: 'max-height: 130px;',
                hscrollbar_policy: St.PolicyType.NEVER,
                vscrollbar_policy: St.PolicyType.AUTOMATIC,
                overlay_scrollbars: true,
                x_expand: true,
            });

            const suggestionContent = new St.BoxLayout({
                vertical: true,
                x_expand: true,
            });

            const suggestionLabel = new St.Label({
                style_class: 'writing-companion-suggestion-text',
                text: data.corrected_text,
                x_expand: true,
            });
            suggestionLabel.clutter_text.line_wrap = true;
            suggestionLabel.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
            suggestionLabel.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;

            suggestionContent.add_child(suggestionLabel);
            suggestionScrollView.set_child(suggestionContent);
            suggestionBox.add_child(suggestionScrollView);

            // 3. Diff Pills (Key modifications)
            if (data.changes && data.changes.length > 0) {
                const diffContainer = new St.BoxLayout({
                    style_class: 'writing-companion-diff-container',
                });
                for (const ch of data.changes.slice(0, 3)) {
                    const pill = new St.BoxLayout({
                        style_class: 'writing-companion-diff-pill',
                    });
                    pill.add_child(new St.Label({
                        style_class: 'writing-companion-diff-orig',
                        text: ch.original,
                    }));
                    pill.add_child(new St.Label({
                        style_class: 'writing-companion-diff-arrow',
                        text: '➔',
                    }));
                    pill.add_child(new St.Label({
                        style_class: 'writing-companion-diff-repl',
                        text: ch.replacement,
                    }));
                    diffContainer.add_child(pill);
                }
                suggestionBox.add_child(diffContainer);
            }

            this._contentBox.add_child(suggestionBox);
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
            text: ' جایگزینی   ',
        });

        const dKey = new St.Label({
            style_class: 'writing-companion-key',
            text: 'D',
        });
        const dashLabel = new St.Label({
            text: ' ⚙️ داشبورد   ',
        });
        const dashBox = new St.BoxLayout({
            style_class: 'writing-companion-btn',
            reactive: true,
            can_focus: true,
        });
        dashBox.add_child(dKey);
        dashBox.add_child(dashLabel);
        dashBox.connect('button-press-event', () => {
            const onDash = this._onDashboard;
            this.close();
            if (onDash) onDash();
            return Clutter.EVENT_STOP;
        });

        const escKey = new St.Label({
            style_class: 'writing-companion-key',
            text: 'Esc',
        });
        const dismissLabel = new St.Label({
            text: ' انصراف',
        });

        footer.add_child(enterKey);
        footer.add_child(replaceLabel);
        footer.add_child(dashBox);
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
            x_expand: true,
        });
        errLabel.clutter_text.line_wrap = true;
        errLabel.clutter_text.line_wrap_mode = Pango.WrapMode.WORD_CHAR;
        errLabel.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        errBox.add_child(errLabel);
        this._contentBox.add_child(errBox);

        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2500, () => {
            this.close();
            return GLib.SOURCE_REMOVE;
        });
    }

    _setupEvents() {
        // On Wayland a plain grab_key_focus() cannot pull the keyboard away
        // from the focused application window; a modal grab is required so
        // Enter/Esc/D are routed to the shell at all.
        this._grab = Main.pushModal(this._actor);

        this._keyEventId = this._actor.connect('key-press-event', (actor, event) => {
            const symbol = event.get_key_symbol();
            if (symbol === Clutter.KEY_Escape) {
                if (this._onDismiss) this._onDismiss();
                this.close();
                return Clutter.EVENT_STOP;
            }

            if (symbol === Clutter.KEY_Return || symbol === Clutter.KEY_KP_Enter) {
                const onAccept = this._onAccept;
                this.close();
                if (onAccept) {
                    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 80, () => {
                        onAccept();
                        return GLib.SOURCE_REMOVE;
                    });
                }
                return Clutter.EVENT_STOP;
            }

            if (symbol === Clutter.KEY_d || symbol === Clutter.KEY_D) {
                const onDash = this._onDashboard;
                this.close();
                if (onDash) onDash();
                return Clutter.EVENT_STOP;
            }

            return Clutter.EVENT_PROPAGATE;
        });

        // Dismiss on pointer press outside the popup. During the grab every
        // event is delivered to the grab actor, so listen on the actor and
        // check the real target (same pattern as Shell's PopupMenuManager).
        this._capturedEventId = this._actor.connect('captured-event', (actor, event) => {
            const type = event.type();
            if (type !== Clutter.EventType.BUTTON_PRESS && type !== Clutter.EventType.TOUCH_BEGIN)
                return Clutter.EVENT_PROPAGATE;

            const targetActor = global.stage.get_event_actor(event);
            if (targetActor && this._actor.contains(targetActor))
                return Clutter.EVENT_PROPAGATE;

            if (this._onDismiss) this._onDismiss();
            this.close();
            return Clutter.EVENT_PROPAGATE;
        });
    }

    /**
     * Cleanly remove actor from compositor scene graph.
     */
    close() {
        if (this._grab) {
            try {
                Main.popModal(this._grab);
            } catch (e) {
                console.warn(`[WritingAssistant] popModal failed: ${e}`);
            }
            this._grab = null;
        }

        if (this._capturedEventId && this._actor) {
            this._actor.disconnect(this._capturedEventId);
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
        this._onDashboard = null;
    }
}
