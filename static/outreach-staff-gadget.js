/**
 * Outreach Dashboard Course Staff Gadget
 * 
 * Adds an "Outreach" tab to user-related pages for users who have any presence
 * on the Outreach Dashboard. Clicking the tab opens a modal dialog showing
 * staff information. The tab includes a traffic light indicator:
 * - 🟢 Green: User has courses with active events
 * - 🟡 Yellow: User has courses being tracked (event ended)
 * - 🔴 Red: User has courses but none are currently active/tracked
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
   * Fetch user dashboard status (lightweight check).
   */
  async function fetchUserStatus(username) {
    const resp = await fetch(`${API_BASE}/api/users/${encodeURIComponent(username)}/status`, { credentials: 'omit' });
    if (!resp.ok) return null;
    return await resp.json();
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
   * Add CSS styles for the modal and content.
   */
  function addStyles() {
    if (document.getElementById('mw-outreach-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'mw-outreach-styles';
    style.textContent = `
      /* Modal overlay */
      .mw-outreach-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
      }
      .mw-outreach-modal {
        background: white;
        border-radius: 4px;
        max-width: 800px;
        width: 100%;
        max-height: 90vh;
        overflow: auto;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        position: relative;
      }
      .mw-outreach-modal-header {
        position: sticky;
        top: 0;
        background: #f8f9fa;
        border-bottom: 1px solid #a2a9b1;
        padding: 15px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        z-index: 1;
      }
      .mw-outreach-modal-title {
        font-size: 1.3em;
        font-weight: bold;
        margin: 0;
      }
      .mw-outreach-modal-close {
        background: none;
        border: none;
        font-size: 24px;
        line-height: 1;
        cursor: pointer;
        color: #72777d;
        padding: 0;
        width: 30px;
        height: 30px;
        border-radius: 2px;
      }
      .mw-outreach-modal-close:hover {
        background: #eaecf0;
        color: #000;
      }
      .mw-outreach-modal-body {
        padding: 20px;
      }
      .mw-outreach-loading {
        text-align: center;
        padding: 40px;
        color: #72777d;
      }
      
      /* Tab indicator */
      .mw-outreach-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-left: 6px;
        vertical-align: middle;
      }
      .mw-outreach-indicator-active {
        background: #14866d;
        box-shadow: 0 0 4px rgba(20, 134, 109, 0.5);
      }
      .mw-outreach-indicator-tracking {
        background: #fc3;
        box-shadow: 0 0 4px rgba(255, 204, 51, 0.5);
      }
      .mw-outreach-indicator-inactive {
        background: #72777d;
      }
      
      /* Content styles */
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
   * Add the Outreach tab with status indicator.
   */
  function addOutreachTab(username, status) {
    // Determine indicator class based on status
    let indicatorClass = 'mw-outreach-indicator-inactive';
    let tooltip = 'View Outreach Dashboard information';
    
    if (status.has_active_event) {
      indicatorClass = 'mw-outreach-indicator-active';
      tooltip = `Active events: ${status.active_event_count} course(s) with ongoing events`;
    } else if (status.has_active_tracking) {
      indicatorClass = 'mw-outreach-indicator-tracking';
      tooltip = `Being tracked: ${status.tracked_count} course(s) being tracked`;
    } else if (status.has_any_courses) {
      tooltip = `${status.total_courses} course(s) on dashboard (not currently active)`;
    }
    
    // Create tab with indicator
    const tab = mw.util.addPortletLink(
      'p-views',
      '#',
      'Outreach',
      'ca-outreach',
      tooltip,
      null,
      '#ca-history'
    );
    
    if (!tab) return;
    
    // Add indicator dot to the tab
    const link = tab.querySelector('a');
    if (link) {
      const indicator = document.createElement('span');
      indicator.className = `mw-outreach-indicator ${indicatorClass}`;
      link.appendChild(indicator);
    }
    
    // Handle tab click - open modal
    tab.addEventListener('click', async function(e) {
      e.preventDefault();
      await showOutreachModal(username, status);
    });
  }
  
  /**
   * Show the outreach modal dialog.
   */
  async function showOutreachModal(username, status) {
    addStyles();
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'mw-outreach-modal-overlay';
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'mw-outreach-modal';
    
    // Create header
    const header = document.createElement('div');
    header.className = 'mw-outreach-modal-header';
    
    const title = document.createElement('h2');
    title.className = 'mw-outreach-modal-title';
    title.textContent = `Outreach Dashboard: ${username}`;
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'mw-outreach-modal-close';
    closeBtn.innerHTML = '×';
    closeBtn.title = 'Close';
    
    header.appendChild(title);
    header.appendChild(closeBtn);
    
    // Create body
    const body = document.createElement('div');
    body.className = 'mw-outreach-modal-body';
    body.innerHTML = '<div class="mw-outreach-loading">Loading...</div>';
    
    modal.appendChild(header);
    modal.appendChild(body);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Close handlers
    const closeModal = () => {
      overlay.remove();
    };
    
    closeBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal();
    });
    
    // ESC key handler
    const escHandler = (e) => {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', escHandler);
      }
    };
    document.addEventListener('keydown', escHandler);
    
    // Load content
    try {
      const data = await fetchCourseStaff(username);
      
      if (!data) {
        // No active courses - show all courses instead
        const userResp = await fetch(`${API_BASE}/api/users/${encodeURIComponent(username)}?enrich=true`, { credentials: 'omit' });
        if (userResp.ok) {
          const userData = await userResp.json();
          body.innerHTML = renderAllCoursesPage(userData, status);
        } else {
          body.innerHTML = `
            <div class="mw-outreach-page">
              <p>User has ${status.total_courses} course(s) on the dashboard, but none are currently active.</p>
              <p><a href="${OUTREACH_BASE}/users/${encodeURIComponent(username)}" target="_blank" rel="noopener">View on Outreach Dashboard</a></p>
            </div>
          `;
        }
      } else {
        const { staffData, userData } = data;
        body.innerHTML = renderOutreachPage(staffData, userData);
        
        // Add copy button handler
        const copyBtn = body.querySelector('.mw-outreach-copy-btn');
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
      }
    } catch (e) {
      console.error('Outreach modal error:', e);
      body.innerHTML = `
        <div class="mw-outreach-page">
          <p class="error">Error loading course information: ${mw.html.escape(e.message)}</p>
        </div>
      `;
    }
  }
  
  /**
   * Render page for users with courses but no active staff.
   */
  function renderAllCoursesPage(userData, status) {
    const wikiBase = window.location.origin;
    let html = '<div class="mw-outreach-page"><div class="mw-outreach-section">';
    
    html += `<p><strong>${status.total_courses}</strong> course(s) on the dashboard.</p>`;
    
    if (status.active_event_count === 0 && status.tracked_count === 0) {
      html += `<p>None are currently active or being tracked.</p>`;
    }
    
    html += `
      <p class="mw-outreach-actions">
        <a href="${OUTREACH_BASE}/users/${encodeURIComponent(userData.username)}" target="_blank" rel="noopener">View on Outreach Dashboard</a>
      </p>
    `;
    
    // Show courses if available
    if (userData.courses && userData.courses.length > 0) {
      const sortedCourses = [...userData.courses].sort((a, b) => {
        const activeEventA = a.active_event ? 1 : 0;
        const activeEventB = b.active_event ? 1 : 0;
        if (activeEventA !== activeEventB) {
          return activeEventB - activeEventA;
        }
        
        const activeTrackingA = a.active_tracking ? 1 : 0;
        const activeTrackingB = b.active_tracking ? 1 : 0;
        if (activeTrackingA !== activeTrackingB) {
          return activeTrackingB - activeTrackingA;
        }
        
        const dateA = a.timeline_end || a.end || '';
        const dateB = b.timeline_end || b.end || '';
        
        if (dateA && dateB) {
          return dateB.localeCompare(dateA);
        }
        
        return a.course_title.localeCompare(b.course_title);
      });
      
      sortedCourses.forEach(course => {
        const courseUrl = `${OUTREACH_BASE}/courses/${course.course_slug}`;
        
        let statusBadge = '';
        if (course.active_event) {
          statusBadge = '<span class="mw-outreach-badge mw-outreach-active" title="Event is currently happening">● Active</span>';
        } else if (course.active_tracking) {
          statusBadge = '<span class="mw-outreach-badge mw-outreach-tracking" title="Event has ended but activity is still being tracked">○ Tracking</span>';
        }
        
        html += `<div class="mw-outreach-course">`;
        html += `<div class="mw-outreach-course-title"><a href="${courseUrl}" target="_blank" rel="noopener">${mw.html.escape(course.course_title)}</a> ${statusBadge}</div>`;
        
        const metaParts = [];
        if (course.course_term) {
          metaParts.push(mw.html.escape(course.course_term));
        }
        if (course.user_role) {
          metaParts.push(`Role: ${mw.html.escape(course.user_role)}`);
        }
        if (metaParts.length > 0) {
          html += `<div class="mw-outreach-meta">${metaParts.join(' • ')}</div>`;
        }
        
        html += `</div>`;
      });
    }
    
    html += '</div></div>';
    return html;
  }
  
  /**
   * Main initialization.
   */
  mw.loader.using(['mediawiki.util']).then(async function () {
    // Only run on relevant pages
    if (!isRelevantPage()) return;

    const username = getTargetUsername();
    if (!username) return;

    // Guard against multiple simultaneous initializations
    const guardKey = 'outreach-gadget-initializing';
    if (window[guardKey]) {
      console.debug('Outreach gadget: Already initializing, skipping duplicate');
      return;
    }
    
    // Avoid duplicates - check for existing tab
    if (document.getElementById('ca-outreach')) {
      console.debug('Outreach gadget: Tab already exists, skipping duplicate');
      return;
    }
    
    // Set guard flag
    window[guardKey] = true;

    // Add styles early so indicator shows properly
    addStyles();

    // Check if user has any dashboard presence
    try {
      const status = await fetchUserStatus(username);
      if (!status || !status.has_any_courses) return;
      
      // Double-check before adding tab (race condition protection)
      if (document.getElementById('ca-outreach')) {
        console.debug('Outreach gadget: Tab appeared during initialization, skipping');
        return;
      }
      
      // Add the tab with status indicator
      addOutreachTab(username, status);
    } catch (e) {
      console.error('Outreach gadget initialization error:', e);
    } finally {
      // Clear guard flag after a short delay to allow for legitimate re-runs on different pages
      setTimeout(() => {
        delete window[guardKey];
      }, 1000);
    }
  });
})();
