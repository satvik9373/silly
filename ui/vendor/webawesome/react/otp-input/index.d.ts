import Component from '../../components/otp-input/otp-input.js';
import { type EventName } from '@lit/react';
import type { WaClearEvent, WaCompleteEvent, WaInvalidEvent } from '../../events/events.js';
export type { WaClearEvent, WaCompleteEvent, WaInvalidEvent } from '../../events/events.js';
/**
 * @summary OTP inputs collect one-time passcodes, PINs, and other fixed-length codes, one character per segment.
 * Use them for SMS verification, two-factor authentication, and invite codes.
 * @documentation https://webawesome.com/docs/components/otp-input
 * @status stable
 * @since 3.11
 *
 * @slot label - An optional label. Use this for labels that contain HTML. When `label` attribute is set it takes priority.
 * @slot hint - Optional hint text. Use this for hints that contain HTML. When `hint` attribute is set it takes priority.
 *
 * @event focus - Emitted when the control gains focus.
 * @event blur - Emitted when the control loses focus.
 * @event input - Emitted when a character is entered or removed.
 * @event change - Emitted when the value changes and the field loses focus.
 * @event wa-complete - Emitted once when all segments are filled. Cancelable — call `preventDefault()` to stop
 *   `autosubmit` from submitting the form for this completion.
 * @event wa-clear - Emitted when the control's value is cleared.
 * @event wa-invalid - Emitted when the form control has been checked for validity and its constraints aren't satisfied.
 *
 * @csspart label - The label element.
 * @csspart hint - The hint element.
 * @csspart segments - The wrapper around all segment cells and separators.
 * @csspart segment - An individual character segment cell.
 * @csspart segment-literal - Inert literal text between segment groups (e.g. space or dash).
 *
 * @cssstate --blank - Applied when no characters have been entered.
 * @cssstate --filled - Applied when all segments are filled.
 * @cssstate disabled - Applied when the component is disabled.
 * @cssstate readonly - Applied when the component is readonly.
 * @cssstate user-invalid - Applied when validation fails after interaction.
 *
 * @cssproperty [--segment-size=2.5em] - Width and height of each segment cell.
 * @cssproperty [--segment-gap=var(--wa-space-xs)] - Gap between segments (not used in `contained` appearance).
 * @cssproperty [--segment-border-radius=var(--wa-form-control-border-radius)] - Corner radius of each segment.
 * @cssproperty [--mask-char='•'] - Character shown in place of entered values when `mask` is set, and as a hint
 *   in empty segments when `with-mask` is set.
 */
declare const reactWrapper: import("@lit/react").ReactWebComponent<Component, {
    onWaComplete: EventName<WaCompleteEvent>;
    onWaClear: EventName<WaClearEvent>;
    onWaInvalid: EventName<WaInvalidEvent>;
}>;
export default reactWrapper;
