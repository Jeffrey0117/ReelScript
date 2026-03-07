import { aa as head } from './index2-BJkuhNcZ.js';
import { p as page } from './stores-LNmbpkhS.js';
import './exports-BXvEiaiv.js';
import { e as escape_html } from './escaping-CqgfEcN3.js';
import './state.svelte-BisSb15R.js';
import { t } from './i18n-DYMqjHva.js';

function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    page.subscribe((p) => {
      p.params.id ?? "";
    });
    head("1oiicp0", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>${escape_html("Loading...")} — ReelScript</title>`);
      });
    });
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-1oiicp0">${escape_html(t("loading"))}</div>`);
    }
    $$renderer2.push(`<!--]-->`);
  });
}

export { _page as default };
//# sourceMappingURL=_page.svelte-BQzao7Uz.js.map
