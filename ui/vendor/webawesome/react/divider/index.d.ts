import Component from '../../components/divider/divider.js';
/**
 * @summary Dividers visually separate or group adjacent elements with a horizontal or vertical line. Use them to
 *  establish rhythm and hierarchy within menus, toolbars, and layouts.
 * @documentation https://webawesome.com/docs/components/divider
 * @status stable
 * @since 2.0
 *
 * @slot - An optional label to show in the center of the divider.
 *
 * @csspart label - The container that wraps the divider's label.
 *
 * @cssproperty --color - The color of the divider.
 * @cssproperty --width - The width of the divider.
 * @cssproperty --spacing - The spacing of the divider.
 * @cssproperty --label-spacing - The amount of space between the label and the divider's lines.
 * @cssproperty --label-offset - The length of the line between the divider's edge and a label placed at the `start` or
 *  `end`.
 *
 * @ssr - If you slot in a label, set the `with-label` attribute, otherwise the label won't be centered in the divider
 *  until the component hydrates on the client. This works around the lack of a `:has-slotted` CSS pseudo-class.
 */
declare const reactWrapper: import("@lit/react").ReactWebComponent<Component, {}>;
export default reactWrapper;
