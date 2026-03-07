import { aa as head, ai as ssr_context } from './index2-BJkuhNcZ.js';
import './exports-BXvEiaiv.js';
import { e as escape_html } from './escaping-CqgfEcN3.js';
import './state.svelte-BisSb15R.js';
import { t } from './i18n-DYMqjHva.js';

function onDestroy(fn) {
  /** @type {SSRContext} */
  ssr_context.r.on_destroy(fn);
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let segments = [];
    segments.map((s) => s.text).join(" ");
    segments.some((s) => s.translation) ? segments.map((s) => s.translation || "").join("") : "";
    segments.flatMap((s) => s.vocabulary ?? []).filter((v, i, arr) => arr.findIndex((a) => a.word === v.word) === i);
    onDestroy(() => {
    });
    head("1lrmvxp", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>IG Mode - ReelScript</title>`);
      });
    });
    $$renderer2.push(`<div class="ig-container svelte-1lrmvxp">`);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="ig-loading svelte-1lrmvxp"><p class="svelte-1lrmvxp">${escape_html(t("loading"))}</p></div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}

export { _page as default };
//# sourceMappingURL=_page.svelte-CvQOWMan.js.map
