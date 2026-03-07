import { aa as head, ae as getContext } from './index2-BJkuhNcZ.js';
import './state.svelte-BisSb15R.js';
import './exports-BXvEiaiv.js';
import { w as writable } from './index-CKogXSVf.js';
import { t } from './i18n-DYMqjHva.js';
import { e as escape_html } from './escaping-CqgfEcN3.js';

function create_updated_store() {
  const { set, subscribe } = writable(false);
  {
    return {
      subscribe,
      // eslint-disable-next-line @typescript-eslint/require-await
      check: async () => false
    };
  }
}
const stores = {
  updated: /* @__PURE__ */ create_updated_store()
};
({
  check: stores.updated.check
});
function context() {
  return getContext("__request__");
}
const page$1 = {
  get params() {
    return context().page.params;
  }
};
const page = page$1;
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    page.params.id;
    head("95ygql", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>${escape_html(t("loading"))} — ${escape_html(t("blog"))}</title>`);
      });
    });
    $$renderer2.push(`<article class="post svelte-95ygql"><a href="/blog" class="back-link svelte-95ygql"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="svelte-95ygql"><polyline points="15 18 9 12 15 6" class="svelte-95ygql"></polyline></svg> ${escape_html(t("blogBackToList"))}</a> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="post-skeleton svelte-95ygql"><div class="sk wide svelte-95ygql"></div> <div class="sk narrow svelte-95ygql"></div> <div class="sk wide svelte-95ygql"></div> <div class="sk wide svelte-95ygql"></div></div>`);
    }
    $$renderer2.push(`<!--]--></article>`);
  });
}

export { _page as default };
//# sourceMappingURL=_page.svelte-sCcGsRIG.js.map
