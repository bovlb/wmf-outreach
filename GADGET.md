# MediaWiki Gadget Integration

This document explains how to install and use the Outreach Dashboard Course Staff gadget.

## What Does the Gadget Do?

The gadget adds a **"Course staff"** tab to user-related pages (User pages, User talk pages, Special:Contributions, Special:DeletedContributions). This tab only appears when the user is currently enrolled in an active Outreach Dashboard course.

When clicked, the tab shows:
- All currently active courses the user is enrolled in
- Staff members for each course (instructors and teaching assistants)
- Links to course pages on the Outreach Dashboard
- Links to staff member talk pages
- A "Copy ping template" button that copies `{{ping|Staff1}} {{ping|Staff2}}` to your clipboard

## Installation

### Option 1: Local Testing

1. **Start the service:**
   ```bash
   cd wmf-outreach
   uvicorn app.main:app --reload
   ```

2. **Create a test HTML page** that loads the gadget:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>Gadget Test Page</title>
       <script>
           // Mock MediaWiki environment
           window.mw = {
               config: {
                   values: {
                       'wgNamespaceNumber': 2,
                       'wgTitle': 'TestUser',
                       'wgRelevantUserName': 'TestUser',
                       'wgPageName': 'User:TestUser'
                   },
                   get: function(key) { return this.values[key]; }
               },
               util: {
                   addPortletLink: function(portlet, url, text, id, tooltip) {
                       console.log('Adding tab:', { portlet, url, text, id, tooltip });
                       const nav = document.getElementById('p-views') || document.body;
                       const link = document.createElement('a');
                       link.href = url;
                       link.textContent = text;
                       link.id = id;
                       link.title = tooltip;
                       link.style.marginRight = '10px';
                       nav.appendChild(link);
                   }
               },
               loader: {
                   using: function(modules) {
                       return Promise.resolve();
                   }
               }
           };
       </script>
   </head>
   <body>
       <div id="p-views" style="padding: 20px; background: #f8f9fa; border-bottom: 1px solid #a2a9b1;">
           <strong>Tabs:</strong>
       </div>
       <h1>User:TestUser</h1>
       <p>This is a test page to verify the gadget works.</p>
       
       <script src="http://localhost:8000/gadget/outreach-staff-gadget.js"></script>
   </body>
   </html>
   ```

3. **Open the test page** in your browser. If TestUser has active courses, you should see a "Course staff" tab appear.

### Option 2: MediaWiki Installation

#### As a Gadget

1. **Create the gadget definition** on your wiki at `MediaWiki:Gadgets-definition`:
   ```
   * outreach-staff[ResourceLoader|default]|outreach-staff.js
   ```

2. **Create the gadget page** at `MediaWiki:Gadget-outreach-staff.js`:
   - Copy the contents of `static/outreach-staff-gadget.js`
   - **Update the `API_BASE` constant** to point to your deployed service:
     ```javascript
     const API_BASE = 'https://YOUR-TOOL.toolforge.org';
     ```

3. The gadget will now be enabled by default for all users.

#### In Your common.js

Alternatively, add to your `User:YourName/common.js`:
```javascript
mw.loader.load('https://YOUR-TOOL.toolforge.org/gadget/outreach-staff-gadget.js');
```

## Configuration

### API Base URL

The gadget needs to know where your service is running. Edit the `API_BASE` constant in the JavaScript file:

```javascript
// For local testing
const API_BASE = 'http://localhost:8000';

// For Toolforge deployment
const API_BASE = 'https://outreach-dashboard-helper.toolforge.org';

// For custom deployment
const API_BASE = 'https://your-domain.example.com';
```

### Active Status Mode

By default, the gadget uses **activity tracking dates** (the broader window from `start` to `end`). If you want to use the narrower **event dates** instead (`timeline_start` to `timeline_end`), modify the API call:

```javascript
// In hasActiveStaff() function, change:
const apiUrl = `${API_BASE}/api/users/${encodeURIComponent(username)}/active-staff`;

