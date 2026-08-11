/**
 * common.js — renderCommonLayout()
 * Injects the sidebar navigation and top-navbar into the pre-existing
 * #sidebar and #top-navbar placeholder elements.
 */
(function () {
  "use strict";

  // ── Helpers ────────────────────────────────────────────────
  function currentPath() {
    return window.location.pathname;
  }

  function isActive(href) {
    const p = currentPath();
    if (href === "/" && p === "/") return true;
    if (href !== "/" && p.startsWith(href)) return true;
    return false;
  }

  function a(href, icon, label) {
    const active = isActive(href) ? " active" : "";
    return `<a href="${href}" class="sidebar-item${active}">
              <i class="bi ${icon}"></i><span>${label}</span>
            </a>`;
  }

  function section(label) {
    return `<div class="sidebar-section">${label}</div>`;
  }

  function group(icon, label, children) {
    const childHrefs = [...children.matchAll(/href="([^"]+)"/g)].map(m => m[1]);
    const open = childHrefs.some(h => isActive(h)) ? " open" : "";
    return `<details class="sidebar-group"${open}>
      <summary><i class="bi ${icon}"></i><span>${label}</span><i class="bi bi-chevron-right caret"></i></summary>
      <div class="sidebar-sub">${children}</div>
    </details>`;
  }

  // ── Build sidebar HTML ──────────────────────────────────────
  function buildSidebar() {
    return `
      <div class="sidebar-logo">
        <div class="sidebar-logo-icon"><i class="bi bi-calendar-event-fill"></i></div>
        <div>
          <div class="sidebar-logo-text">EventHub</div>
          <div class="sidebar-logo-sub">Registration Platform</div>
        </div>
      </div>

      ${section("Core")}
      ${a("/", "bi-speedometer2", "Dashboard")}

      ${section("Event Category")}
      ${group("bi-folder2-open", "Event Category",
        a("/create-event-category/", "bi-plus-circle", "Create Category") +
        a("/event-category/", "bi-list-ul", "Category List")
      )}

      ${section("Events")}
      ${group("bi-calendar3", "Events",
        a("/create-event/", "bi-plus-circle", "Create Event") +
        a("/event-list/", "bi-list-ul", "Event List")
      )}

      ${section("Members")}
      ${a("/add-event-member/", "bi-person-plus-fill", "Add Event Member")}
      ${a("/join-event-list/", "bi-people-fill", "Join Event List")}

      ${section("Wishlist")}
      ${a("/event-user-wish-list/", "bi-heart-fill", "Event Wish List")}
      ${a("/add-event-user-wish/", "bi-heart-plus-fill", "Add Event Wish User")}

      ${section("Attendance & Marks")}
      ${a("/complete-event-list/", "bi-check2-circle", "Complete Event List")}
      ${a("/absense-user-list/", "bi-person-x-fill", "Absence User List")}
      ${a("/create-user-mark/", "bi-pencil-fill", "Create User Mark")}
      ${a("/user-mark-list/", "bi-journal-check", "User Mark List")}
    `;
  }

  // ── Build top-navbar HTML ───────────────────────────────────
  function buildNavbar() {
    // Read username from meta tag injected by Django (see base.html)
    const userMeta = document.querySelector('meta[name="current-user"]');
    const username = userMeta ? userMeta.content : "Admin";

    return `
      <span class="navbar-brand-text"><i class="bi bi-calendar-event me-1"></i>Event Registration Platform</span>
      <div class="navbar-right">
        <span class="navbar-user">Logged in as: <span>${username}</span></span>
        <a href="/logout/" class="btn-logout"><i class="bi bi-box-arrow-right me-1"></i>Logout</a>
      </div>
    `;
  }

  // ── Inject into DOM ─────────────────────────────────────────
  function renderCommonLayout() {
    const sidebar = document.getElementById("sidebar");
    const navbar  = document.getElementById("top-navbar");

    if (sidebar) sidebar.innerHTML = buildSidebar();
    if (navbar)  navbar.innerHTML  = buildNavbar();
  }

  // Run after DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderCommonLayout);
  } else {
    renderCommonLayout();
  }

  // Expose globally (optional)
  window.renderCommonLayout = renderCommonLayout;
})();
