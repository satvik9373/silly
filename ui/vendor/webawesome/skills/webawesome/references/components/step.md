# Step

`<wa-step>`

Experimental [Navigation](https://webawesome.com/docs/components/?category=navigation) [Since 3.14](https://webawesome.com/docs/resources/changelog#wa_3140)

Steps represent a single stage inside a [`<wa-stepper>`](https://webawesome.com/docs/components/stepper), showing its position, label, and status.

This component must be used as a child of [`<wa-stepper>`](https://webawesome.com/docs/components/stepper). Please see the [Stepper docs](https://webawesome.com/docs/components/stepper) to see examples of this component in action.

```html
<wa-stepper active="shipping">
  <wa-step name="cart" completed>Cart</wa-step>
  <wa-step name="shipping" data-anatomy-subject="true">
    Shipping
    <span slot="description">Enter your address</span>
  </wa-step>
  <wa-step name="payment">Payment</wa-step>
</wa-stepper>
```

## API

### Importing

If you're using the autoloader or a hosted project, components load on demand — no manual import needed. To cherry-pick a component manually, use one of the following snippets.

\*\*CDN\*\*

Import this component directly from the CDN:

```js
import 'https://ka-f.webawesome.com/webawesome@3.14.0/components/step/step.js';
```

\*\*npm\*\*

After installing Web Awesome via npm, import this component:

```js
import '@awesome.me/webawesome/dist/components/step/step.js';
```

\*\*Self-Hosted\*\*

If you're self-hosting Web Awesome, import this component from your server:

```js
import './webawesome/dist/components/step/step.js';
```

\*\*React\*\*

To import this component for React 18 or below, use the following code:

```js
import WaStep from '@awesome.me/webawesome/dist/react/step/index.js';
```

### Slots

| Name | Description |
| --- | --- |
| (default) | The step's label. |
| \`description\` | Optional text shown under the label. |
| \`icon\` | \`

### Attributes & Properties

| Name | Description | Reflects |
| --- | --- | --- |
| \`active\` active | \`\` Draws the step as the stepper's current step. The parent sets this from its own active attribute, so you only need to set it yourself for SSR. Type boolean Default false | |
| \`attention\` attention | \`'none' \\| 'pulse' \\| 'bounce'\` Adds an animation to the step's marker to draw attention to it, e.g. the step the user should do next. Type Default 'none' | |
| \`completed\` completed | \`boolean\` Marks the step done. Shows a checkmark instead of the step number. Type Default false | |
| \`disabled\` disabled | \`next()\` Makes the step non-interactive. It can't be clicked or reached with /goTo(), and it renders as a disabled button when the stepper is clickable. Type boolean Default false | |
| \`loading\` loading | \`boolean\` Shows a loading indicator instead of the step number, e.g. while an async transition is in progress. Type Default false | |
| \`name\` name | \`active\` Identifies the step. Matched against the stepper's attribute and used in events. Type string Default '' | |
| \`variant\` variant | \`brand\` Colors the step's marker with a semantic color. Upcoming steps keep a neutral outline so a default stepper reads quietly. The color is cosmetic; pair it with an icon in the icon slot and a clear label when a step needs to read as failed or flagged. Type 'neutral' \\| 'brand' \\| 'success' \\| 'warning' \\| 'danger' Default 'brand' | |
| \`withDescription\` with-description | \`true\` Only required for SSR. Set to if you're slotting in a description element, so the server-rendered markup includes it before the component hydrates on the client. Type boolean Default false | |

### CSS Custom Properties

| Name | Description |
| --- | --- |
| \`--pulse-color\` | \`attention="pulse"\` The color of the marker's pulse effect when using . Defaults to the step's accent color. |

### Custom States

| Name | Description | CSS selector |
| --- | --- | --- |
| \`active\` | Applied when this is the parent stepper's current step. | \`:state(active)\` |
| \`clickable\` | \`clickable\` Applied by the parent stepper when its attribute is set, allowing this step to be clicked or activated (Enter/Space) directly. | \`:state(clickable)\` |
| \`completed\` | \`completed\` Mirrors the attribute. | \`:state(completed)\` |
| \`disabled\` | \`disabled\` Mirrors the attribute. | \`:state(disabled)\` |
| \`loading\` | \`loading\` Mirrors the attribute. | \`:state(loading)\` |
| \`locked\` | \`linear\` Applied by the parent stepper when is set and this step can't be reached yet, i.e. it comes after the first incomplete step. | \`:state(locked)\` |

### CSS Parts

| Name | Description | CSS selector |
| --- | --- | --- |
| \`button\` | \`\` The wrapping the marker and content. Only rendered when the parent stepper is clickable; otherwise the same wrapper is a plain, non-focusable element. | \`::part(button)\` |
| \`connector\` | The line connecting this step to its neighbors. Each step draws the half leading in and the half leading out, and both carry this part name. | \`::part(connector)\` |
| \`content\` | The wrapper around the label, status text, and description. | \`::part(content)\` |
| \`description\` | The step's description. | \`::part(description)\` |
| \`label\` | The step's label. | \`::part(label)\` |
| \`marker\` | The circular marker that shows the step's number, checkmark, or loading indicator. | \`::part(marker)\` |
| \`spinner\` | \`loading\` The spinner shown in the marker while the step is . | \`::part(spinner)\` |
| \`status\` | Visually hidden text that tells assistive technology whether the step is completed, not completed, or locked. | \`::part(status)\` |
| \`step\` | The component's outer wrapper. | \`::part(step)\` |

### Dependencies

This component automatically imports the following elements. Sub-dependencies, if any exist, will also be included in this list.

-   [`<wa-icon>`](https://webawesome.com/docs/components/icon)
-   [`<wa-spinner>`](https://webawesome.com/docs/components/spinner)