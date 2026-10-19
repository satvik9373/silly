import Component from '../../components/tag-input/tag-input.js';
import { type EventName } from '@lit/react';
import type { WaClearEvent, WaCreateEvent, WaInvalidEvent } from '../../events/events.js';
export type { WaClearEvent, WaCreateEvent, WaInvalidEvent } from '../../events/events.js';
/**
 * @summary Tag inputs collect a list of short values, such as keywords, email addresses, or labels, as removable tags.
 *  Users add a tag by typing and pressing Enter or a delimiter, and each tag is submitted as its own form value.
 * @documentation https://webawesome.com/docs/components/tag-input
 * @status experimental
 * @since 3.13
 *
 * @dependency wa-icon
 * @dependency wa-tag
 *
 * @slot label - The tag input's label. Alternatively, you can use the `label` attribute.
 * @slot start - An element, such as `<wa-icon>`, placed at the start of the control.
 * @slot end - An element, such as `<wa-icon>`, placed at the end of the control.
 * @slot clear-icon - An icon to use in lieu of the default clear icon.
 * @slot hint - Text that describes how to use the tag input. Alternatively, you can use the `hint` attribute.
 *
 * @event blur - Emitted when the control loses focus.
 * @event change - Emitted when a tag is added, removed, or all tags are cleared by the user.
 * @event focus - Emitted when the control gains focus.
 * @event input - Emitted when the user types in the text box or when a tag is added or removed.
 * @event wa-create - Emitted before typed text becomes a tag. Call `event.preventDefault()` to reject it. The event
 *  `detail` contains `{ inputValue: string }`, the text that would become the tag.
 * @event wa-clear - Emitted when the clear button is activated.
 * @event wa-invalid - Emitted when the form control has been checked for validity and its constraints aren't satisfied.
 *
 * @csspart form-control-label - The label.
 * @csspart tag-input - The component's outer wrapper, the bordered box that holds the tags and text box.
 * @csspart start - The container that wraps the `start` slot.
 * @csspart tags - The list that holds the tags.
 * @csspart tag - Each tag, a `<wa-tag>`.
 * @csspart tag__content - The tag's content part.
 * @csspart tag__remove-button - The tag's remove button.
 * @csspart tag__remove-button__base - The tag's remove button base part.
 * @csspart input - The internal text box, an `<input>` element.
 * @csspart clear-button - The clear button.
 * @csspart end - The container that wraps the `end` slot.
 * @csspart hint - The hint's wrapper.
 *
 * @cssstate blank - The tag input has no tags.
 * @cssstate readonly - The tag input is readonly.
 */
declare const reactWrapper: import("@lit/react").ReactWebComponent<Component, {
    onWaCreate: EventName<WaCreateEvent>;
    onWaClear: EventName<WaClearEvent>;
    onWaInvalid: EventName<WaInvalidEvent>;
}>;
export default reactWrapper;
