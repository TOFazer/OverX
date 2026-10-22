/*
 * Public website settings only.
 * Never put DISCORD_TOKEN, DISCORD_CLIENT_SECRET, DATABASE_URL, or other secrets here.
 * Discord Application IDs and invite URLs are public values used for installation links.
 */
window.OVERX_CONFIG = Object.freeze({
  // Public origin of the deployed site, no trailing slash (e.g. "https://overx.example").
  // When set, the build writes canonical/og:url/twitter:image and sitemap.xml from it.
  // Leave empty while the domain is not chosen: the site works fine without it.
  siteUrl: "",

  // Set the public Discord Application ID for the production bot to activate install CTAs.
  // Example format: "123456789012345678" — do not use a development app by accident.
  discordApplicationId: "1556443310053130260",

  // Official production install URL supplied by the project owner. It takes precedence over
  // the generated URL below so Discord receives the exact permissions/scopes they selected.
  // Scopes for the BOT invite link are exactly: bot + applications.commands.
  discordInstallUrl: "https://discord.com/oauth2/authorize?client_id=1556443310053130260&permissions=268528656&integration_type=0&scope=bot+applications.commands",

  // Fallback used only when discordInstallUrl is empty. Matches the production link above:
  // manage channels + manage roles + view channels + send messages + embed links
  // + read message history + manage messages (the two last ones are documented as optional).
  installPermissions: "268528656",

  // Optional: public invite to the OverX Discord community; hidden when empty.
  communityInviteUrl: "",

  // Optional public endpoints of the bot dashboard (read-only JSON, no secrets inside).
  // They feed the "FreeGameDrop en chiffres" band and the status page. The dashboard must allow
  // CORS from this site's origin (or be served behind the same domain). While empty,
  // every counter stays at "—" — real numbers only.
  statsApiUrl: "",
  healthApiUrl: "",

  // Project links (also referenced in page content and README).
  botSourceUrl: "https://github.com/TOFazer/FreeGameDropDev",
  supportUrl: "https://github.com/TOFazer/FreeGameDropDev/issues",
});
