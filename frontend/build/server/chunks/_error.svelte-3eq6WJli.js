import { a9 as store_get, aa as head, ab as unsubscribe_stores } from './index2-BJkuhNcZ.js';
import { p as page } from './stores-LNmbpkhS.js';
import { t } from './i18n-DYMqjHva.js';
import { e as escape_html } from './escaping-CqgfEcN3.js';
import './exports-BXvEiaiv.js';
import './state.svelte-BisSb15R.js';

function _error($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let status = store_get($$store_subs ??= {}, "$page", page).status;
    let message = store_get($$store_subs ??= {}, "$page", page).error?.message || "";
    head("1j96wlh", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Error ${escape_html(status)} — ReelScript</title>`);
      });
    });
    $$renderer2.push(`<div class="error-page svelte-1j96wlh"><h1 class="error-code svelte-1j96wlh">${escape_html(status)}</h1> <p class="error-message svelte-1j96wlh">${escape_html(message || "Something went wrong")}</p> <div class="error-actions"><a href="/" class="btn btn-primary">${escape_html(t("home"))}</a></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}

export { _error as default };
//# sourceMappingURL=_error.svelte-3eq6WJli.js.map
