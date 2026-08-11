/**
 * common.js — renderCommonLayout()
 * Builds the sidebar + top-navbar and injects them into their placeholder elements.
 * Sidebar design matches the AdminLTE-style layout shown in the project reference image.
 */
(function () {
  "use strict";

  /* ── Path helpers ─────────────────────────────────── */
  function path() {
    return window.location.pathname.replace(/\/$/, '') || '/';
  }

  function normalizeHref(href) {
    return href.replace(/\/$/, '') || '/';
  }

  function isActive(href) {
    return path() === normalizeHref(href);
  }

  /* ── Single nav link ──────────────────────────────── */
  function navLink(href, icon, label) {
    const active = isActive(href) ? " nav-active" : "";
    return `
      <li class="nav-item${active}">
        <a href="${href}" class="nav-link${active}">
          <i class="nav-icon bi ${icon}"></i>
          <p>${label}</p>
        </a>
      </li>`;
  }

  /* ── Collapsible nav group ────────────────────────── */
  function navGroup(icon, label, children) {
    const childHrefs = [...children.matchAll(/href="([^"]+)"/g)].map(m => m[1]);
    const anyActive  = childHrefs.some(h => isActive(h));
    const openClass  = anyActive ? " menu-open" : "";
    const id         = "group-" + label.replace(/\s+/g, "-").toLowerCase();
    return `
      <li class="nav-item has-treeview${openClass}">
        <a href="#" class="nav-link" onclick="toggleMenu('${id}',this);return false;">
          <i class="nav-icon bi ${icon}"></i>
          <p>${label}<i class="bi bi-chevron-right right"></i></p>
        </a>
        <ul class="nav nav-treeview" id="${id}" style="display:${anyActive ? "block" : "none"}">
          ${children}
        </ul>
      </li>`;
  }

  /* ── Section header ───────────────────────────────── */
  function navHeader(label) {
    return `<li class="nav-header">${label}</li>`;
  }

  /* ── Build full sidebar HTML ──────────────────────── */
  function buildSidebar() {
    const userMeta = document.querySelector('meta[name="current-user"]');
    const username = userMeta ? userMeta.content : "Admin";
    const initial  = username.charAt(0).toUpperCase();

    return `
      <!-- Brand / Logo -->
      <div class="sidebar-brand">
        <a href="/" class="brand-link">
          <div class="brand-icon-wrap">
            <i class="bi bi-calendar-event-fill"></i>
          </div>
          <span class="brand-text">Admin Panel</span>
        </a>
      </div>

      <!-- User panel -->
      <div class="sidebar-user-panel">
        <div class="user-avatar">${initial}</div>
        <div class="user-info">
          <span class="user-name">${username}</span>
          <span class="user-status"><i class="bi bi-circle-fill"></i> Online</span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="sidebar-nav">
        <ul class="nav nav-pills nav-sidebar flex-column">

          ${navHeader("MAIN NAVIGATION")}
          ${navLink("/", "bi-speedometer2", "Dashboard")}

          ${navHeader("EVENT CATEGORY")}
          ${navGroup("bi-folder2-open", "Event Category",
              navLink("/create-event-category/", "bi-plus-circle-dotted", "Create Category") +
              navLink("/event-category/",         "bi-list-ul",            "Category List")
          )}

          ${navHeader("EVENTS")}
          ${navGroup("bi-calendar3", "Events",
              navLink("/create-event/", "bi-plus-circle-dotted", "Create Event") +
              navLink("/event-list/",   "bi-list-ul",            "Event List")
          )}

          ${navHeader("MEMBERS")}
          ${navLink("/add-event-member/", "bi-person-plus-fill", "Add Event Member")}
          ${navLink("/join-event-list/",  "bi-people-fill",      "Join Event List")}

          ${navHeader("WISHLIST")}
          ${navLink("/event-user-wish-list/", "bi-heart-fill",      "Event Wish List")}
          ${navLink("/add-event-user-wish/",  "bi-heart-plus-fill", "Add Event Wish User")}

          ${navHeader("ATTENDANCE & MARKS")}
          ${navLink("/absense-user-list/",         "bi-person-x-fill",  "Absence User List")}
          ${navLink("/complete-event-list/",        "bi-check2-circle",  "Complete Event List")}
          ${navLink("/create-user-mark/",           "bi-pencil-fill",    "Create User Mark")}
          ${navLink("/user-mark-list/",             "bi-journal-check",  "User Mark List")}

        </ul>
      </nav>`;
  }

  /* ── Build top-navbar HTML ────────────────────────── */
  function buildNavbar() {
    const userMeta = document.querySelector('meta[name="current-user"]');
    const username = userMeta ? userMeta.content : "Admin";

    return `
      <!-- Hamburger toggle -->
      <button class="navbar-toggle-btn" onclick="toggleSidebar()" title="Toggle Sidebar">
        <i class="bi bi-list"></i>
      </button>

      <!-- Brand name (centre-left) -->
      <a href="/" class="navbar-brand-link">
        <i class="bi bi-calendar-event me-1"></i>
        <span>Event Registration Platform</span>
      </a>

      <!-- Right controls -->
      <ul class="navbar-right-menu">
        <li class="nav-item dropdown">
          <a href="#" class="nav-link dropdown-toggle d-flex align-items-center gap-2"
             data-bs-toggle="dropdown">
            <div class="navbar-avatar">${username.charAt(0).toUpperCase()}</div>
            <span class="navbar-username d-none d-md-inline">${username}</span>
          </a>
          <ul class="dropdown-menu dropdown-menu-end shadow-sm">
            <li><span class="dropdown-item-text text-muted small px-3 py-1">Signed in as <strong>${username}</strong></span></li>
            <li><hr class="dropdown-divider my-1"></li>
            <li><a class="dropdown-item" href="/logout/">
              <i class="bi bi-box-arrow-right me-2 text-danger"></i>Logout
            </a></li>
          </ul>
        </li>
      </ul>`;
  }

  /* ── Toggle collapsible menu group ───────────────── */
  window.toggleMenu = function (id, anchor) {
    const ul     = document.getElementById(id);
    const li     = anchor.closest("li");
    const isOpen = li.classList.contains("menu-open");
    if (isOpen) {
      li.classList.remove("menu-open");
      ul.style.display = "none";
    } else {
      li.classList.add("menu-open");
      ul.style.display = "block";
    }
  };

  /* ── Toggle sidebar collapsed state ──────────────── */
  window.toggleSidebar = function () {
    document.body.classList.toggle("sidebar-collapsed");
  };

  /* ── Inject ───────────────────────────────────────── */
  function renderCommonLayout() {
    const sidebar = document.getElementById("sidebar");
    const navbar  = document.getElementById("top-navbar");
    if (sidebar) sidebar.innerHTML = buildSidebar();
    if (navbar)  navbar.innerHTML  = buildNavbar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderCommonLayout);
  } else {
    renderCommonLayout();
  }

  window.renderCommonLayout = renderCommonLayout;
})();
