import Component from '../../components/dropdown-item/dropdown-item.js';
/**
 * @summary Dropdown items represent selectable entries within a dropdown menu, including standard actions, checkable
 *  items, and submenu triggers.
 * @documentation https://webawesome.com/docs/components/dropdown-item
 * @status stable
 * @since 3.0
 *
 * @dependency wa-icon
 *
 * @event blur - Emitted when the dropdown item loses focus.
 * @event focus - Emitted when the dropdown item gains focus.
 *
 * @slot - The dropdown item's label.
 * @slot icon - An optional icon to display before the label.
 * @slot details - Additional content or details to display after the label.
 * @slot submenu - Submenu items, typically `<wa-dropdown-item>` elements, to create a nested menu.
 *
 * @csspart checkmark - The checkmark icon (a `<wa-icon>` element) when the item is a checkbox.
 * @csspart icon - The container for the icon slot.
 * @csspart label - The container for the label slot.
 * @csspart details - The container for the details slot.
 * @csspart submenu-icon - The submenu indicator icon (a `<wa-icon>` element).
 * @csspart submenu - The submenu container.
 *
 * @cssstate active - Applied when the item is the active item in the menu.
 * @cssstate checked - Applied when the item is checked.
 * @cssstate disabled - Applied when the item is disabled.
 * @cssstate has-submenu - Applied when the item has a submenu.
 * @cssstate link - Applied when the item is a link (i.e. `href` is set).
 * @cssstate submenu-open - Applied when the item's submenu is open.
 */
declare const reactWrapper: import("@lit/react").ReactWebComponent<Component, {}>;
export default reactWrapper;
