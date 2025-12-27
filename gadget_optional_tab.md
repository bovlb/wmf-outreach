# MediaWiki gadget: optionally add a tab on User / User talk / Contributions / Deleted contributions

This describes a **client-side MediaWiki gadget** that **adds a new tab (a “view” link)** only on:

- **User pages** (`NS_USER`, namespace 2)
- **User talk pages** (`NS_USER_TALK`, namespace 3)
- **Special:Contributions/<user>**
- **Special:DeletedContributions/<user>** (or similar “deleted contributions” special page names, depending on wiki config)

…and only when your gadget decides the tab is relevant (e.g., your Toolforge backend says there’s data for that user).

---

## 1) Prereqs: how gadgets are loaded

### Gadget definition (site-wide)
On a wiki where you have interface-admin rights:

1. Put the JS in a gadget page, e.g.:
   - `MediaWiki:Gadget-MyTool-tab.js`

2. Register it in `MediaWiki:Gadgets-definition`:
   ```text
   * MyToolTab[ResourceLoader|default|dependencies=mediawiki.util,mediawiki.api]|MyTool-tab.js
   ```

### Per-user enablement (for testing)
If you don’t want to register a gadget yet, you can test by loading it from your common.js:
```js
mw.loader.load( mw.util.getUrl('MediaWiki:Gadget-MyTool-tab.js', { action: 'raw', ctype: 'text/javascript' }) );
```

---

## 2) What “adding a tab” means in MediaWiki

The tabs you see at the top (“Read”, “Edit”, “View history”, etc.) are typically links in the **`p-views` portlet**.

The simplest cross-skin way to add one is:

```js
mw.util.addPortletLink(
  'p-views',          // portlet id
  url,                // link target
  'My Tab',           // link text
  'ca-mytool',        // id (must be unique)
  'Tooltip text',     // tooltip
  null,               // accesskey
  '#ca-history'       // insert before this tab if present
);
```

Notes:
- `ca-*` ids match core tab ids; you can choose your own like `ca-mytool`.
- `#ca-history` is a decent insertion point when it exists; otherwise it appends.

---

## 3) Detecting which kind of page you’re on

### A) User / User talk pages
Use `wgNamespaceNumber`:

- User: `wgNamespaceNumber === 2`
- User talk: `wgNamespaceNumber === 3`

Target username usually comes from the title:
- `mw.config.get('wgTitle')` (page title without namespace)
- or `mw.config.get('wgRelevantUserName')` (often set on user-related pages)

### B) Special:Contributions
Use `wgCanonicalSpecialPageName`:

- `mw.config.get('wgCanonicalSpecialPageName') === 'Contributions'`

Then get the target user:
- Prefer `wgRelevantUserName` if present
- Otherwise parse it from the URL (see below)

### C) Special:DeletedContributions
On many wikis this is:
- `wgCanonicalSpecialPageName === 'DeletedContributions'`

But you should not assume the name is identical everywhere (extensions / config can vary). Treat it as:
- check canonical name if present
- otherwise match `wgPageName` prefix like `Special:DeletedContributions`

---

## 4) Getting the target username robustly

You want a function that returns the “subject user” **or null**.

```js
function getTargetUsername() {
  const ns = mw.config.get('wgNamespaceNumber');
  const special = mw.config.get('wgCanonicalSpecialPageName');
  const relevant = mw.config.get('wgRelevantUserName');

  if (relevant) return relevant;

  // User / User talk pages: title is the username
  if (ns === 2 || ns === 3) {
    return mw.config.get('wgTitle'); // typically the username
  }

  // Special pages: parse 'target' param if present (Contributions uses it)
  if (special === 'Contributions' || special === 'DeletedContributions') {
    const params = new URLSearchParams(location.search);
    const target = params.get('target') || params.get('user');
    if (target) return target;

    // Some wikis put the username in the path after Special:Contributions/
    // Example: /wiki/Special:Contributions/Foo
    const pageName = mw.config.get('wgPageName') || '';
    // pageName is like "Special:Contributions/Foo"
    const m = pageName.match(/^Special:(?:Contributions|DeletedContributions)\\/(.+)$/);
    if (m) return decodeURIComponent(m[1]).replace(/_/g, ' ');
  }

  return null;
}
```

Caveats:
- Users can be IPs; treat them as strings.
- Usernames can contain spaces; MediaWiki often uses underscores in URLs.

---

## 5) Decide when to show the tab (the “optional” part)

Typical pattern:

1. Detect page type + username.
2. Query your Toolforge backend for “does this user have data?”
3. Only then add the tab.

### Backend endpoint suggestion
Have a cheap endpoint like:

- `GET https://<tool>.toolforge.org/api/user/has_data?username=...`
- Response:
  ```json
  { "username": "Foo", "has_data": true, "url": "https://<tool>.toolforge.org/user/Foo" }
  ```

This avoids doing heavier fetches just to decide whether to show a tab.

