(() => {
  "use strict";

  const config = window.OVERX_CONFIG || {};
  const menuButton = document.querySelector("[data-menu-toggle]");
  const nav = document.querySelector("[data-site-nav]");
  const announcer = document.querySelector("[data-site-announcer]");
  const header = document.querySelector(".site-header");

  // Mark document as JS-enhanced for progressive reveal animations
  document.documentElement.classList.add("js-ready");

  if (header) {
    const updateHeaderScroll = () => {
      header.classList.toggle("is-scrolled", window.scrollY > 18);
    };
    updateHeaderScroll();
    window.addEventListener("scroll", updateHeaderScroll, { passive: true });
  }

  if (menuButton && nav) {
    const closeMenu = () => {
      nav.classList.remove("is-open");
      menuButton.setAttribute("aria-expanded", "false");
      menuButton.setAttribute("aria-label", "Ouvrir le menu");
    };

    menuButton.addEventListener("click", () => {
      const isOpen = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!isOpen));
      menuButton.setAttribute("aria-label", isOpen ? "Ouvrir le menu" : "Fermer le menu");
      nav.classList.toggle("is-open", !isOpen);
    });

    nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && nav.classList.contains("is-open")) {
        closeMenu();
        menuButton.focus();
      }
    });
    document.addEventListener("click", (event) => {
      if (nav.classList.contains("is-open") && !nav.contains(event.target) && !menuButton.contains(event.target)) {
        closeMenu();
      }
    });
  }

  // ------------------------------------------------------------------
  // Scroll-reveal animations (progressive & reduced-motion friendly)
  // ------------------------------------------------------------------
  const revealNodes = Array.from(document.querySelectorAll("[data-reveal]"));
  const motionQuery = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  const reduceMotion = Boolean(motionQuery && motionQuery.matches);

  if (revealNodes.length) {
    revealNodes.forEach((node) => {
      const delay = node.getAttribute("data-reveal-delay");
      if (delay) {
        node.style.setProperty("--reveal-delay", `${Number(delay)}ms`);
      }
    });

    if (reduceMotion || !("IntersectionObserver" in window)) {
      revealNodes.forEach((node) => node.classList.add("is-visible"));
    } else {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-visible");
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.08, rootMargin: "0px 0px -36px 0px" }
      );
      revealNodes.forEach((node) => observer.observe(node));
      motionQuery?.addEventListener?.("change", (event) => {
        if (event.matches) {
          revealNodes.forEach((node) => {
            node.classList.add("is-visible");
            observer.unobserve(node);
          });
        }
      });
    }
  }

  // ------------------------------------------------------------------
  // Subtle spotlight tracking on interactive surfaces
  // ------------------------------------------------------------------
  if (!reduceMotion) {
    document.querySelectorAll("[data-spotlight]").forEach((card) => {
      card.addEventListener(
        "pointermove",
        (event) => {
          const rect = card.getBoundingClientRect();
          const x = event.clientX - rect.left;
          const y = event.clientY - rect.top;
          card.style.setProperty("--spot-x", `${x}px`);
          card.style.setProperty("--spot-y", `${y}px`);
        },
        { passive: true }
      );
    });
  }

  // ------------------------------------------------------------------
  // Interactive OverLoad App Showcase tabs
  // ------------------------------------------------------------------
  document.querySelectorAll("[data-app-showcase]").forEach((showcase) => {
    const tabs = Array.from(showcase.querySelectorAll("[data-showcase-tab]"));
    const panels = Array.from(showcase.querySelectorAll("[data-showcase-panel]"));
    if (!tabs.length || !panels.length) return;

    const activateTab = (targetId, focusTab = false) => {
      tabs.forEach((tab) => {
        const selected = tab.dataset.showcaseTab === targetId;
        tab.classList.toggle("is-active", selected);
        tab.setAttribute("aria-selected", String(selected));
        if (selected && focusTab) tab.focus();
      });
      panels.forEach((panel) => {
        const active = panel.dataset.showcasePanel === targetId;
        panel.classList.toggle("is-active", active);
        panel.hidden = !active;
      });
    };

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => {
        activateTab(tab.dataset.showcaseTab);
      });
      tab.addEventListener("keydown", (event) => {
        if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
          event.preventDefault();
          const delta = event.key === "ArrowRight" ? 1 : -1;
          const next = tabs[(index + delta + tabs.length) % tabs.length];
          if (next) activateTab(next.dataset.showcaseTab, true);
        }
      });
    });
  });

  function validDiscordInstallUrl(rawUrl) {
    if (!rawUrl || typeof rawUrl !== "string") return null;
    try {
      const url = new URL(rawUrl);
      if (url.protocol !== "https:" || url.hostname !== "discord.com" || !url.pathname.startsWith("/oauth2/authorize")) return null;
      return url.href;
    } catch {
      return null;
    }
  }

  function getInstallUrl() {
    const suppliedUrl = validDiscordInstallUrl(config.discordInstallUrl);
    if (suppliedUrl) return suppliedUrl;

    const clientId = String(config.discordApplicationId || "").trim();
    // A Discord Application ID is public; bot tokens and OAuth client secrets are not.
    if (!/^\d{17,20}$/.test(clientId)) return null;

    const url = new URL("https://discord.com/oauth2/authorize");
    url.searchParams.set("client_id", clientId);
    url.searchParams.set("permissions", String(config.installPermissions || "268454928"));
    url.searchParams.set("scope", "bot applications.commands");
    return url.href;
  }

  function replaceLabel(element, label) {
    const firstText = Array.from(element.childNodes).find((node) => node.nodeType === Node.TEXT_NODE);
    if (firstText) {
      firstText.nodeValue = `${label} `;
    } else {
      element.prepend(document.createTextNode(`${label} `));
    }
  }

  function enableDiscordLink(element, url) {
    element.href = url;
    element.target = "_blank";
    element.rel = "noopener noreferrer";
    element.removeAttribute("aria-disabled");
    element.removeAttribute("aria-label");
    element.removeAttribute("title");
    element.classList.remove("is-unavailable");
    element.addEventListener("click", () => {
      if (nav?.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        menuButton?.setAttribute("aria-expanded", "false");
      }
    });
  }

  function disableDirectDiscordLink(element) {
    element.href = "#ajouter";
    element.removeAttribute("target");
    element.removeAttribute("rel");
    element.setAttribute("aria-disabled", "true");
    element.setAttribute("aria-label", "Invitation Discord de production à configurer");
    element.setAttribute("title", "Le lien officiel de l'application PROD doit être ajouté par l'équipe OverX.");
    element.classList.add("is-unavailable");
    element.addEventListener("click", (event) => {
      event.preventDefault();
      if (announcer) announcer.textContent = "Le lien d'invitation de production n'est pas encore configuré. Le bouton sera activé dès que l'URL OAuth2 officielle sera ajoutée.";
    });
  }

  const installUrl = getInstallUrl();

  // General install CTAs open Discord directly once the production link is configured.
  // Until then, they lead to a helpful install guide instead of a broken or fake URL.
  document.querySelectorAll("[data-install-cta]").forEach((link) => {
    if (installUrl) {
      enableDiscordLink(link, installUrl);
      link.setAttribute("aria-label", "Ajouter FreeGameDrop à un serveur Discord");
      replaceLabel(link, "Ajouter à Discord");
    } else {
      link.removeAttribute("aria-disabled");
      link.removeAttribute("target");
      link.removeAttribute("rel");
      link.setAttribute("aria-label", "Ouvrir le guide d'installation de FreeGameDrop");
      replaceLabel(link, "Guide d'installation");
    }
  });

  // The prominent button on the install page is the actual OAuth action.
  document.querySelectorAll("[data-discord-install]").forEach((link) => {
    if (installUrl) {
      enableDiscordLink(link, installUrl);
      link.setAttribute("aria-label", "Ajouter FreeGameDrop à un serveur Discord");
      replaceLabel(link, "Ajouter à Discord");
    } else {
      disableDirectDiscordLink(link);
      replaceLabel(link, "Invitation de production à configurer");
    }
  });

  document.querySelectorAll("[data-install-status]").forEach((element) => {
    element.textContent = installUrl
      ? "Le lien officiel d'installation est configuré. Discord te demandera ensuite de choisir le serveur et d'autoriser les permissions."
      : "Le lien OAuth2 de l'application FreeGameDrop PROD n'a pas encore été fourni. Les autres boutons ouvrent ce guide plutôt qu'un lien non vérifié.";
  });

  document.querySelectorAll("[data-copy-admin]").forEach((button) => {
    if (!installUrl) return;
    button.hidden = false;
    button.addEventListener("click", async () => {
      const message = `Peux-tu ajouter FreeGameDrop à notre serveur Discord ? Il faut la permission « Gérer le serveur » pour autoriser l'application. Voici le lien officiel : ${installUrl}`;
      try {
        await navigator.clipboard.writeText(message);
        if (announcer) announcer.textContent = "Message d'installation copié. Tu peux l'envoyer à un administrateur du serveur.";
        button.textContent = "Message copié ✓";
      } catch {
        if (announcer) announcer.textContent = "La copie automatique n'a pas fonctionné. Tu peux partager le lien d'invitation directement.";
      }
    });
  });

  document.querySelectorAll("[data-install-state]").forEach((element) => {
    const textNode = Array.from(element.childNodes).find((node) => node.nodeType === Node.TEXT_NODE);
    if (installUrl) {
      element.classList.remove("status-neutral");
      element.classList.add("status-current");
      if (textNode) textNode.nodeValue = " Invitation prête";
    } else if (textNode) {
      textNode.nodeValue = " Lien de production à configurer";
    }
  });

  document.querySelectorAll("[data-current-year]").forEach((element) => {
    element.textContent = String(new Date().getFullYear());
  });

  const communityUrl = String(config.communityInviteUrl || "").trim();
  if (communityUrl) {
    try {
      const url = new URL(communityUrl);
      if (url.protocol === "https:" && (url.hostname === "discord.gg" || url.hostname === "discord.com")) {
        document.querySelectorAll("[data-community-cta]").forEach((link) => {
          link.href = url.href;
          link.hidden = false;
          if (link.tagName === "A") {
            link.target = "_blank";
            link.rel = "noopener noreferrer";
          }
        });
      }
    } catch {
      // An invalid public invite stays hidden; never render an untrusted URL.
    }
  }

  // ------------------------------------------------------------------
  // Share button: Web Share API with clipboard fallback.
  // ------------------------------------------------------------------
  document.querySelectorAll("[data-share]").forEach((button) => {
    button.addEventListener("click", async () => {
      const url = window.location.href;
      const title = document.title;
      try {
        if (navigator.share) {
          await navigator.share({ title, url });
          return;
        }
        await navigator.clipboard.writeText(url);
        const previous = button.textContent;
        button.textContent = "Lien copié ✓";
        setTimeout(() => {
          button.textContent = previous;
        }, 2000);
      } catch {
        if (announcer) announcer.textContent = "La copie du lien n'a pas fonctionné sur ce navigateur.";
      }
    });
  });

  // ------------------------------------------------------------------
  // Catalogue: client-side search + category filters over real cards.
  // ------------------------------------------------------------------
  const catalogueGrid = document.querySelector("[data-catalogue-grid]");
  if (catalogueGrid) {
    const searchInput = document.querySelector("[data-catalogue-search]");
    const filterButtons = Array.from(document.querySelectorAll("[data-catalogue-filter]"));
    const cards = Array.from(catalogueGrid.querySelectorAll("[data-bot-card]"));
    const emptyState = document.querySelector("[data-catalogue-empty]");
    let activeFilter = "all";

    const normalize = (value) => value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

    const apply = () => {
      const query = normalize(String(searchInput?.value || "").trim());
      let visible = 0;
      cards.forEach((card) => {
        const matchesCategory = activeFilter === "all" || card.dataset.category === activeFilter;
        const haystack = normalize(`${card.dataset.search || ""} ${card.textContent || ""}`);
        const matchesQuery = !query || haystack.includes(query);
        const shown = matchesCategory && matchesQuery;
        card.hidden = !shown;
        if (shown) visible += 1;
      });
      if (emptyState) emptyState.hidden = visible !== 0;
    };

    searchInput?.addEventListener("input", apply);
    filterButtons.forEach((button) => {
      button.addEventListener("click", () => {
        activeFilter = button.dataset.catalogueFilter || "all";
        filterButtons.forEach((other) => other.classList.toggle("is-active", other === button));
        apply();
      });
    });
  }

  // ------------------------------------------------------------------
  // Public stats & health: only ever displayed when a measured API is
  // configured and reachable. "—" is the honest default.
  // ------------------------------------------------------------------
  const STAT_KEYS = {
    guilds: ["guilds", "guild_count", "server_count", "servers", "serveurs"],
    offers: ["offers_detected", "offers_total", "total_offers", "offres_detectees", "offers"],
    active_offers: ["offers_active", "active_offers", "offres_actives"],
    uptime: ["uptime_percent", "uptime"],
  };

  function pickNumber(payload, keys) {
    if (!payload || typeof payload !== "object") return null;
    for (const key of keys) {
      const value = payload[key];
      if (typeof value === "number" && Number.isFinite(value)) return value;
      if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) return Number(value);
    }
    return null;
  }

  function formatStat(key, value) {
    if (value == null) return "—";
    if (key === "uptime") return `${value.toFixed(1).replace(".", ",")} %`;
    return new Intl.NumberFormat("fr-FR").format(value);
  }

  async function fetchJson(url, timeoutMs = 6000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { signal: controller.signal, headers: { Accept: "application/json" } });
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    } finally {
      clearTimeout(timer);
    }
  }

  const statsUrl = String(config.statsApiUrl || "").trim();
  const statNodes = document.querySelectorAll("[data-stat]");
  if (statsUrl && statNodes.length) {
    fetchJson(statsUrl).then((payload) => {
      const note = document.querySelector("[data-stats-note]");
      if (!payload) {
        if (note) note.textContent = "L'API de statistiques configurée n'a pas répondu : les compteurs restent à « — » plutôt que d'afficher une valeur incertaine.";
        return;
      }
      statNodes.forEach((node) => {
        const value = pickNumber(payload, STAT_KEYS[node.dataset.stat] || [node.dataset.stat]);
        node.textContent = formatStat(node.dataset.stat, value);
      });
      if (note) note.textContent = "Chiffres mesurés par l'instance publique du bot, via son API /api/stats.";
    });
  }

  const healthUrl = String(config.healthApiUrl || "").trim();
  const healthPanel = document.querySelector("[data-health-panel]");
  if (healthUrl && healthPanel) {
    fetchJson(healthUrl).then((payload) => {
      const title = document.querySelector("[data-health-title]");
      const updated = document.querySelector("[data-health-updated]");
      if (!payload) {
        if (title) title.textContent = "Sonde configurée mais injoignable";
        if (updated) updated.textContent = "l'endpoint /api/health n'a pas répondu depuis ce navigateur";
        return;
      }
      healthPanel.hidden = false;
      if (title) title.textContent = "Mesuré en temps réel";
      const stamp = payload.checked_at || payload.last_check || payload.updated_at || payload.timestamp;
      if (updated) updated.textContent = stamp ? `dernière vérification : ${String(stamp)}` : "dernière vérification : à l'instant";

      const setDot = (name, state) => {
        const dot = document.querySelector(`[data-health-dot="${name}"]`);
        const text = document.querySelector(`[data-health-text="${name}"]`);
        const ok = state === "ok" || state === true || state === "up";
        const warn = state === "warn" || state === "degraded";
        if (dot) {
          dot.textContent = ok ? "✓" : warn ? "!" : "?";
          dot.classList.add(ok ? "dot-ok" : warn ? "dot-warn" : "dot-down");
        }
        if (text) text.textContent = ok ? "opérationnel" : warn ? "dégradé" : typeof state === "string" ? state : "indisponible";
      };

      const components = payload.components || payload;
      setDot("bot", components.bot ?? payload.bot ?? (payload.status === "ok" ? "ok" : "down"));
      setDot("discord", components.discord ?? payload.discord ?? payload.discord_connected);
      setDot("database", components.database ?? payload.database ?? payload.db);
      const sources = components.sources ?? payload.sources;
      if (sources && typeof sources === "object") {
        const states = Object.values(sources).map((source) => (source && typeof source === "object" ? source.state || source.status : source));
        const allOk = states.every((state) => state === "ok" || state === true || state === "up");
        const anyOk = states.some((state) => state === "ok" || state === true || state === "up");
        setDot("sources", allOk ? "ok" : anyOk ? "warn" : "down");
        const text = document.querySelector('[data-health-text="sources"]');
        if (text) text.textContent = states.map((state) => String(state)).join(" · ");
      } else {
        setDot("sources", sources);
      }
    });
  }
})();
