import { e as escape_html } from './escaping-CqgfEcN3.js';
import { t } from './i18n-DYMqjHva.js';

function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { children } = $$props;
    $$renderer2.push(`<!---->`);
    {
      $$renderer2.push(`<div class="app svelte-12qhfyh"><nav class="navbar svelte-12qhfyh"><a href="/" class="logo svelte-12qhfyh">ReelScript <span class="logo-sub svelte-12qhfyh">一刷一句</span></a> <div class="nav-right svelte-12qhfyh"><div class="nav-links svelte-12qhfyh"><a href="/" class="svelte-12qhfyh">${escape_html(t("home"))}</a> <a href="/blog" class="svelte-12qhfyh">${escape_html(t("blog"))}</a> <a href="/collections" class="svelte-12qhfyh">${escape_html(t("collections"))}</a> `);
      {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></div> <div class="nav-actions svelte-12qhfyh"><button class="nav-btn svelte-12qhfyh" title="Toggle language">${escape_html("EN")}</button> <button class="nav-btn svelte-12qhfyh" title="Toggle theme">`);
      {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`);
      }
      $$renderer2.push(`<!--]--></button> `);
      {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push(`<button class="nav-btn login-btn svelte-12qhfyh">${escape_html(t("login"))}</button>`);
      }
      $$renderer2.push(`<!--]--></div></div></nav> <main class="main svelte-12qhfyh">`);
      children($$renderer2);
      $$renderer2.push(`<!----></main></div>`);
    }
    $$renderer2.push(`<!---->`);
  });
}

export { _layout as default };
//# sourceMappingURL=_layout.svelte-C_iCujID.js.map
