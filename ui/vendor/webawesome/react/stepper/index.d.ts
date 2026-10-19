import Component from '../../components/stepper/stepper.js';
import { type EventName } from '@lit/react';
import type { WaBeforeStepChangeEvent, WaStepChangeEvent } from '../../events/events.js';
export type { WaBeforeStepChangeEvent, WaStepChangeEvent } from '../../events/events.js';
/**
 * @summary Steppers visually guide users through a process step by step, breaking content into clear, logical
 *  stages. Use them for checkout flows, multi-step setup, onboarding, or just to show the status of a process.
 * @documentation https://webawesome.com/docs/components/stepper
 * @status experimental
 * @since 3.14
 *
 * @dependency wa-step
 *
 * @event {{ name: string, previousName: string | null, step: WaStep, previousStep: WaStep | null }} wa-before-step-change
 *  - Emitted before the active step
 *  changes. Calling `event.preventDefault()` prevents the change, to guard against invalid or unsaved data.
 * @event {{ name: string, previousName: string | null, step: WaStep, previousStep: WaStep | null }} wa-step-change
 *  - Emitted after the active step changes.
 *
 * @slot - One or more `<wa-step>` elements.
 *
 * @csspart stepper - The component's outer wrapper. A `<nav>` landmark when the stepper is `clickable`, since its
 *  steps are then controls you can navigate with; otherwise a labeled `role="group"`, since a display-only stepper has
 *  nothing to navigate.
 * @csspart summary - Visually hidden "Step X of Y" text that tells assistive technology where the active step sits.
 * @csspart steps - The `<ol>` that lays out the steps.
 *
 * @cssproperty [--gap=var(--wa-space-l)] - The space between steps.
 * @cssproperty [--marker-size=2em] - The size of each step's marker.
 * @cssproperty [--connector-color=var(--wa-color-neutral-fill-normal)] - The color of the connector line after a
 *  step that isn't completed.
 * @cssproperty --connector-color-active - The color of the connector line after a completed step. Unset by default,
 *  so the line takes the completed marker's fill and follows its `variant`.
 * @cssproperty [--connector-width=var(--wa-border-width-m)] - The thickness of the connector line, in either
 *  orientation.
 * @cssproperty [--connector-gap=0.35em] - The gap between a marker's edge and the connector line, on both sides.
 *  Kept clear of the marker geometrically, so it holds even if a marker's background is transparent.
 *
 * @cssstate completed - Applied when every step is completed.
 * @cssstate loading - Applied when at least one step is loading.
 * @cssstate stacked - Applied while the steps are laid out vertically, whether by `orientation="vertical"` or because
 *  an `auto` stepper is too narrow to give each step room.
 *
 * @ssr - During SSR, `<wa-stepper>` can't access its children to determine which step is active. To render the correct
 *  step, also set the `active` attribute on the matching `<wa-step>`. Step numbers appear once the stepper hydrates.
 */
declare const reactWrapper: import("@lit/react").ReactWebComponent<Component, {
    onWaBeforeStepChange: EventName<WaBeforeStepChangeEvent>;
    onWaStepChange: EventName<WaStepChangeEvent>;
}>;
export default reactWrapper;
