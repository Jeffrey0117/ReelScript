import { aa as head, ac as ensure_array_like } from './index2-BJkuhNcZ.js';
import { t } from './i18n-DYMqjHva.js';
import { e as escape_html } from './escaping-CqgfEcN3.js';

function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    head("u4k2t", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>${escape_html(t("blog"))} — ReelScript</title>`);
      });
    });
    $$renderer2.push(`<section class="blog-page svelte-u4k2t"><h1 class="blog-heading svelte-u4k2t">${escape_html(t("blogTitle"))}</h1> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="blog-grid svelte-u4k2t"><!--[-->`);
      const each_array = ensure_array_like(Array(6));
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        each_array[$$index];
        $$renderer2.push(`<div class="blog-card skeleton svelte-u4k2t"><div class="skeleton-thumb svelte-u4k2t"></div> <div class="skeleton-body svelte-u4k2t"><div class="skeleton-line wide svelte-u4k2t"></div> <div class="skeleton-line narrow svelte-u4k2t"></div></div></div>`);
      }
      $$renderer2.push(`<!--]--></div>`);
    }
    $$renderer2.push(`<!--]--></section>`);
  });
}

export { _page as default };
//# sourceMappingURL=_page.svelte-Qe1bo-Dx.js.map
