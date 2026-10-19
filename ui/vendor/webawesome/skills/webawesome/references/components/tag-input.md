# Tag Input

`<wa-tag-input>`

Experimental [Forms](https://webawesome.com/docs/components/?category=forms) [Since 3.13](https://webawesome.com/docs/resources/changelog#wa_3130)

Tag inputs collect a list of short values, such as keywords, email addresses, or labels, as removable tags. Users add a tag by typing and pressing Enter or a delimiter, and each tag is submitted as its own form value.

```html
<wa-tag-input label="Keywords" placeholder="Add a keyword" value="design, accessibility"></wa-tag-input>
```

```html
<wa-tag-input label="Topics" hint="Press Enter or type a comma after each topic." value="Design, CSS" with-clear>
  <wa-icon slot="start" name="tag"></wa-icon>
</wa-tag-input>
```

This component works with standard `<form>` elements. See [form controls](https://webawesome.com/docs/form-controls) for form submission and client-side validation.

## Accessibility Considerations

The tags are exposed to assistive technology as a list, and each tag's remove button is labeled. A focused tag carries a hidden description explaining that Backspace or Delete removes it. Additions, removals, rejected duplicates, and clearing all tags are announced to screen readers. Always provide a label with the `label` attribute or slot; without one, the text box has no accessible name.

Tags are reachable with the arrow keys rather than Tab, so the control takes a single tab stop:

| Key | Behavior |
| --- | --- |
| Enter | Adds the typed text as a tag. With an empty text box, submits the form. |
| Delimiter (, by default) | Adds the text before it as a tag |
| Backspace | With an empty text box, removes the last tag. On a focused tag, removes it and focuses the previous one. |
| Delete | On a focused tag, removes it and focuses the next one |
| ← → | From an empty text box, ← focuses the last tag. Moves between tags, and → from the last tag returns to the text box. |
| Home End | On a focused tag, Home focuses the first tag and End returns to the text box |
| Escape | Clears the typed text. On a focused tag, returns to the text box. |

In right-to-left languages, the arrow keys follow the reading direction, so → moves toward the start of the list and ← moves toward the text box.

## API

### Importing

If you're using the autoloader or a hosted project, components load on demand — no manual import needed. To cherry-pick a component manually, use one of the following snippets.

\*\*CDN\*\*

Import this component directly from the CDN:

```js
import 'https://ka-f.webawesome.com/webawesome@3.14.0/components/tag-input/tag-input.js';
```

\*\*npm\*\*

After installing Web Awesome via npm, import this component:

```js
import '@awesome.me/webawesome/dist/components/tag-input/tag-input.js';
```

\*\*Self-Hosted\*\*

If you're self-hosting Web Awesome, import this component from your server:

```js
import './webawesome/dist/components/tag-input/tag-input.js';
```

\*\*React\*\*

To import this component for React 18 or below, use the following code:

```js
import WaTagInput from '@awesome.me/webawesome/dist/react/tag-input/index.js';
```

### Slots

| Name | Description |
| --- | --- |
| \`clear-icon\` | An icon to use in lieu of the default clear icon. |
| \`end\` | \`\` An element, such as , placed at the start of the control. |

### Attributes & Properties

| Name | Description | Reflects |
| --- | --- | --- |
| \`allowDuplicates\` allow-duplicates | \`boolean\` Allows the same tag to be added more than once. By default, duplicates are ignored. Type Default false | |
| \`appearance\` appearance | \`'filled' \\| 'outlined' \\| 'filled-outlined'\` The tag input's visual appearance. Type Default 'outlined' | |
| \`autocapitalize\` autocapitalize | \`'off' \\| 'none' \\| 'on' \\| 'sentences' \\| 'words' \\| 'characters'\` Controls whether and how text input is automatically capitalized as it is entered by the user. Type | |
| \`autocomplete\` autocomplete | \`off\` Specifies what permission the browser has to provide assistance in filling out form field values. Refer to this page on MDN for available values. Defaults to . Type string | |
| \`autocorrect\` autocorrect | \`"off"\` Indicates whether the browser's autocorrect feature is on or off. When set as an attribute, use or "on". When set as a property, use true or false. Type boolean | |
| \`defaultValue\` value | \`string \\| null\` The default value of the form control as a delimiter-separated string. Primarily used for resetting the form control. Type | |
| \`delimiter\` delimiter | \`",;"\` The characters that turn typed text into a tag. Each character is a separate delimiter, so accepts both commas and semicolons. Pasted text is split on the same characters. Set to an empty string so only Enter adds a tag. Also used to parse the value attribute, which falls back to a comma when the delimiter is empty. Type string Default ',' | |
| \`disabled\` disabled | \`boolean\` Disables the form control. Type Default false | |
| \`enterkeyhint\` enterkeyhint | \`'enter' \\| 'done' \\| 'go' \\| 'next' \\| 'previous' \\| 'search' \\| 'send'\` Used to customize the label or icon of the Enter key on virtual keyboards. Type | |
| \`form\` | \`

\` By default, form controls are associated with the nearest containing element. This attribute allows you to place the form control outside of a form and associate it with the form that has this id. The form must be in the same document or shadow root for this to work. Type HTMLFormElement \\| null | |
| \`hint\` hint | \`hint\` The tag input's . If you need to display HTML, use the hint slot instead. Type string Default '' | |
| \`inputmode\` inputmode | \`'none' \\| 'text' \\| 'decimal' \\| 'numeric' \\| 'tel' \\| 'search' \\| 'email' \\| 'url'\` Tells the browser what type of data will be entered by the user, allowing it to display the appropriate virtual keyboard on supportive devices. Type | |
| \`inputValue\` | \`string\` The text currently typed in the text box that hasn't become a tag yet. Type Default '' | |
| \`label\` label | \`label\` The tag input's . If you need to display HTML, use the label slot instead. Type string Default '' | |
| \`maxTags\` max-tags | \`number\` The maximum of tags that can be added. Once reached, no more tags can be added until one is removed. Type number | |
| \`minTags\` min-tags | \`number\` The minimum of tags required for the control to be valid. Has no effect when there are no tags. Type number | |
| \`name\` name | \`string \\| null\` The name of the input, submitted as a name/value pair with form data. Type Default null | |
| \`pill\` pill | \`boolean\` Draws a pill-style tag input, and pill-style tags, with rounded edges. Type Default false | |
| \`placeholder\` placeholder | \`string\` Placeholder text to show in the text box. Hidden once the maximum number of tags is reached. Type Default '' | |
| \`readonly\` readonly | \`boolean\` Makes the tag input readonly. Tags stay visible and are still submitted, but can't be added or removed. Type Default false | |
| \`required\` required | \`boolean\` Makes the tag input a required field, so at least one tag must be added. Type Default false | |
| \`size\` size | \`'xs' \\| 's' \\| 'm' \\| 'l' \\| 'xl' \\| 'small' \\| 'medium' \\| 'large'\` The tag input's size. Also applied to each tag. Type Default 'm' | |
| \`spellcheck\` spellcheck | \`boolean\` Enables spell checking on the text box. Type Default true | |
| \`validationTarget\` | \`undefined \\| HTMLElement\` Override this to change where constraint validation popups are anchored. Type | |
| \`validators\` | \`observedAttributes\` Validators are static because they have , essentially attributes to "watch" for changes. Whenever these attributes change, we want to be notified and update the validator. Type Validator\[\] Default \[\] | |
| \`value\` | \`name\` The tags as an array of strings, submitted as one entry per tag under . Set the value attribute to a delimiter-separated string for an initial value. Type string\[\] | |
| \`withClear\` with-clear | \`boolean\` Adds a clear button that removes all tags. Type Default false | |
| \`withHint\` with-hint | \`true\` Only required for SSR. Set to if you're slotting in a hint element so the server-rendered markup includes the hint before the component hydrates on the client. Type boolean Default false | |
| \`withLabel\` with-label | \`true\` Only required for SSR. Set to if you're slotting in a label element so the server-rendered markup includes the label before the component hydrates on the client. Type boolean Default false | |

### Methods

| Name | Description | Arguments |
| --- | --- | --- |
| \`blur()\` | Removes focus from the text box. | |
| \`focus()\` | Sets focus on the text box. | \`options: FocusOptions\` |
| \`formStateRestoreCallback()\` | Called when the browser is trying to restore element’s state to state in which case reason is "restore", or when the browser is trying to fulfill autofill on behalf of user in which case reason is "autocomplete". In the case of "restore", state is a string, File, or FormData object previously set as the second argument to setFormValue. | \`state: string \\| File \\| FormData \\| null, reason: 'autocomplete' \\| 'restore'\` |
| \`resetValidity()\` | Reset validity is a way of removing manual custom errors and native validation. | |
| \`setCustomValidity()\` | Do not use this when creating a "Validator". This is intended for end users of components. We track manually defined custom errors so we don't clear them on accident in our validators. | \`message: string\` |

### Events

| Name | Description |
| --- | --- |
| \`blur\` | Emitted when the control loses focus. |
| \`change\` | Emitted when a tag is added, removed, or all tags are cleared by the user. |
| \`focus\` | Emitted when the control gains focus. |
| \`input\` | Emitted when the user types in the text box or when a tag is added or removed. |
| \`wa-clear\` | Emitted when the clear button is activated. |
| \`wa-create\` | \`event.preventDefault()\` Emitted before typed text becomes a tag. Call to reject it. The event detail contains { inputValue: string }, the text that would become the tag. |
| \`wa-invalid\` | Emitted when the form control has been checked for validity and its constraints aren't satisfied. |

### Custom States

| Name | Description | CSS selector |
| --- | --- | --- |
| \`blank\` | The tag input has no tags. | \`:state(blank)\` |
| \`readonly\` | The tag input is readonly. | \`:state(readonly)\` |

### CSS Parts

| Name | Description | CSS selector |
| --- | --- | --- |
| \`clear-button\` | The clear button. | \`::part(clear-button)\` |
| \`end\` | \`end\` The container that wraps the slot. | \`::part(end)\` |
| \`form-control-label\` | The label. | \`::part(form-control-label)\` |
| \`hint\` | The hint's wrapper. | \`::part(hint)\` |
| \`input\` | \`\` The internal text box, an element. | \`::part(input)\` |
| \`start\` | \`start\` The container that wraps the slot. | \`::part(start)\` |
| \`tag\` | \`\` Each tag, a . | \`::part(tag)\` |
| \`tag\_\_content\` | The tag's content part. | \`::part(tag\_\_content)\` |
| \`tag\_\_remove-button\` | The tag's remove button. | \`::part(tag\_\_remove-button)\` |
| \`tag\_\_remove-button\_\_base\` | The tag's remove button base part. | \`::part(tag\_\_remove-button\_\_base)\` |
| \`tag-input\` | The component's outer wrapper, the bordered box that holds the tags and text box. | \`::part(tag-input)\` |
| \`tags\` | The list that holds the tags. | \`::part(tags)\` |

### Dependencies

This component automatically imports the following elements. Sub-dependencies, if any exist, will also be included in this list.

-   [`<wa-button>`](https://webawesome.com/docs/components/button)
-   [`<wa-icon>`](https://webawesome.com/docs/components/icon)
-   [`<wa-spinner>`](https://webawesome.com/docs/components/spinner)
-   [`<wa-tag>`](https://webawesome.com/docs/components/tag)

## Examples

### Label

Use the `label` attribute to give the tag input an accessible label. For labels that contain HTML, use the `label` slot instead.

```html
<wa-tag-input label="Skills"></wa-tag-input>
```

### Hint

Add a descriptive hint with the `hint` attribute. For hints that contain HTML, use the `hint` slot instead.

```html
<wa-tag-input label="Ingredients" hint="Press Enter or type a comma after each ingredient."></wa-tag-input>
```

### Placeholder

Use the `placeholder` attribute to show prompt text in the text box. The placeholder is hidden once the maximum number of tags is reached.

```html
<wa-tag-input label="Guest list" placeholder="Add a name"></wa-tag-input>
```

### Initial Value

Use the `value` attribute to start with a list of tags. Separate each tag with the delimiter, a comma by default.

```html
<wa-tag-input label="Toppings" value="Mushrooms, Olives, Peppers"></wa-tag-input>
```

Framework users can bind directly to the `value` property, an array of strings.

### Delimiter

Use the `delimiter` attribute to change which characters turn typed text into a tag. Each character in the string is a separate delimiter, and pasted text is split on the same characters. Set it to an empty string so only Enter adds a tag.

Text left in the text box becomes a tag when the tag input loses focus. Text that can't become a tag is discarded.

```html
<div class="wa-stack">
  <wa-tag-input label="Space-separated" delimiter=" " placeholder="Type a word and a space"></wa-tag-input>
  <wa-tag-input label="Commas or semicolons" delimiter=",;" placeholder="Type a value and , or ;"></wa-tag-input>
  <wa-tag-input label="Enter only" delimiter="" placeholder="Type a value and press Enter"></wa-tag-input>
</div>
```

### Pasting

Pasting delimiter-separated text adds a tag for each value in one step. The same rules apply as when typing, so values that can't become tags, such as duplicates and anything past `max-tags`, stay in the text box instead of being lost. Pasted text without a delimiter is inserted as ordinary text.

```html
<wa-copy-button value="Cumin, Paprika, Coriander, Turmeric">
  <wa-button appearance="filled">
    <wa-icon slot="start" name="clipboard"></wa-icon>
    Copy spices
  </wa-button>
</wa-copy-button>

<wa-divider></wa-divider>

<wa-tag-input label="Spices" placeholder="Paste the copied list here"></wa-tag-input>
```

### Clearable

Add the `with-clear` attribute to show a button that removes every tag at once. The button only appears once there is at least one tag.

```html
<wa-tag-input label="Tickers" value="AAPL, MSFT, NVDA" with-clear></wa-tag-input>
```

### Max Tags

Use the `max-tags` attribute to cap the number of tags. Once the limit is reached, no more tags can be added until one is removed.

```html
<wa-tag-input
  label="Desert island albums"
  hint="Choose up to three."
  value="Kind of Blue, Rumours"
  max-tags="3"
  placeholder="Add an album"
></wa-tag-input>
```

### Allowing Duplicates

Duplicate tags are ignored by default. Add the `allow-duplicates` attribute to let the same value appear more than once.

```html
<wa-tag-input label="Dice rolls" value="6, 6" allow-duplicates placeholder="Roll again"></wa-tag-input>
```

### Appearance

Use the `appearance` attribute to change the tag input's visual style.

```html
<div class="wa-stack">
  <wa-tag-input appearance="outlined" value="Outlined" label="Outlined"></wa-tag-input>
  <wa-tag-input appearance="filled" value="Filled" label="Filled"></wa-tag-input>
  <wa-tag-input appearance="filled-outlined" value="Filled outlined" label="Filled outlined"></wa-tag-input>
</div>
```

### Pill

Use the `pill` attribute to give the tag input and its tags rounded edges.

```html
<wa-tag-input label="Interests" value="Hiking, Chess" pill></wa-tag-input>
```

### Size

Use the `size` attribute to change the tag input's size. The tags scale with it.

```html
<div class="wa-stack">
  <wa-tag-input size="xs" label="Extra small" value="Extra small"></wa-tag-input>
  <wa-tag-input size="s" label="Small" value="Small"></wa-tag-input>
  <wa-tag-input size="m" label="Medium" value="Medium"></wa-tag-input>
  <wa-tag-input size="l" label="Large" value="Large"></wa-tag-input>
  <wa-tag-input size="xl" label="Extra large" value="Extra large"></wa-tag-input>
</div>
```

### Disabled

Use the `disabled` attribute to disable a tag input.

```html
<wa-tag-input label="Assignees" value="Ada, Grace" disabled></wa-tag-input>
```

### Readonly

Use the `readonly` attribute to show tags that can't be changed. Unlike `disabled`, a readonly tag input stays focusable and its value is still submitted with the form.

```html
<wa-tag-input label="Roles" value="Owner, Maintainer" readonly></wa-tag-input>
```

### Start & End Decorations

Use the `start` and `end` slots to add presentational elements such as [`<wa-icon>`](https://webawesome.com/docs/components/icon) inside the tag input.

```html
<div class="wa-stack">
  <wa-tag-input label="Recipients" placeholder="Add an email">
    <wa-icon slot="start" name="envelope"></wa-icon>
  </wa-tag-input>
  <wa-tag-input label="Keywords" placeholder="Add a keyword">
    <wa-icon slot="start" name="tag"></wa-icon>
    <wa-icon slot="end" name="circle-info"></wa-icon>
  </wa-tag-input>
</div>
```

### Validation

Add the `required` attribute to require at least one tag. Use the `min-tags` and `max-tags` attributes to validate the number of tags. `min-tags` only applies once there is at least one tag, so pair it with `required` to make tags mandatory. `max-tags` also prevents adding more.

```html
<form class="tag-input-validation">
  <wa-tag-input
    name="tags"
    label="Tags"
    hint="Add between two and five tags."
    min-tags="2"
    max-tags="5"
    required
  ></wa-tag-input>
  <br />
  <wa-button appearance="filled" type="submit">Submit</wa-button>
  <wa-button type="reset">Reset</wa-button>
</form>

<script type="module">
  const form = document.querySelector('.tag-input-validation');

  form.addEventListener('submit', event => {
    event.preventDefault();
    alert(`Submitted: ${new FormData(form).getAll('tags').join(', ')}`);
  });
</script>
```

### Custom Validity

Use the `setCustomValidity()` method to set a custom validation message. This will prevent the form from submitting and make the browser display the error message you provide. To clear the error, call this function with an empty string.

```html
<form class="tag-input-custom-validity">
  <wa-tag-input
    name="emails"
    label="Invite"
    hint="Every tag must be an email address."
    placeholder="name@example.com"
  ></wa-tag-input>
  <br />
  <wa-button appearance="filled" type="submit">Send invites</wa-button>
</form>

<script type="module">
  const form = document.querySelector('.tag-input-custom-validity');
  const tagInput = form.querySelector('wa-tag-input');

  tagInput.addEventListener('change', () => {
    const invalid = tagInput.value.filter(tag => !tag.includes('@'));
    tagInput.setCustomValidity(invalid.length ? `Not an email address: ${invalid.join(', ')}` : '');
  });

  form.addEventListener('submit', event => {
    event.preventDefault();
    alert('Invites sent');
  });
</script>
```

### Rejecting Tags

The `wa-create` event fires before typed text becomes a tag. Call `event.preventDefault()` to reject it, for example to enforce a format.

```html
<wa-tag-input
  class="tag-input-reject"
  label="Usernames"
  hint="Letters, numbers, and underscores only."
  placeholder="Add a username"
></wa-tag-input>

<script type="module">
  const tagInput = document.querySelector('.tag-input-reject');

  tagInput.addEventListener('wa-create', event => {
    if (!/^\w+$/.test(event.detail.inputValue)) {
      event.preventDefault();
    }
  });
</script>
```

**Tell people why a tag was rejected.**  
Rejecting a tag produces no message of its own. Update the `hint` or call `setCustomValidity()` from your listener so the reason reaches screen readers too.

### Reacting to Changes

Listen for the `change` event to respond when a tag is added or removed. The `value` property holds the current list.

```html
<div class="tag-input-changes">
  <wa-tag-input label="Labels" value="bug, help wanted"></wa-tag-input>
  <p>Labels: <code class="output">bug, help wanted</code></p>
</div>

<script type="module">
  const container = document.querySelector('.tag-input-changes');
  const tagInput = container.querySelector('wa-tag-input');
  const output = container.querySelector('.output');

  tagInput.addEventListener('change', () => {
    output.textContent = tagInput.value.join(', ') || '(none)';
  });
</script>
```

### Customizing

Use [CSS parts](#css-parts) to style the tags and the text box.

```html
<wa-tag-input class="tag-input-styled" label="Genres" value="Jazz, Ambient, Techno"></wa-tag-input>

<style>
  .tag-input-styled::part(tag) {
    background-color: var(--wa-color-brand-fill-quiet);
    border-color: var(--wa-color-brand-border-quiet);
    color: var(--wa-color-brand-on-quiet);
  }

  .tag-input-styled::part(tag__remove-button) {
    color: var(--wa-color-brand-on-quiet);
  }
</style>
```
