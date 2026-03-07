import { aa as head, ad as attr, ac as ensure_array_like, ah as attr_class } from './index2-BJkuhNcZ.js';
import { t } from './i18n-DYMqjHva.js';
import { e as escape_html } from './escaping-CqgfEcN3.js';

function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let collections = [];
    let newName = "";
    let creating = false;
    let selectedDetail = null;
    head("8lyz9q", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>${escape_html(t("collections"))} — ReelScript</title>`);
      });
    });
    $$renderer2.push(`<div class="collections-layout svelte-8lyz9q"><div class="sidebar svelte-8lyz9q"><h2 class="svelte-8lyz9q">${escape_html(t("myCollections"))}</h2> <form class="create-form svelte-8lyz9q"><input type="text"${attr("value", newName)}${attr("placeholder", t("collectionName"))}${attr("disabled", creating, true)} class="svelte-8lyz9q"/> <button class="btn btn-primary svelte-8lyz9q" type="submit"${attr("disabled", !newName.trim(), true)}>${escape_html(t("create"))}</button></form> <div class="collection-list svelte-8lyz9q"><!--[-->`);
    const each_array = ensure_array_like(collections);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let col = each_array[$$index];
      $$renderer2.push(`<div${attr_class("collection-row svelte-8lyz9q", void 0, { "active": selectedDetail?.id === col.id })}><button class="collection-btn svelte-8lyz9q"><span class="col-name svelte-8lyz9q">${escape_html(col.name)}</span> <span class="col-count-badge svelte-8lyz9q">${escape_html(col.video_count)}</span></button> <button class="btn btn-danger btn-sm svelte-8lyz9q">x</button></div>`);
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<p class="empty svelte-8lyz9q">${escape_html(t("loading"))}</p>`);
    }
    $$renderer2.push(`<!--]--></div></div> <div class="detail-panel svelte-8lyz9q">`);
    {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<div class="empty-detail svelte-8lyz9q"><p>${escape_html(t("myCollections"))}</p></div>`);
    }
    $$renderer2.push(`<!--]--></div></div>`);
  });
}

export { _page as default };
//# sourceMappingURL=_page.svelte-DsICD0zt.js.map
