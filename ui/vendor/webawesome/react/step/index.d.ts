import Component from '../../components/step/step.js';
/**
 * @summary Steps represent a single stage inside a `<wa-stepper>`, showing its position, label, and status.
 * @documentation https://webawesome.com/docs/components/step
 * @status experimental
 * @since 3.14
 *
 * @dependency wa-icon
 * @dependency wa-spinner
 *
 * @slot - The step's label.
 * @slot description - Optional text shown under the label.
 * @slot icon - An element, such as `<wa-icon>`, that replaces the step number, checkmark, or loading indicator.
 *
 * @csspart step - The component's outer wrapper.
 * @csspart connector - The line connecting this step to its neighbors. Each step draws the half leading in and the
 *  half leading out, and both carry this part name.
 * @csspart button - The `<button>` wrapping the marker and content. Only rendered when the parent stepper is
 *  `clickable`; otherwise the same wrapper is a plain, non-focusable element.
 * @csspart marker - The circular marker that shows the step's number, checkmark, or loading indicator.
 * @csspart spinner - The spinner shown in the marker while the step is `loading`.
 * @csspart content - The wrapper around the label, status text, and description.
 * @csspart label - The step's label.
 * @csspart status - Visually hidden text that tells assistive technology whether the step is completed, not
 *  completed, or locked.
 * @csspart description - The step's description.
 *
 * @cssproperty --pulse-color - The color of the marker's pulse effect when using `attention="pulse"`. Defaults to the
 *  step's accent color.
 *
 * @cssstate active - Applied when this is the parent stepper's current step.
 * @cssstate completed - Mirrors the `completed` attribute.
 * @cssstate loading - Mirrors the `loading` attribute.
 * @cssstate disabled - Mirrors the `disabled` attribute.
 * @cssstate locked - Applied by the parent stepper when `linear` is set and this step can't be reached yet, i.e. it
 *  comes after the first incomplete step.
 * @cssstate clickable - Applied by the parent stepper when its `clickable` attribute is set, allowing this step to
 *  be clicked or activated (Enter/Space) directly.
 */
declare const reactWrapper: import("@lit/react").ReactWebComponent<Component, {}>;
export default reactWrapper;
