# Stepper

`<wa-stepper>`

Experimental [Navigation](https://webawesome.com/docs/components/?category=navigation) [Since 3.14](https://webawesome.com/docs/resources/changelog#wa_3140)

Steppers visually guide users through a process step by step, breaking content into clear, logical stages. Use them for checkout flows, multi-step setup, onboarding, or just to show the status of a process.

```html
<wa-stepper active="shipping">
  <wa-step name="cart" completed>Cart</wa-step>
  <wa-step name="shipping">Shipping</wa-step>
  <wa-step name="payment">Payment</wa-step>
</wa-stepper>
```

Set the `active` attribute to the name of the current [`<wa-step>`](https://webawesome.com/docs/components/step). A stepper is a display, not a form control, and by default its steps aren't directly interactive. Pair it with your own Next/Back buttons (see [Navigating Declaratively](#navigating-declaratively)) or call its methods directly to move between steps as the user progresses. Add the `clickable` attribute (see [Clickable](#clickable)) to let people click a step, or focus it and press Enter/Space, to jump straight to it.

## Accessibility Considerations

-   **Structure.** The stepper renders an ordered list, and each [`<wa-step>`](https://webawesome.com/docs/components/step) carries `role="listitem"`. When the stepper is [`clickable`](#clickable), the list sits in a `<nav>` landmark, since its steps are then controls you can navigate with; otherwise it's a labeled group, so a display-only stepper doesn't add a navigation landmark with nothing to navigate. Set the `label` attribute whenever more than one stepper appears on the same page, so screen reader users can tell them apart. Without it, the wrapper gets a generic localized name.
-   **Current step.** The active step carries `aria-current="step"` on whichever element is actually focusable: the step's own host when the stepper isn't `clickable`, or its inner `<button>` when it is. It's removed, not set to `"false"`, everywhere else. The stepper also renders visually hidden "Step 2 of 4" text, so the position is announced without relying on the markers.
-   **Step changes are announced.** When `next()`, `previous()`, or `goTo()` changes the active step, the new position is announced to screen readers through a shared live region, so the update isn't silent even when nothing in the stepper has focus.
-   **Step status.** Each step's status is announced, not just shown. Completed steps carry visually hidden "Completed" text, pending steps "Not completed", disabled steps "Disabled", and locked steps "Locked". The checkmark itself is decorative.
-   **Keyboard.** Steps are only in the tab order when the stepper is [`clickable`](#clickable), and then each one is rendered as a `<button>`: Tab moves between them and Enter or Space activates one, the same as clicking it. `disabled` and locked steps render as disabled buttons, so they're skipped. Without `clickable`, nothing in the stepper takes focus, and screen readers still read every step in order.
-   **Busy state.** Each loading step carries `aria-busy="true"`. The stepper itself carries the `loading` custom state while any step is loading, as a styling hook. It isn't propagated to the stepper's own `aria-busy`, since nesting that on the landmark can suppress announcements for the whole region.
-   **Color and meaning.** The `variant` attribute is cosmetic. It changes color, which doesn't carry meaning on its own, so include the reason in the step's visible label or description, and add an icon in the `icon` slot when a step needs to read as failed.

## API

### Importing

If you're using the autoloader or a hosted project, components load on demand — no manual import needed. To cherry-pick a component manually, use one of the following snippets.

\*\*CDN\*\*

Import this component directly from the CDN:

```js
import 'https://ka-f.webawesome.com/webawesome@3.14.0/components/stepper/stepper.js';
```

\*\*npm\*\*

After installing Web Awesome via npm, import this component:

```js
import '@awesome.me/webawesome/dist/components/stepper/stepper.js';
```

\*\*Self-Hosted\*\*

If you're self-hosting Web Awesome, import this component from your server:

```js
import './webawesome/dist/components/stepper/stepper.js';
```

\*\*React\*\*

To import this component for React 18 or below, use the following code:

```js
import WaStepper from '@awesome.me/webawesome/dist/react/stepper/index.js';
```

### Slots

| Name | Description |
| --- | --- |
| (default) | \`\` One or more elements. |

### Attributes & Properties

| Name | Description | Reflects |
| --- | --- | --- |
| \`active\` active | \`string\` The name of the active step. Falls back to the first step if unset, or if it doesn't match any step's name. Type Default '' | |
| \`clickable\` clickable | \`next()\` Allows clicking a step, or focusing it and pressing Enter/Space, to jump straight to it. When unset (the default), only /previous()/goTo() change the active step, e.g. from your own Next/Back buttons or a data-stepper invoker. Type boolean Default false | |
| \`label\` label | \`string\` A label that describes the stepper to assistive devices. Especially useful when more than one is on the page. Type Default '' | |
| \`linear\` linear | \`next()\` Requires steps to be completed in order. When set, /goTo()/a data-stepper invoker and, if clickable is also set, clicking or activating a step can't reach a step until every step before it is completed. Every step past that point renders as locked. Type boolean Default false | |
| \`orientation\` orientation | \`auto\` The stepper's layout direction. lays steps out in a row and stacks them when the stepper is too narrow to give each step about 6em of width, so labels stay legible on small screens; use it for anything shown on a phone. It relies on measuring the stepper, so a server-rendered auto stepper starts as a row and stacks once it hydrates, which is why horizontal is the default. Type 'horizontal' \\| 'vertical' \\| 'auto' Default 'horizontal' | |

### Methods

| Name | Description | Arguments |
| --- | --- | --- |
| \`goTo()\` | \`wa-before-step-change\` Requests a change to the named step. Emits a cancelable ; if not canceled, updates active, emits wa-step-change, and announces the new position to assistive technology. No-ops silently if the step doesn't exist, is disabled, or (in linear mode) isn't reachable yet. | \`name: string\` |
| \`next()\` | Advances to the step after the active one, if any. | |
| \`previous()\` | Goes back to the step before the active one, if any. | |

### Events

| Name | Description |
| --- | --- |
| \`detail\` | |
| \`wa-before-step-change\` | \`event.preventDefault()\` Emitted before the active step changes. Calling prevents the change, to guard against invalid or unsaved data. |
| \`wa-step-change\` | Emitted after the active step changes. |

### CSS Custom Properties

| Name | Description |
| --- | --- |
| \`--connector-color\` | \`var(--wa-color-neutral-fill-normal)\` The color of the connector line after a step that isn't completed. Default |
| \`--connector-color-active\` | \`variant\` The color of the connector line after a completed step. Unset by default, so the line takes the completed marker's fill and follows its . |
| \`--connector-gap\` | \`0.35em\` The gap between a marker's edge and the connector line, on both sides. Kept clear of the marker geometrically, so it holds even if a marker's background is transparent. Default |
| \`--connector-width\` | \`var(--wa-border-width-m)\` The thickness of the connector line, in either orientation. Default |
| \`--gap\` | \`var(--wa-space-l)\` The space between steps. Default |
| \`--marker-size\` | \`2em\` The size of each step's marker. Default |

### Custom States

| Name | Description | CSS selector |
| --- | --- | --- |
| \`completed\` | Applied when every step is completed. | \`:state(completed)\` |
| \`loading\` | Applied when at least one step is loading. | \`:state(loading)\` |
| \`stacked\` | \`orientation="vertical"\` Applied while the steps are laid out vertically, whether by or because an auto stepper is too narrow to give each step room. | \`:state(stacked)\` |

### CSS Parts

| Name | Description | CSS selector |
| --- | --- | --- |
| \`stepper\` | \`

\` The component's outer wrapper. A landmark when the stepper is clickable, since its steps are then controls you can navigate with; otherwise a labeled role="group", since a display-only stepper has nothing to navigate. | \`::part(stepper)\` |
| \`steps\` | \`\` The that lays out the steps. | \`::part(steps)\` |
| \`summary\` | Visually hidden "Step X of Y" text that tells assistive technology where the active step sits. | \`::part(summary)\` |

### Dependencies

This component automatically imports the following elements. Sub-dependencies, if any exist, will also be included in this list.

-   [`<wa-icon>`](https://webawesome.com/docs/components/icon)
-   [`<wa-spinner>`](https://webawesome.com/docs/components/spinner)
-   [`<wa-step>`](https://webawesome.com/docs/components/step)

### SSR

Learn more about [Server-Side Rendering (SSR)](https://webawesome.com/docs/ssr).

During SSR, `<wa-stepper>` can't access its children to determine which step is active. To render the correct step, also set the `active` attribute on the matching [`<wa-step>`](https://webawesome.com/docs/components/step). Step numbers appear once the stepper hydrates.

## Examples

### Clickable

Add the `clickable` attribute to render each step as a button, so clicking it, or focusing it and pressing Enter/Space, jumps straight to it, the same as calling `goTo()`. Without it, steps aren't focusable, and only `next()`/`previous()`/`goTo()` change the active step. Disabled and locked steps render as disabled buttons.

```html
<wa-stepper active="shipping" clickable>
  <wa-step name="cart" completed>Cart</wa-step>
  <wa-step name="shipping">Shipping</wa-step>
  <wa-step name="payment">Payment</wa-step>
</wa-stepper>
```

### Linear

Add the `linear` attribute to require steps to be completed in order. Every step past the first incomplete one renders `locked`, and `next()`/`goTo()` (including a [`data-stepper`](#navigating-declaratively) invoker, or a click/activation when `clickable` is also set) can't reach it until the steps before it are `completed`.

Combined with `clickable`, this gives the common checkout behavior: users can return to any completed step and advance to the next one, but can't skip ahead.

```html
<wa-stepper active="shipping" linear clickable>
  <wa-step name="cart" completed>Cart</wa-step>
  <wa-step name="shipping">Shipping</wa-step>
  <wa-step name="payment">Payment</wa-step>
</wa-stepper>
```

### Orientation

Set the `orientation` attribute to `vertical` to stack the steps, useful in a sidebar or a narrow column.

```html
<wa-stepper orientation="vertical" active="proof">
  <wa-step name="mix" completed>Mix</wa-step>
  <wa-step name="knead" completed>Knead</wa-step>
  <wa-step name="proof">
    Proof
    <span slot="description">Let it rise. Resist poking it.</span>
  </wa-step>
  <wa-step name="bake">Bake</wa-step>
</wa-stepper>
```

Each connector runs from its step's marker, across the gap, to the next marker. To lengthen the connectors, increase the `--gap` custom property.

```html
<wa-stepper orientation="vertical" active="proof" style="--gap: var(--wa-space-3xl);">
  <wa-step name="mix" completed>Mix</wa-step>
  <wa-step name="knead" completed>Knead</wa-step>
  <wa-step name="proof">
    Proof
    <span slot="description">Let it rise. Resist poking it.</span>
  </wa-step>
  <wa-step name="bake">Bake</wa-step>
</wa-stepper>
```

Set `orientation` to `auto` to lay steps out in a row and stack them when the stepper is narrower than about 6em per step, so labels stay readable on small screens. Use it for any stepper that will be shown on a phone. Resize the example to see the switch. While stacked, the stepper has the `stacked` custom state, so `wa-stepper:state(stacked)` targets it.

The default, `horizontal`, keeps a row at any width. Labels wrap between words, and a row that still can't fit overflows its container rather than squeezing the steps. It's the default because `auto` measures the stepper in the browser, so a server-rendered `auto` stepper renders as a row first and stacks once it hydrates.

```html
<wa-stepper orientation="auto" active="team">
  <wa-step name="account" completed>Account</wa-step>
  <wa-step name="profile" completed>Profile</wa-step>
  <wa-step name="team">Team</wa-step>
  <wa-step name="notifications">Notifications</wa-step>
</wa-stepper>
```

### Variant

Set the `variant` attribute on a step to color its marker with a semantic color. The current step uses the variant's loud fill, a completed step its normal fill, and an upcoming step a thin border in its color. The default is `brand`, whose upcoming steps keep a neutral border so a plain stepper reads quietly. The color is cosmetic and never changes the marker's content, like `variant` on a badge or callout.

```html
<wa-stepper active="current">
  <wa-step name="current">Current</wa-step>
  <wa-step name="success" variant="success">Success</wa-step>
  <wa-step name="warning" variant="warning">Warning</wa-step>
  <wa-step name="danger" variant="danger">Danger</wa-step>
</wa-stepper>
```

To flag a step that failed or needs attention, pair the variant with an icon in the [`icon` slot](#custom-icon) and state the reason in the label or description, so the meaning doesn't depend on color alone.

```html
<wa-stepper active="payment">
  <wa-step name="cart" completed variant="success">Cart</wa-step>
  <wa-step name="shipping" completed variant="success">Shipping</wa-step>
  <wa-step name="payment" variant="danger">
    <wa-icon slot="icon" name="xmark" library="system" variant="solid"></wa-icon>
    Payment
    <span slot="description">Card declined</span>
  </wa-step>
</wa-stepper>
```

### Size

A stepper is sized relative to the current font size, like a badge. Set `font-size` on the stepper (or an ancestor element) to change it; markers, connectors, and text scale together.

```html
<div class="wa-stack wa-gap-l">
  <wa-stepper class="size-stepper" active="shipping" style="font-size: var(--wa-font-size-xs);">
    <wa-step name="cart" completed>Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>
  <wa-stepper class="size-stepper" active="shipping" style="font-size: var(--wa-font-size-s);">
    <wa-step name="cart" completed>Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>
  <wa-stepper class="size-stepper" active="shipping" style="font-size: var(--wa-font-size-m);">
    <wa-step name="cart" completed>Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>
  <wa-stepper class="size-stepper" active="shipping" style="font-size: var(--wa-font-size-l);">
    <wa-step name="cart" completed>Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>
  <wa-stepper class="size-stepper" active="shipping" style="font-size: var(--wa-font-size-xl);">
    <wa-step name="cart" completed>Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>
</div>

<style>
  .size-stepper {
    max-inline-size: 24em;
  }
</style>
```

### Drawing Attention

Set the `attention` attribute on a step to `pulse` or `bounce` to animate its marker, the same options as [`<wa-badge>`](https://webawesome.com/docs/components/badge#drawing-attention). Use it sparingly, for the one step the user should act on next. The pulse color follows the step's accent; set the `--pulse-color` custom property to change it. Both animations are disabled when the user prefers reduced motion.

```html
<div class="wa-stack">
  <wa-stepper active="verify">
    <wa-step name="account" completed>Create account</wa-step>
    <wa-step name="verify" attention="pulse">Verify email</wa-step>
    <wa-step name="profile">Set up profile</wa-step>
  </wa-stepper>

  <wa-stepper active="verify">
    <wa-step name="account" completed>Create account</wa-step>
    <wa-step name="verify" attention="bounce">Verify email</wa-step>
    <wa-step name="profile">Set up profile</wa-step>
  </wa-stepper>
</div>
```

### Description

Add the `description` slot to any step for supporting text under its label.

```html
<wa-stepper active="shipping">
  <wa-step name="cart" completed>
    Cart
    <span slot="description">3 items</span>
  </wa-step>
  <wa-step name="shipping">
    Shipping
    <span slot="description">Enter your address</span>
  </wa-step>
  <wa-step name="payment">
    Payment
    <span slot="description">Add a card</span>
  </wa-step>
</wa-stepper>
```

### Custom Icon

Use the `icon` slot on a step to replace its number, checkmark, or spinner with an element such as [`<wa-icon>`](https://webawesome.com/docs/components/icon). The marker keeps its state styling, so an icon reads as completed, current, or upcoming the same way a number would.

```html
<wa-stepper active="shipped">
  <wa-step name="ordered" completed>
    <wa-icon slot="icon" name="bag-shopping"></wa-icon>
    Ordered
    <span slot="description">Monday</span>
  </wa-step>
  <wa-step name="shipped">
    <wa-icon slot="icon" name="truck"></wa-icon>
    Shipped
    <span slot="description">Left the warehouse</span>
  </wa-step>
  <wa-step name="delivered">
    <wa-icon slot="icon" name="house"></wa-icon>
    Delivered
    <span slot="description">Thursday, probably</span>
  </wa-step>
</wa-stepper>
```

### Loading

Add the `loading` attribute to a step to show a spinner in its marker instead of a number, e.g. while an async transition is in progress.

```html
<wa-stepper active="steep">
  <wa-step name="boil" completed>Boil the kettle</wa-step>
  <wa-step name="warm" completed>Warm the pot</wa-step>
  <wa-step name="steep" loading>
    Steep
    <span slot="description">Four minutes for a proper cuppa</span>
  </wa-step>
  <wa-step name="pour">Pour</wa-step>
</wa-stepper>
```

### Disabled

Add the `disabled` attribute to a step that doesn't apply to the current user. The step stays visible, so the full process is still shown, but it can't be clicked, focused, or reached with `next()`/`goTo()`.

```html
<wa-stepper active="cart">
  <wa-step name="cart">Cart</wa-step>
  <wa-step name="shipping">Shipping</wa-step>
  <wa-step name="gift-wrap" disabled>Gift Wrap</wa-step>
  <wa-step name="payment">Payment</wa-step>
</wa-stepper>
```

### Navigating Declaratively

Add the `data-stepper` attribute to any button on the page, with `next <id>`, `previous <id>`, or `goto <id> <name>` as its value, to call `next()`, `previous()`, or `goTo()` on the stepper with that `id`. It's the same convention as [`<wa-dialog>`](https://webawesome.com/docs/components/dialog)'s `data-dialog="open <id>"`, and the button doesn't need to be inside the stepper.

```html
<div class="stepper-declarative-demo">
  <wa-stepper id="stepper-declarative" active="cart">
    <wa-step name="cart" completed>Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>

  <wa-divider></wa-divider>

  <div class="wa-cluster">
    <wa-button appearance="filled" data-stepper="previous stepper-declarative">Back</wa-button>
    <wa-button appearance="filled" data-stepper="next stepper-declarative">Continue</wa-button>
    <wa-button appearance="filled" data-stepper="goto stepper-declarative payment">Skip to Payment</wa-button>
  </div>
</div>
```

### Reacting to Changes

The `wa-step-change` event fires once the active step has changed, with `name` and `previousName` in `event.detail`, plus the `step` and `previousStep` elements themselves. The stepper never sets `completed` itself. Mark a step done from your own code, e.g. once the user has advanced past it.

```html
<div class="stepper-events-demo">
  <wa-stepper id="stepper-events" active="cart">
    <wa-step name="cart" completed>Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>

  <wa-divider></wa-divider>

  <div class="wa-cluster wa-align-items-center">
    <wa-button appearance="filled" data-stepper="previous stepper-events">Back</wa-button>
    <wa-button appearance="filled" data-stepper="next stepper-events">Continue</wa-button>
    <small>Active step: <span id="stepper-events-output">cart</span></small>
  </div>
</div>

<script>
  const stepperEvents = document.getElementById('stepper-events');
  const stepperEventsOutput = document.getElementById('stepper-events-output');

  stepperEvents.addEventListener('wa-step-change', event => {
    const { name, step, previousStep } = event.detail;
    const steps = [...stepperEvents.querySelectorAll('wa-step')];

    if (previousStep) {
      if (steps.indexOf(step) > steps.indexOf(previousStep)) {
        // Advancing: the step just left behind is done.
        previousStep.completed = true;
      } else {
        // Going back: the step being revisited is back in progress, not done.
        step.completed = false;
      }
    }

    stepperEventsOutput.textContent = name;
  });
</script>
```

### Pairing with Content

The stepper only shows progress; it doesn't hold the content for each step. Keep that content in your own elements and show the one that matches the active step from a `wa-step-change` listener. This keeps the stepper usable with any layout, from a single form panel to a full page per step.

```html
<div class="stepper-content-demo wa-stack">
  <wa-stepper id="stepper-content" active="cart">
    <wa-step name="cart">Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>

  <p data-step="cart">Review the items in your cart.</p>
  <p data-step="shipping" hidden>Enter the address to ship to.</p>
  <p data-step="payment" hidden>Add a card to pay with.</p>

  <wa-divider></wa-divider>

  <div class="wa-cluster">
    <wa-button appearance="filled" data-stepper="previous stepper-content">Back</wa-button>
    <wa-button appearance="filled" data-stepper="next stepper-content">Continue</wa-button>
  </div>
</div>

<script>
  const stepperContent = document.getElementById('stepper-content');
  const stepperContentPanels = stepperContent.parentElement.querySelectorAll('[data-step]');

  stepperContent.addEventListener('wa-step-change', event => {
    stepperContentPanels.forEach(panel => {
      panel.hidden = panel.dataset.step !== event.detail.name;
    });
  });
</script>
```

### Preventing a Step Change

The `wa-before-step-change` event fires before the step changes and is cancelable. Call `event.preventDefault()` to block the transition, e.g. to guard against unsaved changes. Toggle the switch and press Continue to see the change blocked or allowed.

```html
<div class="stepper-guard-demo">
  <wa-stepper id="stepper-guard" active="shipping">
    <wa-step name="cart" completed>Cart</wa-step>
    <wa-step name="shipping">Shipping</wa-step>
    <wa-step name="payment">Payment</wa-step>
  </wa-stepper>

  <wa-divider></wa-divider>

  <div class="wa-cluster wa-align-items-center">
    <wa-switch id="stepper-guard-unsaved" checked>Unsaved changes</wa-switch>
    <wa-button appearance="filled" data-stepper="next stepper-guard">Continue</wa-button>
    <small id="stepper-guard-output"></small>
  </div>
</div>

<script>
  const stepperGuard = document.getElementById('stepper-guard');
  const stepperGuardUnsaved = document.getElementById('stepper-guard-unsaved');
  const stepperGuardOutput = document.getElementById('stepper-guard-output');

  stepperGuard.addEventListener('wa-before-step-change', event => {
    if (stepperGuardUnsaved.checked) {
      event.preventDefault();
      stepperGuardOutput.textContent = 'Blocked by unsaved changes';
    } else {
      stepperGuardOutput.textContent = '';
    }
  });

  stepperGuard.addEventListener('wa-step-change', event => {
    if (event.detail.previousStep) event.detail.previousStep.completed = true;
  });
</script>
```

### Customizing

Use the exported [CSS parts](#css-parts) and [custom properties](#css-custom-properties) to restyle the stepper. This example gives completed steps the `success` variant, and the connector after each completed step follows it. It sets the inactive connector with the `--connector-color` custom property, enlarges the markers and widens the space between steps with the `--marker-size` and `--gap` custom properties, then squares off the markers and bolds their text via each step's `marker` part. The part belongs to [`<wa-step>`](https://webawesome.com/docs/components/step), so the selector targets the steps, not the stepper; see the [Step page](https://webawesome.com/docs/components/step#css-parts) for every part a step exposes.

```html
<wa-stepper class="custom-stepper" active="shipping">
  <wa-step name="cart" completed variant="success">Cart</wa-step>
  <wa-step name="shipping">Shipping</wa-step>
  <wa-step name="payment">Payment</wa-step>
</wa-stepper>

<style>
  .custom-stepper {
    --marker-size: 2.5em;
    --gap: var(--wa-space-2xl);
    --connector-color: var(--wa-color-neutral-border-normal);
  }

  .custom-stepper wa-step::part(marker) {
    font-weight: var(--wa-font-weight-bold);
    border-radius: var(--wa-border-radius-m);
  }
</style>
```

Here the connector properties become a transit line, the `marker` part turns each stop into a ring, and the `completed` and `active` custom states mark the stops behind you and the one you're at. Shrink it to see `orientation="auto"` stack it into a strip map.

```html
<wa-stepper class="tube-stepper" label="Piccadilly line" orientation="auto" active="green-park">
  <wa-step name="heathrow" completed>Heathrow</wa-step>
  <wa-step name="earls-court" completed>
    Earl's Court
    <span slot="description">District line</span>
  </wa-step>
  <wa-step name="knightsbridge" completed>Knightsbridge</wa-step>
  <wa-step name="green-park" attention="pulse">
    Green Park
    <span slot="description">Victoria and Jubilee lines</span>
  </wa-step>
  <wa-step name="kings-cross">King's Cross</wa-step>
</wa-stepper>

<style>
  .tube-stepper {
    --line: var(--wa-color-brand-fill-loud);
    --marker-size: 1.25em;
    --gap: var(--wa-space-m);
    --connector-width: 0.375em;
    --connector-gap: 0px;
    --connector-color: var(--wa-color-brand-fill-normal);
    --connector-color-active: var(--line);
  }

  .tube-stepper wa-step::part(marker) {
    color: transparent;
    background-color: var(--wa-color-surface-default);
    border: 0.25em solid var(--line);
  }

  .tube-stepper wa-step:state(completed)::part(marker) {
    background-color: var(--line);
  }

  .tube-stepper wa-step:state(active)::part(marker) {
    scale: 1.25;
  }
</style>
```

Steps share the row equally. Give a step with more content extra room by setting `flex` on it. The connectors meet in the middle of each gap, so uneven widths don't break the line. In a stacked layout, `flex` has no effect, because the column has no extra height to distribute.

```html
<wa-stepper class="uneven-stepper" orientation="auto" active="mordor">
  <wa-step name="shire" completed>The Shire</wa-step>
  <wa-step name="rivendell" completed>Rivendell</wa-step>
  <wa-step name="moria" completed>Moria</wa-step>
  <wa-step name="mordor">
    Mount Doom
    <span slot="description">One does not simply walk into Mordor</span>
  </wa-step>
</wa-stepper>

<style>
  .uneven-stepper wa-step[name='mordor'] {
    flex: 3;
  }
</style>
```