### Gadget fetch logic
```js
async function hasDataForUser(username) {
  const apiUrl = 'https://YOURTOOL.toolforge.org/api/user/has_data?username=' +
                 encodeURIComponent(username);

  const resp = await fetch(apiUrl, { credentials: 'omit' });
  if (!resp.ok) return { hasData: false };

  const json = await resp.json();
  return { hasData: !!json.has_data, url: json.url };
}
```

**CORS:** If your Toolforge endpoint is on a different origin, you must send appropriate CORS headers from the backend (at minimum `Access-Control-Allow-Origin` for the wiki origin(s) you care about).

---

## 6) Add the tab

```js
function addMyToolTab(url, username) {
  const linkText = 'MyTool';
  const tooltip = 'Open MyTool for ' + username;

  // Make sure p-views exists; if not, fall back to a toolbox link.
  const portlet = document.getElementById('p-views') ? 'p-views' : 'p-tb';
  const before = document.querySelector('#ca-history') ? '#ca-history' : null;

  mw.util.addPortletLink(
    portlet,
    url,
    linkText,
    'ca-mytool',
    tooltip,
    null,
    before
  );
}
```

---

## 7) Full example gadget (drop-in)

Create `MediaWiki:Gadget-MyTool-tab.js` with something like:

```js
/* global mw */
(function () {
  'use strict';

  function isRelevantPage() {
    const ns = mw.config.get('wgNamespaceNumber');
    const special = mw.config.get('wgCanonicalSpecialPageName');
    const pageName = mw.config.get('wgPageName') || '';

    if (ns === 2 || ns === 3) return true; // User / User talk
    if (special === 'Contributions' || special === 'DeletedContributions') return true;

    // fallback if canonical name isn't available / consistent
    if (/^Special:(Contributions|DeletedContributions)\\b/.test(pageName)) return true;

    return false;
  }

  function getTargetUsername() {
    const ns = mw.config.get('wgNamespaceNumber');
    const special = mw.config.get('wgCanonicalSpecialPageName');
    const relevant = mw.config.get('wgRelevantUserName');

    if (relevant) return relevant;

    if (ns === 2 || ns === 3) return mw.config.get('wgTitle');

    if (special === 'Contributions' || special === 'DeletedContributions') {
      const params = new URLSearchParams(location.search);
      const target = params.get('target') || params.get('user');
      if (target) return target;

      const pageName = mw.config.get('wgPageName') || '';
      const m = pageName.match(/^Special:(?:Contributions|DeletedContributions)\\/(.+)$/);
      if (m) return decodeURIComponent(m[1]).replace(/_/g, ' ');
    }

    return null;
  }

  async function hasDataForUser(username) {
    const apiUrl = 'https://YOURTOOL.toolforge.org/api/user/has_data?username=' +
                   encodeURIComponent(username);

    try {
      const resp = await fetch(apiUrl, { credentials: 'omit' });
      if (!resp.ok) return { hasData: false };
      const json = await resp.json();
      return { hasData: !!json.has_data, url: json.url };
    } catch (e) {
      return { hasData: false };
    }
  }

  function addMyToolTab(url, username) {
    const linkText = 'MyTool';
    const tooltip = 'Open MyTool for ' + username;

    const portlet = document.getElementById('p-views') ? 'p-views' : 'p-tb';
    const before = document.querySelector('#ca-history') ? '#ca-history' : null;

    mw.util.addPortletLink(
      portlet,
      url,
      linkText,
      'ca-mytool',
      tooltip,
      null,
      before
    );
  }

  mw.loader.using(['mediawiki.util']).then(async function () {
    if (!isRelevantPage()) return;

    const username = getTargetUsername();
    if (!username) return;

    // Avoid adding duplicates if gadget is loaded twice
    if (document.getElementById('ca-mytool')) return;

    const { hasData, url } = await hasDataForUser(username);
    if (!hasData || !url) return;

    addMyToolTab(url, username);
  });
})();
```

---

## 8) Practical notes (things that bite people)

- **Don’t block page render.** Do the backend check async; the tab can appear a moment later.
- **Cache on the backend.** Gadgets can create a lot of traffic fast.
- **Be careful with usernames.** They can be IPs, can contain spaces, and can be hidden in some contexts.
- **Deleted contributions access.** Users may not have rights to see deleted contributions; still safe to add the tab, but your tool page should handle “no access” gracefully.
- **Skin differences.** `p-views` usually exists, but not always. Falling back to `p-tb` (toolbox) is a good pragmatic fallback.

---

## 9) Optional: add a “disabled” tab instead of hiding it

If you want users to discover the tool even when no data exists, you can always add the tab but style it disabled and open a help page. That’s a product decision, not a technical one.

---

## 10) Testing checklist

- User page: `User:Example`
- User talk: `User talk:Example`
- Contributions: `Special:Contributions/Example` and `Special:Contributions?target=Example`
- Deleted contributions: `Special:DeletedContributions/Example` and `... ?target=Example`
- IP user targets (e.g. `Special:Contributions/127.0.0.1`)
- Confirm no duplicate tab appears when you refresh or when gadget is loaded twice.
"""

path = "/mnt/data/gadget_optional_tab.md"
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

path