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

  // ------------------------------------------------------------------
  // Jeux gratuits : catalogue commun FreeGameDrop ↔ OverX
  // Lit data/offers.json (ou offersApiUrl) et rend filtres + cartes.
  // ------------------------------------------------------------------
  const offersRoot = document.querySelector("[data-offers-catalog]");
  if (offersRoot) {
    const grid = offersRoot.querySelector("[data-offers-grid]");
    const searchInput = offersRoot.querySelector("[data-offers-search]");
    const platformChips = Array.from(offersRoot.querySelectorAll("[data-offers-platform]"));
    const typeChips = Array.from(offersRoot.querySelectorAll("[data-offers-type]"));
    const sortSelect = offersRoot.querySelector("[data-offers-sort]");
    const countNode = document.querySelector("[data-offers-count]");
    const updatedNode = document.querySelector("[data-offers-updated]");
    const emptyNode = offersRoot.querySelector("[data-offers-empty]");
    const loadingNode = offersRoot.querySelector("[data-offers-loading]");
    const noticeNode = document.querySelector("[data-offers-notice]");
    const expiryToggle = offersRoot.querySelector("[data-offers-expiring]");

    const PAGE_SIZE = 24;
    const pagination = offersRoot.querySelector("[data-offers-pagination]");
    let allOffers = [];
    let activePlatform = "all";
    let activeType = "all";
    let onlyExpiring = false;
    let currentPage = 1;

    // Pré-filtre via URL : ?platform=steam&type=dlc&q=orbit&expiring=1
    try {
      const params = new URLSearchParams(window.location.search);
      const p = params.get("platform") || params.get("boutique");
      if (p && ["steam","epic","gog","ubisoft"].includes(p.toLowerCase())) activePlatform = p.toLowerCase();
      const t = params.get("type");
      if (t && ["game","dlc","pack"].includes(t.toLowerCase())) activeType = t.toLowerCase();
      const q = params.get("q") || params.get("search");
      if (q && searchInput) searchInput.value = q;
      const page = Number.parseInt(params.get("page") || "1", 10);
      if (Number.isFinite(page) && page > 0) currentPage = page;
      if (params.get("expiring") === "1" || params.get("urgent") === "1") onlyExpiring = true;
    } catch {}
    // Sync visuel des chips avec l'état initial (URL ou défaut)
    platformChips.forEach((c) => c.classList.toggle("is-active", (c.dataset.offersPlatform || "all") === activePlatform));
    typeChips.forEach((c) => c.classList.toggle("is-active", (c.dataset.offersType || "all") === activeType));
    if (expiryToggle) expiryToggle.checked = onlyExpiring;

    const PLATFORM_LABELS = { steam: "Steam", epic: "Epic Games Store", gog: "GOG", ubisoft: "Ubisoft" };
    const TYPE_LABELS = { game: "Jeu complet", dlc: "DLC", pack: "Contenu bonus" };

    const normalize = (value) => String(value || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

    const formatExpiry = (offer) => {
      if (offer.is_permanent || offer.availability === "permanent" || !offer.expires_at) {
        return { text: "Toujours gratuit", cls: "permanent", urgent: false, ms: Infinity };
      }
      const expiry = new Date(offer.expires_at);
      if (Number.isNaN(expiry.getTime())) return { text: "Durée limitée", cls: "permanent", urgent: false, ms: Infinity };
      const diff = expiry.getTime() - Date.now();
      if (diff <= 0) return { text: "Expiré", cls: "urgency-high", urgent: false, ms: diff, expired: true };
      const hours = diff / 3600000;
      let cls = "urgency-low";
      if (hours <= 6) cls = "urgency-high";
      else if (hours <= 24) cls = "urgency-mid";
      const days = Math.floor(hours / 24);
      const remHours = Math.floor(hours % 24);
      let text = "";
      if (days > 0) text = `Expire dans ${days}j ${remHours}h`;
      else if (hours >= 1) text = `Expire dans ${Math.floor(hours)}h`;
      else text = `Expire dans ${Math.floor(diff / 60000)} min`;
      return { text, cls, urgent: hours <= 24, ms: diff };
    };

    const isExpired = (offer) => {
      if (offer.is_permanent || offer.availability === "permanent" || !offer.expires_at) return false;
      const d = new Date(offer.expires_at);
      return !Number.isNaN(d.getTime()) && d.getTime() <= Date.now();
    };

    const escapeHtml = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[char]);

    const directOfferUrl = (offer) => {
      try {
        const parsed = new URL(String(offer.url || ""));
        if (parsed.protocol !== "https:" || parsed.pathname === "/" || !parsed.hostname.includes(".")) return "";
        return parsed.href;
      } catch {
        return "";
      }
    };

    const offerImageUrl = (offer) => {
      const supplied = String(offer.image || "").trim();
      if (supplied) {
        try {
          const parsed = new URL(supplied);
          if (parsed.protocol === "https:") return parsed.href;
        } catch {}
      }
      // Steam's official CDN exposes a cover image for both app and DLC IDs.
      const steamMatch = offer.platform === "steam" && String(offer.url || "").match(/store\.steampowered\.com\/(?:app|sub)\/(\d+)/i);
      return steamMatch ? `https://cdn.akamai.steamstatic.com/steam/apps/${steamMatch[1]}/header.jpg` : "";
    };

    const offerCard = (offer) => {
      const expiry = formatExpiry(offer);
      const platformLabel = escapeHtml(offer.platform_label || PLATFORM_LABELS[offer.platform] || offer.platform || "—");
      const typeLabel = escapeHtml(offer.type_label || TYPE_LABELS[offer.type] || offer.type || "Offre");
      const initial = escapeHtml((offer.title || "?").trim().charAt(0).toUpperCase() || "?");
      const titleEsc = escapeHtml(offer.title || "Offre sans titre");
      const descEsc = escapeHtml(offer.description || "");
      const url = directOfferUrl(offer);
      const detailBase = offersRoot.dataset.offersDetailUrl || "fiche.html";
      const detailUrl = offer.id ? `${detailBase}?id=${encodeURIComponent(String(offer.id))}` : "";
      const image = offerImageUrl(offer);
      const priceOrig = offer.price_original ? `<s>${escapeHtml(offer.price_original)}</s>` : "";
      const expiredCls = expiry.expired ? " is-expired" : "";
      const badges = `<div class="offer-badges"><span class="offer-badge offer-badge-platform">${platformLabel}</span><span class="offer-badge offer-badge-type">${typeLabel}</span></div>`;
      const visual = image
        ? `<div class="offer-visual has-image"><div class="offer-visual-placeholder">${initial}<span>•</span></div><img src="${escapeHtml(image)}" alt="Visuel de ${titleEsc}" loading="lazy" onerror="this.closest('.offer-visual').classList.remove('has-image');this.remove()">${badges}<span class="offer-expiry ${expiry.cls}">${expiry.text}</span></div>`
        : `<div class="offer-visual"><div class="offer-visual-placeholder">${initial}<span>•</span></div>${badges}<span class="offer-expiry ${expiry.cls}">${expiry.text}</span></div>`;
      const action = url
        ? `<a class="button button-primary" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Récupérer <span aria-hidden="true">↗</span></a>`
        : `<span class="button button-secondary" aria-disabled="true" title="Lien direct vers la fiche du jeu ou du DLC manquant">Lien de l'offre indisponible</span>`;
      return `<article class="offer-card${expiredCls}" data-platform="${escapeHtml(offer.platform || "")}" data-type="${escapeHtml(offer.type || "")}" data-title="${titleEsc.toLowerCase()}" data-spotlight>
        ${visual}
        <div class="offer-body">
          <h3 class="offer-title">${titleEsc}</h3>
          <div class="offer-meta"><strong>${platformLabel}</strong> · ${typeLabel}${offer.availability === "permanent" ? " · Permanent" : ""}</div>
          <p class="offer-desc">${descEsc}</p>
          <div class="offer-price">${priceOrig} <b>Gratuit</b></div>
          <div class="offer-actions">
            ${action}
            ${detailUrl ? `<a class="button button-secondary" href="${escapeHtml(detailUrl)}">Détails <span aria-hidden="true">→</span></a>` : ""}
          </div>
        </div>
      </article>`;
    };

    const applyFilters = () => {
      if (!grid) return;
      const query = normalize(searchInput?.value || "");
      const sort = sortSelect?.value || "urgent";
      let visible = 0;
      const now = Date.now();

      let filtered = allOffers.filter((offer) => {
        if (activePlatform !== "all" && offer.platform !== activePlatform) return false;
        if (activeType !== "all" && offer.type !== activeType) return false;
        if (onlyExpiring) {
          if (offer.is_permanent || offer.availability === "permanent" || !offer.expires_at) return false;
          const expiry = new Date(offer.expires_at);
          if (Number.isNaN(expiry.getTime()) || expiry.getTime() <= now) return false;
          const hours = (expiry.getTime() - now) / 3600000;
          if (hours > 72) return false;
        }
        if (query) {
          const haystack = normalize(`${offer.title || ""} ${offer.description || ""} ${offer.platform_label || ""} ${offer.type_label || ""}`);
          if (!haystack.includes(query)) return false;
        }
        if (isExpired(offer)) return false;
        return true;
      });

      filtered = filtered.slice().sort((a, b) => {
        if (sort === "alpha") return String(a.title).localeCompare(String(b.title), "fr");
        if (sort === "platform") return String(a.platform).localeCompare(String(b.platform));
        const ea = formatExpiry(a).ms;
        const eb = formatExpiry(b).ms;
        if (ea !== eb) return ea - eb;
        return String(a.title).localeCompare(String(b.title), "fr");
      });

      const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
      currentPage = Math.min(Math.max(currentPage, 1), pageCount);
      const pageStart = (currentPage - 1) * PAGE_SIZE;
      const pageOffers = filtered.slice(pageStart, pageStart + PAGE_SIZE);
      grid.innerHTML = pageOffers.map(offerCard).join("");

      if (pagination) {
        if (pageCount <= 1) {
          pagination.hidden = true;
          pagination.innerHTML = "";
        } else {
          pagination.hidden = false;
          const first = Math.max(1, Math.min(currentPage - 2, pageCount - 4));
          const last = Math.min(pageCount, first + 4);
          const pageButtons = Array.from({ length: last - first + 1 }, (_, index) => {
            const page = first + index;
            return `<button type="button" class="offers-page${page === currentPage ? " is-active" : ""}" data-offers-page="${page}"${page === currentPage ? ' aria-current="page"' : ""} aria-label="Page ${page}">${page}</button>`;
          }).join("");
          pagination.innerHTML = `<button type="button" class="offers-page offers-page-step" data-offers-page="${currentPage - 1}"${currentPage === 1 ? " disabled" : ""} aria-label="Page précédente">←</button>${pageButtons}<button type="button" class="offers-page offers-page-step" data-offers-page="${currentPage + 1}"${currentPage === pageCount ? " disabled" : ""} aria-label="Page suivante">→</button><span class="offers-page-summary">Page ${currentPage} sur ${pageCount}</span>`;
        }
      }
      if (pagination && !pagination.dataset.bound) {
        pagination.dataset.bound = "true";
        pagination.addEventListener("click", (event) => {
          const button = event.target.closest("[data-offers-page]");
          if (!button || button.disabled) return;
          currentPage = Number(button.dataset.offersPage) || 1;
          applyFilters();
          offersRoot.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }

      visible = filtered.length;
      if (pagination && pageCount > 1) {
        const rangeStart = pageStart + 1;
        const rangeEnd = Math.min(pageStart + PAGE_SIZE, visible);
        const summary = pagination.querySelector(".offers-page-summary");
        if (summary) summary.textContent = `Page ${currentPage} sur ${pageCount} · ${rangeStart}–${rangeEnd} sur ${visible}`;
      }

      if (countNode) {
        const total = allOffers.filter((o) => !isExpired(o)).length;
        countNode.innerHTML = visible === total
          ? `<strong>${visible}</strong> offre${visible !== 1 ? "s" : ""} disponible${visible !== 1 ? "s" : ""}`
          : `<strong>${visible}</strong> / ${total} offre${total !== 1 ? "s" : ""}`;
      }

      if (emptyNode) {
        emptyNode.hidden = visible !== 0;
        if (visible === 0 && allOffers.length > 0) {
          const msg = query ? `Aucun résultat pour « ${String(searchInput.value).replace(/</g, "&lt;")} ».` : "Aucune offre ne correspond à ces filtres.";
          emptyNode.querySelector("p").textContent = msg + " Essaie un autre filtre ou efface la recherche.";
        }
      }
    };

    const bindChips = (chips, getActive, setActive) => {
      chips.forEach((chip) => {
        chip.addEventListener("click", () => {
          setActive(chip.dataset.offersPlatform || chip.dataset.offersType || "all");
          chips.forEach((c) => c.classList.toggle("is-active", c === chip));
          currentPage = 1;
          applyFilters();
        });
      });
    };
    bindChips(platformChips, () => activePlatform, (v) => { activePlatform = v; });
    bindChips(typeChips, () => activeType, (v) => { activeType = v; });

    searchInput?.addEventListener("input", () => { currentPage = 1; applyFilters(); });
    sortSelect?.addEventListener("change", () => { currentPage = 1; applyFilters(); });
    expiryToggle?.addEventListener("change", () => {
      onlyExpiring = Boolean(expiryToggle.checked);
      currentPage = 1;
      applyFilters();
    });

    const offersUrl = (() => {
      const apiUrl = String(config.offersApiUrl || "").trim();
      if (apiUrl) {
        try {
          const u = new URL(apiUrl);
          if (u.protocol === "https:" || u.protocol === "http:") return u.href;
        } catch {}
      }
      const jsonUrl = String(config.offersJsonUrl || "").trim();
      if (jsonUrl) {
        try {
          const u = new URL(jsonUrl, window.location.href);
          return u.href;
        } catch {
          return jsonUrl;
        }
      }
      const fallback = offersRoot.dataset.offersUrl || "data/offers.json";
      try {
        return new URL(fallback, window.location.href).href;
      } catch {
        return fallback;
      }
    })();

    const showError = (msg) => {
      if (loadingNode) loadingNode.hidden = true;
      if (noticeNode) {
        noticeNode.hidden = false;
        noticeNode.innerHTML = `<strong>Catalogue temporairement indisponible</strong><p>${msg} — Vérifie <code>data/offers.json</code> ou <code>offersApiUrl</code> dans <code>assets/site-config.js</code>. Le bot doit publier le fichier comme décrit dans <code>data/README.md</code>.</p>`;
      }
      if (countNode) countNode.textContent = "0 offre";
    };

    fetchJson(offersUrl, 7000).then((payload) => {
      if (loadingNode) loadingNode.hidden = true;
      if (!payload) {
        showError("Le fichier d'offres n'a pas répondu depuis ce navigateur.");
        return;
      }
      const offers = Array.isArray(payload) ? payload : payload.offers;
      if (!Array.isArray(offers)) {
        showError("Format d'offres invalide (attendu : { offers: [] }).");
        return;
      }
      allOffers = offers.filter((o) => o && typeof o.title === "string" && typeof o.url === "string");

      if (updatedNode && payload.generated_at) {
        try {
          const d = new Date(payload.generated_at);
          const fmt = d.toLocaleString("fr-FR", { day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
          updatedNode.textContent = `Actualisé le ${fmt}`;
          updatedNode.dateTime = d.toISOString();
        } catch {
          updatedNode.textContent = `Actualisé : ${String(payload.generated_at)}`;
        }
      } else if (updatedNode) {
        updatedNode.textContent = "Actualisé automatiquement par FreeGameDrop";
      }

      if (noticeNode && payload.notice) {
        const isExample = /exemple/i.test(payload.notice);
        if (isExample) {
          noticeNode.hidden = false;
          noticeNode.innerHTML = `<strong>Catalogue d'exemple</strong><p>Les offres affichées sont illustratives — remplace <code>data/offers.json</code> par l'export automatique du bot pour afficher les vraies offres en temps réel. Voir <code>data/README.md</code>.</p>`;
        } else {
          noticeNode.hidden = true;
        }
      } else if (noticeNode) {
        noticeNode.hidden = true;
      }

      if (allOffers.length === 0) {
        if (emptyNode) {
          emptyNode.hidden = false;
          emptyNode.querySelector("h3").textContent = "Aucune offre pour le moment.";
          emptyNode.querySelector("p").textContent = "Le catalogue est vide : le bot n'a pas encore publié d'offres, ou toutes les offres temporaires ont expiré.";
        }
        if (countNode) countNode.textContent = "0 offre";
        return;
      }

      applyFilters();
      // Refresh urgency labels every minute
      setInterval(applyFilters, 60000);
    }).catch(() => {
      showError("Une erreur réseau a empêché le chargement du catalogue.");
    });
  }

  // ------------------------------------------------------------------
  // Individual game / DLC pages use the offer ID from the shared catalogue.
  // Example: /jeux-gratuits/fiche.html?id=steam_123456
  // ------------------------------------------------------------------
  const offerDetailRoot = document.querySelector("[data-offer-detail]");
  if (offerDetailRoot) {
    const status = offerDetailRoot.querySelector("[data-offer-detail-status]");
    const error = offerDetailRoot.querySelector("[data-offer-detail-error]");
    const card = offerDetailRoot.querySelector("[data-offer-detail-card]");
    const offerId = new URLSearchParams(window.location.search).get("id");
    const labels = { steam: "Steam", epic: "Epic Games Store", gog: "GOG", ubisoft: "Ubisoft Connect" };
    const typeLabels = { game: "Jeu complet", dlc: "DLC / Extension", pack: "Contenu bonus" };
    const escapeDetail = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[char]);
    const showDetailError = (message) => {
      if (status) status.hidden = true;
      if (error) {
        error.hidden = false;
        error.textContent = message;
      }
    };

    if (!offerId) {
      showDetailError("Cette fiche n'a pas d'identifiant. Reviens au catalogue et sélectionne un jeu ou un DLC.");
    } else {
      const apiUrl = String(config.offersApiUrl || "").trim();
      const configuredJson = String(config.offersJsonUrl || "").trim();
      const configuredSource = apiUrl || configuredJson || offerDetailRoot.dataset.offerDataUrl || "../data/offers.json";
      let dataUrl = configuredSource;
      try {
        dataUrl = new URL(configuredSource, window.location.href).href;
      } catch {}

      fetchJson(dataUrl, 7000).then((payload) => {
        const offers = Array.isArray(payload) ? payload : payload?.offers;
        const offer = Array.isArray(offers)
          ? offers.find((item) => item && String(item.id) === offerId)
          : null;
        if (!offer || !card) {
          showDetailError("Cette fiche n'est pas disponible dans le catalogue pour le moment.");
          return;
        }

        const title = String(offer.title || "Jeu ou DLC");
        const description = String(offer.description || "Aucune description n'est disponible pour cette offre.");
        const platform = String(offer.platform_label || labels[offer.platform] || offer.platform || "Boutique");
        const type = String(offer.type_label || typeLabels[offer.type] || offer.type || "Offre");
        const titleNode = card.querySelector("[data-offer-detail-title]");
        const imageNode = card.querySelector("[data-offer-detail-image]");
        const placeholder = card.querySelector("[data-offer-detail-placeholder]");
        titleNode.textContent = title;
        card.querySelector("[data-offer-detail-description]").textContent = description;
        card.querySelector("[data-offer-detail-platform]").textContent = platform;
        card.querySelector("[data-offer-detail-type]").textContent = type;
        placeholder.textContent = title.trim().charAt(0).toUpperCase() || "?";

        const imageUrl = String(offer.image || "").trim();
        let safeImage = "";
        try {
          const parsedImage = new URL(imageUrl);
          if (parsedImage.protocol === "https:") safeImage = parsedImage.href;
        } catch {}
        if (!safeImage && offer.platform === "steam") {
          const match = String(offer.url || "").match(/store\.steampowered\.com\/(?:app|sub)\/(\d+)/i);
          if (match) safeImage = `https://cdn.akamai.steamstatic.com/steam/apps/${match[1]}/header.jpg`;
        }
        if (safeImage) {
          imageNode.src = safeImage;
          imageNode.alt = `Visuel de ${title}`;
          imageNode.hidden = false;
          imageNode.addEventListener("error", () => { imageNode.hidden = true; }, { once: true });
        }

        const original = card.querySelector("[data-offer-detail-original]");
        if (offer.price_original) {
          original.textContent = String(offer.price_original);
          original.hidden = false;
        }
        const permanent = offer.is_permanent || offer.availability === "permanent" || !offer.expires_at;
        let expired = false;
        let deadline = "Toujours gratuit";
        if (!permanent) {
          const date = new Date(offer.expires_at);
          if (Number.isNaN(date.getTime())) deadline = "Durée limitée";
          else if (date.getTime() <= Date.now()) {
            expired = true;
            deadline = `Offre terminée le ${date.toLocaleDateString("fr-FR")}`;
          } else deadline = `Jusqu'au ${date.toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" })}`;
        }
        card.querySelector("[data-offer-detail-expiry]").textContent = deadline;
        document.title = `${title} — jeu ou DLC gratuit | OverX`;
        const descriptionMeta = document.querySelector('meta[name="description"]');
        if (descriptionMeta) descriptionMeta.content = `${title} : ${description}`.slice(0, 300);

        let directUrl = "";
        try {
          const parsedUrl = new URL(String(offer.url || ""));
          if (parsedUrl.protocol === "https:" && parsedUrl.pathname !== "/") directUrl = parsedUrl.href;
        } catch {}
        const claim = card.querySelector("[data-offer-detail-claim]");
        const linkNote = card.querySelector("[data-offer-detail-link-note]");
        if (directUrl && !expired) {
          claim.href = directUrl;
          claim.hidden = false;
        } else {
          linkNote.hidden = false;
          linkNote.textContent = expired
            ? "Cette promotion est terminée. Consulte la boutique pour vérifier si le jeu ou le DLC est encore disponible gratuitement."
            : "Le lien direct vers la fiche officielle de la boutique n'est pas disponible pour cette offre.";
        }
        if (status) status.hidden = true;
        if (error) error.hidden = true;
        card.hidden = false;
      }).catch(() => showDetailError("Impossible de charger le catalogue. Réessaie dans quelques instants."));
    }
  }
})();