// To:
const apiUrl = `${API_BASE}/api/users/${encodeURIComponent(username)}/active-staff?use_event_dates=true`;
```

See [ACTIVE_STATUS_SPLIT.md](ACTIVE_STATUS_SPLIT.md) for details on the difference.

## Testing

### Test Checklist

- [ ] Tab appears on `User:Username` pages
- [ ] Tab appears on `User_talk:Username` pages
- [ ] Tab appears on `Special:Contributions/Username` pages
- [ ] Tab appears on `Special:DeletedContributions/Username` pages
- [ ] Tab does NOT appear for users with no active courses
- [ ] Tab does NOT appear on article pages, talk pages (non-user), etc.
- [ ] Tab does NOT appear twice (no duplicates)
- [ ] Clicking tab opens course-staff.html page
- [ ] Course-staff.html shows correct course information
- [ ] Links to Outreach Dashboard work
- [ ] Links to user talk pages work
- [ ] "Copy ping template" button works
- [ ] Clipboard contains correct `{{ping|...}}` syntax

### Test Users

To test the gadget, you need usernames that appear in the Outreach Dashboard with active courses. You can:

1. **Query the API directly** to find test users:
   ```bash
   # Get a user's active staff (will return 200 only if they have active courses)
   curl http://localhost:8000/api/users/TestUser/active-staff
   ```

2. **Use the enrichment endpoint** to check if a user has active courses:
   ```bash
   curl http://localhost:8000/api/users/TestUser?enrich=true
   ```

3. **Create test data** in your local development environment (see [QUICKSTART.md](QUICKSTART.md) for mock data setup).

## Troubleshooting

### Tab doesn't appear

1. **Check browser console** for JavaScript errors
2. **Verify the API is running** by visiting the service URL in your browser
3. **Check CORS** - the service must allow requests from your wiki domain
4. **Verify username detection** - check console logs to see what username is being extracted
5. **Test the API directly** - visit the `/active-staff` endpoint for your test user

### CORS errors

If you see CORS errors in the browser console:

1. **For local testing**, the service already allows all origins (`allow_origins=["*"]`)
2. **For production**, update `app/main.py` to allow your wiki domain:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://www.wikidata.org",
           "https://www.mediawiki.org",
           # Add your wiki domains
       ],
       allow_credentials=True,
       allow_methods=["GET"],
       allow_headers=["*"],
   )
   ```

### Wrong username detected

The gadget uses this priority for username detection:
1. `mw.config.get('wgRelevantUserName')`
2. `mw.config.get('wgTitle')` for User/User talk pages
3. URL parameter `target` or `user` for Special pages
4. Path extraction for Special:Contributions/Username format

Check the browser console to see what username is being used.

## Deployment

### Toolforge Deployment

When deploying to Toolforge, the static files are served from the same domain as the API:

```
https://YOUR-TOOL.toolforge.org/gadget/outreach-staff-gadget.js
https://YOUR-TOOL.toolforge.org/gadget/course-staff.html
```

Update your gadget code to use this URL, then follow the [DEPLOYMENT.md](DEPLOYMENT.md) guide.

### CDN / Separate Static Hosting

If you want to serve the JavaScript from a CDN:

1. Upload `static/outreach-staff-gadget.js` to your CDN
2. Update the `API_BASE` constant to point to your API server
3. Load the CDN URL in your MediaWiki gadget definition

The HTML interface (`course-staff.html`) must be served from the same domain as your API due to CORS restrictions.

## Customization

### Changing Tab Text

Edit the `linkText` variable in `addCourseStaffTab()`:
```javascript
const linkText = 'Course staff';  // Change to your preferred text
```

### Changing Tab Position

The gadget tries to add the tab to `p-views` (next to Read, Edit, History). To change this:

```javascript
// Add to toolbox instead
const portlet = 'p-tb';

// Add to a specific position (after a certain tab)
const before = '#ca-history';  // Change to your preferred anchor
```

### Custom Styling

The `course-staff.html` page includes embedded CSS. You can customize colors, fonts, and layout by editing the `<style>` section.

## See Also

- [API_EXAMPLES.md](API_EXAMPLES.md) - API usage examples
- [ACTIVE_STAFF.md](ACTIVE_STAFF.md) - Details on the active-staff endpoint
- [ENRICHMENT.md](ENRICHMENT.md) - Course enrichment documentation
- [gadget_optional_tab.md](gadget_optional_tab.md) - General MediaWiki gadget tab guide
