/**
 * Outreach Dashboard Course Staff Gadget
 * 
 * Adds an "Outreach" tab to user-related pages for users who are participants
 * in currently active Outreach Dashboard courses. Clicking the tab displays
 * staff information inline on the page.
 * 
 * Usage: Install as a MediaWiki gadget or load from your common.js
 */
/* global mw, $ */
(function () {
  'use strict';

  // Configuration - UPDATE THIS with your service URL
//   const API_BASE = 'http://localhost:8000'; // For local testing
  const API_BASE = 'https://outreach.toolforge.org'; // For production

  const OUTREACH_BASE = 'https://outreachdashboard.wmflabs.org';

  /**
   * Check if the current page is a user-related page where we should show the tab.
   */
  function isRelevantPage() {
    const ns = mw.config.get('wgNamespaceNumber');
    const special = mw.config.get('wgCanonicalSpecialPageName');
    const pageName = mw.config.get('wgPageName') || '';

    // User or User talk pages
    if (ns === 2 || ns === 3) return true;

    // Special:Contributions
    if (special === 'Contributions' || special === 'DeletedContributions') return true;

    // Fallback for wikis with different special page configurations
    if (/^Special:(Contributions|DeletedContributions)\b/.test(pageName)) return true;

    return false;
  }

  /**
   * Extract the username from the current page.
   */
  function getTargetUsername() {
    const ns = mw.config.get('wgNamespaceNumber');
    const special = mw.config.get('wgCanonicalSpecialPageName');
    const relevant = mw.config.get('wgRelevantUserName');

    // Prefer wgRelevantUserName if available
    if (relevant) return relevant;

    // User/User talk pages: title is the username
    if (ns === 2 || ns === 3) {
      return mw.config.get('wgTitle');
    }

    // Special pages: try to extract from URL
    if (special === 'Contributions' || special === 'DeletedContributions') {
      const params = new URLSearchParams(location.search);
      const target = params.get('target') || params.get('user');
      if (target) return target;

      // Try to extract from path (e.g., Special:Contributions/Username)
      const pageName = mw.config.get('wgPageName') || '';
      const match = pageName.match(/^Special:(?:Contributions|DeletedContributions)\/(.+)$/);
      if (match) {
        return decodeURIComponent(match[1]).replace(/_/g, ' ');
      }
    }

    return null;
  }

  /**
   * Fetch course staff data for the user.
   */
  async function fetchCourseStaff(username) {
    const [staffResp, userResp] = await Promise.all([
      fetch(`${API_BASE}/api/users/${encodeURIComponent(username)}/active-staff`, { credentials: 'omit' }),
      fetch(`${API_BASE}/api/users/${encodeURIComponent(username)}?enrich=true`, { credentials: 'omit' })
    ]);

    if (!staffResp.ok) return null;

    const staffData = await staffResp.json();
    const userData = userResp.ok ? await userResp.json() : null;

    if (!staffData.all_staff || staffData.all_staff.length === 0) {
      return null;
    }

    return { staffData, userData };
  }

  /**
   * Render the full outreach page content.
   */
  function renderOutreachPage(staffData, userData) {
    const wikiBase = window.location.origin;
    
    // Create a map of course slugs to enriched course data
    const courseMap = new Map();
    if (userData && userData.courses) {
      userData.courses.forEach(course => {
        courseMap.set(course.course_slug, course);
      });
    }
    
    // Sort courses
    const sortedCourses = [...staffData.courses].sort((a, b) => {
      const enrichedA = courseMap.get(a.course_slug);
      const enrichedB = courseMap.get(b.course_slug);
      
      const activeEventA = enrichedA?.active_event ? 1 : 0;
      const activeEventB = enrichedB?.active_event ? 1 : 0;
      if (activeEventA !== activeEventB) {
        return activeEventB - activeEventA;
      }
      
      const activeTrackingA = enrichedA?.active_tracking ? 1 : 0;
      const activeTrackingB = enrichedB?.active_tracking ? 1 : 0;
      if (activeTrackingA !== activeTrackingB) {
        return activeTrackingB - activeTrackingA;
      }
      
      const dateA = enrichedA?.timeline_end || enrichedA?.end || '';
      const dateB = enrichedB?.timeline_end || enrichedB?.end || '';
      
      if (dateA && dateB) {
        return dateB.localeCompare(dateA);
      }
      
      if (dateA && !dateB) return -1;
      if (!dateA && dateB) return 1;
      
      return a.course_title.localeCompare(b.course_title);
    });
    
    // Build HTML
    let html = '<div class="mw-outreach-page"><div class="mw-outreach-section">';
    
    // Summary sentence
    html += `<p><strong>${sortedCourses.length}</strong> active course(s) with <strong>${staffData.all_staff.length}</strong> staff member(s).</p>`;
    
    // Actions
    html += `
      <p class="mw-outreach-actions">
        <button class="mw-outreach-copy-btn" data-all-staff='${JSON.stringify(staffData.all_staff)}'>Copy ping template</button>
        <a href="${OUTREACH_BASE}/users/${encodeURIComponent(staffData.username)}" target="_blank" rel="noopener">View on Outreach Dashboard</a>
      </p>
    `;
    
    // List courses
    sortedCourses.forEach(course => {
      const courseUrl = `${OUTREACH_BASE}/courses/${course.course_slug}`;
      const studentsUrl = `${courseUrl}/students/overview`;
      const enrichedCourse = courseMap.get(course.course_slug);
      
      let statusBadge = '';
      if (enrichedCourse) {
        if (enrichedCourse.active_event) {
          statusBadge = '<span class="mw-outreach-badge mw-outreach-active" title="Event is currently happening">● Active</span>';
        } else if (enrichedCourse.active_tracking) {
          statusBadge = '<span class="mw-outreach-badge mw-outreach-tracking" title="Event has ended but activity is still being tracked">○ Tracking</span>';
        }
      }
      
      html += `<div class="mw-outreach-course">`;
      html += `<div class="mw-outreach-course-title"><a href="${courseUrl}" target="_blank" rel="noopener">${mw.html.escape(course.course_title)}</a> ${statusBadge}</div>`;
      
      if (enrichedCourse) {
        const metaParts = [];
        if (enrichedCourse.course_term) {
          metaParts.push(mw.html.escape(enrichedCourse.course_term));
        }
        if (enrichedCourse.user_count > 0) {
          metaParts.push(`<a href="${studentsUrl}" target="_blank" rel="noopener">${enrichedCourse.user_count} student${enrichedCourse.user_count === 1 ? '' : 's'}</a>`);
        }
        if (enrichedCourse.user_role) {
          metaParts.push(`Role: ${mw.html.escape(enrichedCourse.user_role)}`);
        }
        if (metaParts.length > 0) {
          html += `<div class="mw-outreach-meta">${metaParts.join(' • ')}</div>`;
        }
      }
      
      html += `<div class="mw-outreach-staff"><strong>Staff:</strong> `;
      html += course.staff.map(staffMember => {
        const talkUrl = `${wikiBase}/wiki/User_talk:${encodeURIComponent(staffMember)}`;
        return `<a href="${talkUrl}">${mw.html.escape(staffMember)}</a>`;
      }).join(', ');
      html += `</div></div>`;
    });
    
    html += '</div></div>';
    
    return html;
  }

  /**
   * Add CSS styles for the section.
   */
  function addStyles() {
    if (document.getElementById('mw-outreach-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'mw-outreach-styles';
    style.textContent = `
      .mw-outreach-page {
        line-height: 1.6;
      }
      .mw-outreach-section {
        border: 1px solid #a2a9b1;
        padding: 15px;
        margin: 20px 0;
        background: #f8f9fa;
        border-radius: 2px;
      }
      .mw-outreach-actions {
        margin: 15px 0;
      }
      .mw-outreach-actions .mw-outreach-copy-btn,
      .mw-outreach-actions a {
        margin-right: 10px;
      }
      .mw-outreach-copy-btn {
        padding: 5px 12px;
        background: #36c;
        color: white;
        border: none;
        border-radius: 2px;
        cursor: pointer;
        font-size: 13px;
      }
      .mw-outreach-copy-btn:hover {
        background: #2952a3;
      }
      .mw-outreach-actions a {
        padding: 5px 12px;
        background: #72777d;
        color: white;
        text-decoration: none;
        border-radius: 2px;
        font-size: 13px;
      }
      .mw-outreach-actions a:hover {
        background: #54595d;
      }
      .mw-outreach-course {
        margin-bottom: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid #c8ccd1;
      }
      .mw-outreach-course:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
      }
      .mw-outreach-course-title {
        font-weight: bold;
        margin-bottom: 4px;
      }
      .mw-outreach-meta {
        color: #54595d;
        font-size: 0.9em;
        margin-bottom: 4px;
      }
      .mw-outreach-staff {
        font-size: 0.95em;
      }
      .mw-outreach-badge {
        font-size: 0.85em;
        padding: 2px 6px;
        border-radius: 2px;
        margin-left: 6px;
      }
      .mw-outreach-active {
        background: #d5fdf4;
        color: #14866d;
      }
      .mw-outreach-tracking {
        background: #eaf3ff;
        color: #36c;
      }
    `;
    document.head.appendChild(style);
  }

  /**
   * Add the Outreach tab and set up click handler.
   */
  async function addOutreachTab(username) {
    // Add tab to page with hash URL
    const tab = mw.util.addPortletLink(
      'p-views',
      '#Outreach',
      'Outreach',
      'ca-outreach',
      'View Outreach Dashboard course staff',
      null,
      '#ca-history'
    );
    
    if (!tab) return;
    
    // Handle tab click
    tab.addEventListener('click', async function(e) {
      e.preventDefault();
      
      // Update URL hash
      window.location.hash = 'Outreach';
      
      // Mark this tab as selected
      document.querySelectorAll('#p-views li').forEach(el => el.classList.remove('selected'));
      this.classList.add('selected');
      
      // Replace page content with Outreach view
      await showOutreachContent(username);
    });
    
    // Check if we should auto-show based on hash
    if (window.location.hash === '#Outreach') {
      // Simulate a click to show the content
      tab.click();
    }
  }
  
  /**
   * Show the outreach content, replacing the current page content.
   */
  async function showOutreachContent(username) {
    try {
      const data = await fetchCourseStaff(username);
      
      addStyles();
      
      // Get the main content area
      const contentDiv = document.getElementById('mw-content-text');
      if (!contentDiv) return;
      
      if (!data) {
        contentDiv.innerHTML = `
          <div class="mw-outreach-page">
            <p>No active courses found for this user.</p>
          </div>
        `;
        return;
      }
      
      const { staffData, userData } = data;
      
      const html = renderOutreachPage(staffData, userData);
      
      // Replace the entire content
      contentDiv.innerHTML = html;
      
      // Add copy button handler
      const copyBtn = contentDiv.querySelector('.mw-outreach-copy-btn');
      if (copyBtn) {
        copyBtn.addEventListener('click', function() {
          const allStaff = JSON.parse(this.getAttribute('data-all-staff'));
          const chunks = [];
          for (let i = 0; i < allStaff.length; i += 6) {
            const chunk = allStaff.slice(i, i + 6);
            chunks.push(`{{ping|${chunk.join('|')}}}`);
          }
          navigator.clipboard.writeText(chunks.join(' '));
          
          const originalText = this.textContent;
          this.textContent = '✓ Copied!';
          setTimeout(() => {
            this.textContent = originalText;
          }, 2000);
        });
      }
      
    } catch (e) {
      console.error('Outreach gadget error:', e);
      const contentDiv = document.getElementById('mw-content-text');
      if (contentDiv) {
        contentDiv.innerHTML = `
          <div class="mw-outreach-page">
            <p class="error">Error loading course staff: ${mw.html.escape(e.message)}</p>
          </div>
        `;
      }
    }
  }
  
  /**
   * Main initialization.
   */
  mw.loader.using(['mediawiki.util']).then(async function () {
    // Only run on relevant pages
    if (!isRelevantPage()) return;

    const username = getTargetUsername();
    if (!username) return;

    // Avoid duplicates
    if (document.getElementById('ca-outreach')) return;

    // Check if user has active courses before adding tab
    try {
      const resp = await fetch(`${API_BASE}/api/users/${encodeURIComponent(username)}/active-staff`, { credentials: 'omit' });
      if (!resp.ok) return;
      
      const data = await resp.json();
      if (!data.all_staff || data.all_staff.length === 0) return;
      
      // Add the tab
      await addOutreachTab(username);
    } catch (e) {
      console.error('Outreach gadget initialization error:', e);
    }
  });
})();
